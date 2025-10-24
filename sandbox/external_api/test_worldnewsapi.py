from core.config import load_config
import worldnewsapi

def get_api_key():
    cfg = load_config("../config.yaml")
    return ((cfg.get("api_services") or {}).get("worldnewsapi") or {}).get("api_key") or ""


def run():
    key = get_api_key()
    configuration = worldnewsapi.Configuration(host="https://api.worldnewsapi.com")
    configuration.api_key["apiKey"] = key
    configuration.api_key["headerApiKey"] = key
    with worldnewsapi.ApiClient(configuration) as api_client:
        api = worldnewsapi.NewsApi(api_client)
        resp = api.top_news(source_country="pt", language="pt")
        print(str(resp)[:2000])


if __name__ == "__main__":
    run()
