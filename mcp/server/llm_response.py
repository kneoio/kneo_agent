from typing import Optional
from pydantic import BaseModel
from cnst.llm_types import LlmType


class LlmResponse(BaseModel):
    actual_result: str
    reasoning: Optional[str] = None
    search_quality: Optional[int] = None
    llm_type: str

    @classmethod
    def from_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        """Universal response parser for all LLM types"""
        if llm_type == LlmType.GROQ:
            return cls._parse_groq(resp, llm_type)
        else:
            return cls._parse_claude(resp, llm_type)

    @classmethod
    def _parse_claude(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        """Parse Claude response format"""
        content = cls._extract_content(resp)

        search_quality = cls._extract_between_tags(content, "search_quality_score", int)
        reasoning = cls._extract_between_tags(content, "search_quality_reflection", str)

        # Extract result from <result> tags or use full content
        actual_result = cls._extract_between_tags(content, "result", str) or content
        actual_result = cls._clean_content(actual_result)

        return cls(
            actual_result=actual_result,
            reasoning=reasoning,
            search_quality=search_quality,
            llm_type=llm_type.name
        )

    @classmethod
    def _parse_groq(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        """Parse Groq response format"""
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
        """Extract text content from response object"""
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
        """Extract content between XML tags"""
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
        """Remove XML tags and clean up content"""
        import re
        # Remove XML tags
        content = re.sub(r'<[^>]+>', '', content)
        return content.strip()