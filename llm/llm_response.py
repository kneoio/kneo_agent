import logging
from typing import Optional
from pydantic import BaseModel
from cnst.llm_types import LlmType
import json
import re

logger = logging.getLogger(__name__)

class LlmResponse(BaseModel):
    actual_result: str
    reasoning: Optional[str] = None
    thinking: Optional[str] = None
    search_quality: Optional[int] = None
    llm_type: str

    @classmethod
    def _parse_claude(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        content = ""
        if hasattr(resp, "content") and isinstance(resp.content, list):
            parts = []
            for block in resp.content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
                elif hasattr(block, "text"):
                    parts.append(block.text)
            content = " ".join(parts)
        elif hasattr(resp, "content"):
            content = str(resp.content)

        if not content.strip():
            logger.warning("Claude response parsing returned empty content. Raw resp=%s", resp)

        search_quality = cls._extract_between_tags(content, "search_quality_score", int)
        reasoning = cls._extract_between_tags(content, "search_quality_reflection", str)
        thinking = cls._extract_between_tags(content, "thinking", str)

        cleaned_content = content
        if thinking:
            cleaned_content = cls._remove_xml_section(cleaned_content, "thinking")
        if reasoning:
            cleaned_content = cls._remove_xml_section(cleaned_content, "search_quality_reflection")
        if search_quality:
            cleaned_content = cls._remove_xml_section(cleaned_content, "search_quality_score")

        return cls(
            actual_result=cleaned_content.strip(),
            reasoning=reasoning,
            thinking=thinking,
            search_quality=search_quality,
            llm_type=llm_type.name
        )

    @classmethod
    def _parse_groq(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        content = getattr(resp, "content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
                elif hasattr(block, "text"):
                    parts.append(block.text)
            content = " ".join(parts)
        elif isinstance(content, str):
            content = content.strip()
        else:
            content = str(content)

        if not content.strip():
            logger.warning("Groq response parsing returned empty content. Raw resp=%s", resp)

        reasoning = getattr(resp, "additional_kwargs", {}).get("reasoning_content")

        return cls(
            actual_result=content.strip(),
            reasoning=reasoning,
            search_quality=None,
            llm_type=llm_type.name
        )

    @classmethod
    def _parse_openai(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        content = ""
        try:
            if hasattr(resp, "choices") and resp.choices:
                first_choice = resp.choices[0]
                if hasattr(first_choice, "message"):
                    content = first_choice.message.get("content", "")
                elif hasattr(first_choice, "text"):
                    content = first_choice.text
        except Exception as e:
            logger.error("Error parsing OpenAI response: %s", e)

        if not content.strip():
            logger.warning("OpenAI response parsing returned empty content. Raw resp=%s", resp)

        return cls(
            actual_result=content.strip(),
            reasoning=None,
            search_quality=None,
            llm_type=llm_type.name
        )

    @classmethod
    def parse_plain_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        if llm_type == LlmType.GROQ:
            return cls._parse_groq(resp, llm_type)
        elif llm_type == LlmType.OPENAI:
            return cls._parse_openai(resp, llm_type)
        else:  # default Claude
            return cls._parse_claude(resp, llm_type)

    @staticmethod
    def _extract_between_tags(content: str, tag: str, convert_type=str):
        try:
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"
            start = content.find(start_tag)
            if start == -1:
                return None
            start += len(start_tag)
            end = content.find(end_tag, start)
            if end == -1:
                return None
            extracted = content[start:end].strip()
            return convert_type(extracted) if extracted else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _remove_xml_section(content: str, tag: str) -> str:
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        start_pos = content.find(start_tag)
        end_pos = content.find(end_tag)
        if start_pos != -1 and end_pos != -1:
            end_pos += len(end_tag)
            return content[:start_pos] + content[end_pos:]
        return content

    @classmethod
    def parse_structured_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        if llm_type == LlmType.CLAUDE:
            return cls._parse_claude_structured(resp, llm_type)
        elif llm_type == LlmType.OPENAI:
            return cls._parse_openai_structured(resp, llm_type)
        elif llm_type == LlmType.GROQ:
            return cls._parse_groq_structured(resp, llm_type)
        else:
            return cls._parse_claude_structured(resp, llm_type)

    @classmethod
    def _parse_claude_structured(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        base = cls._parse_claude(resp, llm_type)
        raw = base.actual_result.strip()
        match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
        if match:
            json_block = match.group(1).strip()
            try:
                json.loads(json_block)
                base.actual_result = json_block
            except Exception:
                logger.warning("Claude structured parse: invalid JSON")
        return base

    @classmethod
    def _parse_openai_structured(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        base = cls._parse_openai(resp, llm_type)
        text = base.actual_result.strip()
        try:
            json.loads(text)
        except Exception:
            match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        base.actual_result = text
        return base

    @classmethod
    def _parse_groq_structured(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        base = cls._parse_groq(resp, llm_type)
        text = base.actual_result.strip()
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            block = match.group(1).strip()
            try:
                json.loads(block)
                base.actual_result = block
            except Exception:
                pass
        return base
