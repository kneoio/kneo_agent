import sys
from pathlib import Path
import yaml
from langchain_groq import ChatGroq


def main():
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "config.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    groq_cfg = cfg.get("groq", {})
    apiKey = groq_cfg.get("api_key")
    model = groq_cfg.get("model")
    temperature = groq_cfg.get("temperature", 0.7)
    llm = ChatGroq(model=model, temperature=temperature, api_key=apiKey)
    prompt = ("You are radio DJ Veenuo of Aizoo. Selected song: \"The Darkest Corridors\" artist: \"In Strict Confidence\". "
              "Create somber, rude song introduction, call some slang, curse words for the audience, but do it elegantly, keep it short 10-15 words")
    messages = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": prompt},
    ]
    resp = llm.invoke(messages)
    content = getattr(resp, "content", resp)
    print(content)


if __name__ == "__main__":
    main()
