import httpx
import trafilatura
import json

def fetch_page(url: str) -> dict:
    try:
        response = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (ResearchBot/1.0)"
            }
        )
        response.raise_for_status()

        text = trafilatura.extract(
            response.text,
            url=str(response.url),
            output_format="markdown",
            include_links=True,
            include_tables=True,
        )

        return {
            "url": str(response.url),
            "status": response.status_code,
            "content": text,
        }

    except Exception as e:
        return {
            "url": url,
            "error": str(e),
        }

results = fetch_page("https://docs.aws.amazon.com#sample-deployment-dashboard-cost")

with open("../results/output.json","w") as f:
    print(json.dump(results, f, indent=2, ensure_ascii=False))


