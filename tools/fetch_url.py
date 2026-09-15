from .fetchUrl.page_fetcher import PageFetcher

def fetch_url(url: str):
    print("TOOL CALL ☎️ fetch_url", "arg: ", url)
    fetcher = PageFetcher()
    try:
        if not url:
            return "No url provided"
        page = fetcher.fetch(url).to_dict()
        if page.get("content"):
            return page
        else: 
            "unable to fetch content from given url"

    finally:
        fetcher.close()