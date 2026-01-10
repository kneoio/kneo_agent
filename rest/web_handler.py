import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from cnst.llm_types import LlmType
from cnst.translation_types import TranslationType
from llm.llm_request import invoke_intro, translate_content
from llm.llm_response import LlmResponse
from rest.app_setup import app_lifespan, llm_factory, internet, cors_settings, cfg
from rest.prompt_request import PromptRequest
from rest.translation_request import TranslateRequest
from util.template_loader import render_template, template_exists

logger = logging.getLogger(__name__)

logger.info("Initializing FastAPI application...")
app = FastAPI(lifespan=app_lifespan)
logger.info("FastAPI application initialized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_settings["allow_origins"],
    allow_methods=cors_settings["allow_methods"],
    allow_headers=["X-API-Key"] + cors_settings["allow_headers"],
)

API_KEY = cfg["web_handler"]["api_key"]


async def verify_api_key(x_api_key: Annotated[str | None, Header()] = None):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=404, detail="Resource not found")


@app.post("/translate", dependencies=[Depends(verify_api_key)])
async def translate(req: TranslateRequest):
    client = llm_factory.get_llm_client(LlmType.GROQ)

    if req.translationType == TranslationType.PROMPT:
        lang_specific = f"translation/{req.language}_translate_prompt.hbs"
        if template_exists(lang_specific):
            template_path = lang_specific
            logger.info(f"Using language-specific translation template: {lang_specific}")
        else:
            template_path = "translation/default_translate_prompt.hbs"
    else:
        template_path = "translation/code.hbs"
    to_translate_text = render_template(template_path, {
        "language": req.language,
        "toTranslate": req.toTranslate
    })

    translation_result = await translate_content(client, to_translate_text)
    return {"result": translation_result.actual_result, "reasoning": translation_result.reasoning}


@app.post("/prompt/test", dependencies=[Depends(verify_api_key)])
async def test_prompt(req: PromptRequest):
    client = llm_factory.get_llm_client(req.llm, internet_mcp=internet)

    raw_response = await invoke_intro(client, req.prompt, req.draft, "")
    result = LlmResponse.parse_plain_response(raw_response, client.llm_type)
    print(f" >>>> RAW: {result}")
    return {"result": result.actual_result, "reasoning": result.reasoning}


@app.get("/health", dependencies=[Depends(verify_api_key)])
def health():
    return {"status": "ok"}
