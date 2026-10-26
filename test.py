import json

from tools.fetchUrl.page_fetcher import PageFetcher

page_fetcher = PageFetcher()
url = "https://docs.gitlab.com/topics/git/undo/"

fetched_data = page_fetcher.fetch(url).to_dict()

with open("test.json", "w") as f:
    json.dump(fetched_data, f, indent=4, ensure_ascii=False)
