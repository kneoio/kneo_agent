from typing import Optional
from pydantic import BaseModel
from cnst.llm_types import LlmType
import re


class LlmResponse(BaseModel):
    actual_result: str
    reasoning: Optional[str] = None
    thinking: Optional[str] = None  # New field for <thinking> tags
    search_quality: Optional[int] = None
    llm_type: str

    @classmethod
    def _parse_claude(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        """Parse Claude response format"""
        content = cls._extract_content(resp)

        search_quality = cls._extract_between_tags(content, "search_quality_score", int)
        reasoning = cls._extract_between_tags(content, "search_quality_reflection", str)
        thinking = cls._extract_between_tags(content, "thinking", str)

        # Remove all XML sections from content
        cleaned_content = content

        if thinking:
            cleaned_content = cls._remove_xml_section(cleaned_content, "thinking")

        if reasoning:
            cleaned_content = cls._remove_xml_section(cleaned_content, "search_quality_reflection")

        if search_quality:
            cleaned_content = cls._remove_xml_section(cleaned_content, "search_quality_score")

        actual_result = cleaned_content.strip()

        return cls(
            actual_result=actual_result,
            reasoning=reasoning,
            thinking=thinking,
            search_quality=search_quality,
            llm_type=llm_type.name
        )

    @classmethod
    def _parse_groq(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        content = getattr(resp, "content", "").strip()
        reasoning = getattr(resp, "additional_kwargs", {}).get("reasoning_content")

        return cls(
            actual_result=content,
            reasoning=reasoning,
            search_quality=None,
            llm_type=llm_type.name
        )

    @classmethod
    def from_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        if llm_type == LlmType.GROQ:
            return cls._parse_groq(resp, llm_type)
        else:
            return cls._parse_claude(resp, llm_type)

    @staticmethod
    def _extract_content(response) -> str:
        if not hasattr(response, 'content'):
            return ""

        content = response.content

        if isinstance(content, list):
            return ' '.join(
                block.text if hasattr(block, 'text')
                else block.get('text', '') if isinstance(block, dict)
                else str(block)
                for block in content
            )

        return str(content) if content else ""

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
    def _clean_content(content: str) -> str:
        content = re.sub(r'<[^>]+>', '', content)
        return content.strip()