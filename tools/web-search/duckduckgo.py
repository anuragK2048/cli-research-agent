# https://pypi.org/project/ddgs/

from ddgs import DDGS
import json

results = DDGS().text("python programming", max_results=5)
# results = DDGS().extract("https://en.wikipedia.org/wiki/Python_(programming_language)", fmt="text_rich")
print(json.dumps(results, indent=2, ensure_ascii=False))