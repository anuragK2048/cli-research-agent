from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Optional
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@dataclass
class Page:
    url: str
    final_url: str
    title: Optional[str]
    content: str
    content_type: str
    status_code: int
    fetched_with: str
    word_count: int
    content_hash: str
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class PageFetcher:
    """
    Fetches and extracts useful content from web pages.

    Strategy:

        URL
         |
         +--> HTTP fetch
         |       |
         |       +--> PDF ----------> PyMuPDF
         |       |
         |       +--> HTML
         |             |
         |             +--> Trafilatura
         |             |
         |             +--> BeautifulSoup fallback
         |
         +--> If extraction fails
                 |
                 +--> Playwright
                         |
                         +--> Trafilatura
                         |
                         +--> BeautifulSoup
    """

    def __init__(
        self,
        timeout: float = 20.0,
        max_retries: int = 2,
        min_content_length: int = 200,
        enable_browser: bool = True,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_content_length = min_content_length
        self.enable_browser = enable_browser
        self.playwright = None
        self.browser = None

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; ResearchAgent/1.0; "
                "+https://example.com/bot)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,"
                "application/pdf;q=0.8,*/*;q=0.5"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def fetch(self, url: str) -> Page:
        """
        Fetch a URL and return a normalized Page object.
        """

        url = self._normalize_url(url)

        if not url:
            return self._error_page(
                url,
                "Invalid URL"
            )

        # -----------------------------------------------------
        # 1. Normal HTTP request
        # -----------------------------------------------------

        try:
            response = self._http_get(url)

            content_type = response.headers.get(
                "content-type",
                ""
            ).lower()

            final_url = str(response.url)

            # -------------------------------------------------
            # PDF
            # -------------------------------------------------

            if (
                "application/pdf" in content_type
                or final_url.lower().endswith(".pdf")
            ):
                return self._extract_pdf(
                    response.content,
                    url,
                    final_url,
                    response.status_code,
                )

            # -------------------------------------------------
            # HTML
            # -------------------------------------------------

            if (
                "text/html" in content_type
                or "application/xhtml+xml" in content_type
                or content_type == ""
            ):
                html = response.text

                page = self._extract_html(
                    html,
                    url,
                    final_url,
                    response.status_code,
                    fetched_with="httpx + trafilatura",
                )

                if self._is_good_content(page.content):
                    return page

                # -------------------------------------------------
                # 2. Browser fallback
                # -------------------------------------------------

                if self.enable_browser:
                    browser_page = self._fetch_with_browser(url)

                    if browser_page and self._is_good_content(
                        browser_page.content
                    ):
                        return browser_page

                return page

            # -------------------------------------------------
            # Other content types
            # -------------------------------------------------

            return Page(
                url=url,
                final_url=final_url,
                title=None,
                content=response.text[:10000],
                content_type=content_type,
                status_code=response.status_code,
                fetched_with="httpx",
                word_count=len(response.text.split()),
                content_hash=self._hash(response.text),
            )

        except Exception as e:

            # -------------------------------------------------
            # Browser fallback if HTTP failed
            # -------------------------------------------------

            if self.enable_browser:

                try:
                    browser_page = self._fetch_with_browser(url)

                    if browser_page:
                        return browser_page

                except Exception:
                    pass

            return self._error_page(
                url,
                str(e)
            )

    # ---------------------------------------------------------
    # HTTP
    # ---------------------------------------------------------

    def _http_get(self, url: str) -> httpx.Response:

        last_error = None

        for attempt in range(
            self.max_retries + 1
        ):

            try:

                with httpx.Client(
                    headers=self.headers,
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:

                    response = client.get(url)

                    response.raise_for_status()

                    return response

            except Exception as e:

                last_error = e

                if attempt < self.max_retries:
                    continue

        raise RuntimeError(
            f"HTTP request failed: {last_error}"
        )

    # ---------------------------------------------------------
    # HTML extraction
    # ---------------------------------------------------------

    def _extract_html(
        self,
        html: str,
        original_url: str,
        final_url: str,
        status_code: int,
        fetched_with: str,
    ) -> Page:

        title = self._extract_title(html)

        # -----------------------------------------------------
        # Trafilatura
        # -----------------------------------------------------

        content = trafilatura.extract(
            html,
            url=final_url,
            output_format="markdown",
            include_links=True,
            include_tables=True,
            include_images=False,
            include_formatting=True,
        )

        if content:

            content = self._clean_text(content)

            return self._build_page(
                url=original_url,
                final_url=final_url,
                title=title,
                content=content,
                content_type="text/html",
                status_code=status_code,
                fetched_with=fetched_with,
            )

        # -----------------------------------------------------
        # BeautifulSoup fallback
        # -----------------------------------------------------

        content = self._beautifulsoup_extract(html)

        return self._build_page(
            url=original_url,
            final_url=final_url,
            title=title,
            content=content,
            content_type="text/html",
            status_code=status_code,
            fetched_with="httpx + BeautifulSoup",
        )

    # ---------------------------------------------------------
    # BeautifulSoup
    # ---------------------------------------------------------

    def _beautifulsoup_extract(
        self,
        html: str
    ) -> str:

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # Remove things that aren't useful for research.
        for tag in soup([
            "script",
            "style",
            "noscript",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "svg",
        ]):
            tag.decompose()

        # Prefer article/main content.
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(
                "div",
                attrs={"role": "main"}
            )
        )

        if main:
            text = main.get_text(
                "\n",
                strip=True
            )
        else:
            text = soup.get_text(
                "\n",
                strip=True
            )

        return self._clean_text(text)

    # ---------------------------------------------------------
    # PDF extraction
    # ---------------------------------------------------------

    def _extract_pdf(
        self,
        data: bytes,
        original_url: str,
        final_url: str,
        status_code: int,
    ) -> Page:

        if fitz is None:
            return self._error_page(
                original_url,
                "PyMuPDF is not installed"
            )

        try:

            document = fitz.open(
                stream=data,
                filetype="pdf"
            )

            pages = []

            for page_number, pdf_page in enumerate(
                document
            ):

                text = pdf_page.get_text()

                if text.strip():
                    pages.append(
                        f"## Page {page_number + 1}\n\n"
                        f"{text}"
                    )

            content = "\n\n".join(pages)

            metadata = document.metadata or {}

            title = (
                metadata.get("title")
                or None
            )

            document.close()

            return self._build_page(
                url=original_url,
                final_url=final_url,
                title=title,
                content=self._clean_text(content),
                content_type="application/pdf",
                status_code=status_code,
                fetched_with="httpx + PyMuPDF",
            )

        except Exception as e:

            return self._error_page(
                original_url,
                f"PDF extraction failed: {e}"
            )

    # ---------------------------------------------------------
    # Playwright
    # ---------------------------------------------------------

    def _get_browser(self):
        if sync_playwright is None:
            return None

        if self.browser is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)

        return self.browser

    def _fetch_with_browser(
        self,
        url: str
    ) -> Optional[Page]:

        browser = self._get_browser()

        if browser is None:
            return None

        page = browser.new_page(
            user_agent=self.headers["User-Agent"]
        )

        try:

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=int(
                    self.timeout * 1000
                ),
            )

            # Give client-side rendering a chance.
            page.wait_for_timeout(5000)

            html = page.content()

            final_url = page.url

            status_code = (
                response.status
                if response
                else 200
            )

            result = self._extract_html(
                html,
                url,
                final_url,
                status_code,
                fetched_with=(
                    "Playwright + Trafilatura"
                ),
            )

            return result

        except Exception as e:

            print(
                f"[Browser error] {url}: {e}"
            )

            return None

        finally:

            page.close()

    def close(self):
        if self.browser:
            self.browser.close()
            self.browser = None
    
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _extract_title(
        html: str
    ) -> Optional[str]:

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        if soup.title:
            title = soup.title.get_text(
                " ",
                strip=True
            )

            if title:
                return title

        # OpenGraph fallback
        og_title = soup.find(
            "meta",
            property="og:title"
        )

        if og_title:
            return og_title.get(
                "content"
            )

        return None

    @staticmethod
    def _clean_text(
        text: str
    ) -> str:

        if not text:
            return ""

        # Normalize line endings.
        text = text.replace(
            "\r\n",
            "\n"
        )

        text = text.replace(
            "\r",
            "\n"
        )

        # Remove excessive spaces.
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # Maximum 2 consecutive newlines.
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    def _is_good_content(
        self,
        content: str
    ) -> bool:

        if not content:
            return False

        cleaned = content.strip()

        if len(cleaned) < self.min_content_length:
            return False

        words = cleaned.split()

        if len(words) < 40:
            return False

        return True

    @staticmethod
    def _hash(
        text: str
    ) -> str:

        return hashlib.sha256(
            text.encode(
                "utf-8",
                errors="ignore"
            )
        ).hexdigest()

    def _build_page(
        self,
        url: str,
        final_url: str,
        title: Optional[str],
        content: str,
        content_type: str,
        status_code: int,
        fetched_with: str,
    ) -> Page:

        content = content or ""

        return Page(
            url=url,
            final_url=final_url,
            title=title,
            content=content,
            content_type=content_type,
            status_code=status_code,
            fetched_with=fetched_with,
            word_count=len(
                content.split()
            ),
            content_hash=self._hash(
                content
            ),
        )

    @staticmethod
    def _normalize_url(
        url: str
    ) -> str:

        url = url.strip()

        if not url:
            return ""

        parsed = urlparse(url)

        if not parsed.scheme:
            url = "https://" + url

        return url

    @staticmethod
    def _error_page(
        url: str,
        error: str
    ) -> Page:

        return Page(
            url=url,
            final_url=url,
            title=None,
            content="",
            content_type="",
            status_code=0,
            fetched_with="none",
            word_count=0,
            content_hash="",
            error=error,
        )


# =============================================================
# EXECUTION
# =============================================================

if __name__ == "__main__":

    fetcher = PageFetcher(
        timeout=20,
        max_retries=2,
        enable_browser=True,
    )

    url = (
        "https://www.netacad.com/learning-collections/python"
    )

    print("=" * 80)
    print("FETCHING:")
    print(url)
    print("=" * 80)

    page = fetcher.fetch(url)

    print()
    print("TITLE:")
    print(page.title)

    print()
    print("FINAL URL:")
    print(page.final_url)

    print()
    print("STATUS:")
    print(page.status_code)

    print()
    print("CONTENT TYPE:")
    print(page.content_type)

    print()
    print("FETCHED WITH:")
    print(page.fetched_with)

    print()
    print("WORD COUNT:")
    print(page.word_count)

    print()
    print("CONTENT HASH:")
    print(page.content_hash)

    if page.error:

        print()
        print("ERROR:")
        print(page.error)

    print()
    print("=" * 80)
    print("CONTENT")
    print("=" * 80)
    print()

    print(page.content[:10000])
