import worldnewsapi
from core.config import load_config

configuration = worldnewsapi.Configuration(
    host = "https://api.worldnewsapi.com"
)

cfg = load_config("../../config.yaml")
key = cfg.get("api_services").get("worldnewsapi").get("api_key")
configuration.api_key["apiKey"] = key
configuration.api_key["headerApiKey"] = key

with worldnewsapi.ApiClient(configuration) as api_client:
    api = worldnewsapi.NewsApi(api_client)
    resp = api.top_news(source_country="pt", language="pt")

    for item in resp.top_news or []:
        for news in (item.news or []):
            extracted = api.extract_news(news.url, analyze=False)
            print(extracted.title)
            print(extracted.text)
            print()



