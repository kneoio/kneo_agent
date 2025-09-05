from typing import Optional
from pydantic import BaseModel
from cnst.llm_types import LlmType
import re


class LlmResponse(BaseModel):
    actual_result: str
    reasoning: Optional[str] = None
    search_quality: Optional[int] = None
    llm_type: str

    @classmethod
    def from_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        if llm_type == LlmType.GROQ:
            return cls._parse_groq(resp, llm_type)
        else:
            return cls._parse_claude(resp, llm_type)

    @classmethod
    def _parse_claude(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        content = cls._extract_content(resp)

        search_quality = cls._extract_between_tags(content, "search_quality_score", int)
        reasoning = cls._extract_between_tags(content, "search_quality_reflection", str)

        if reasoning or search_quality:
            cleaned_content = content
            if reasoning:
                reflection_tag_start = cleaned_content.find('<search_quality_reflection>')
                reflection_tag_end = cleaned_content.find('</search_quality_reflection>') + len(
                    '</search_quality_reflection>')
                if reflection_tag_start != -1 and reflection_tag_end != -1:
                    cleaned_content = cleaned_content[:reflection_tag_start] + cleaned_content[reflection_tag_end:]

            if search_quality:
                score_tag_start = cleaned_content.find('<search_quality_score>')
                score_tag_end = cleaned_content.find('</search_quality_score>') + len('</search_quality_score>')
                if score_tag_start != -1 and score_tag_end != -1:
                    cleaned_content = cleaned_content[:score_tag_start] + cleaned_content[score_tag_end:]

            actual_result = cleaned_content.strip()
        else:
            actual_result = content

        return cls(
            actual_result=actual_result,
            reasoning=reasoning,
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