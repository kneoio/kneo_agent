import logging
from typing import Optional, Any
from pydantic import BaseModel
from cnst.llm_types import LlmType
import json
import re

logger = logging.getLogger(__name__)

class LlmResponse(BaseModel):
    raw_response: Any  # The raw AIMessage or response object
    llm_type: str
    _structured_result: Optional[str] = None  # Override for structured responses

    @property
    def actual_result(self) -> str:
        """Extract the actual result content from the raw response."""
        if self._structured_result is not None:
            return self._structured_result
        return self._parse_content()

    @property 
    def reasoning(self) -> Optional[str]:
        """Extract reasoning from the raw response."""
        if self.llm_type == LlmType.GROQ.name:
            # Handle both AIMessage and dict formats
            if isinstance(self.raw_response, dict):
                return self.raw_response.get("additional_kwargs", {}).get("reasoning_content")
            else:
                return getattr(self.raw_response, "additional_kwargs", {}).get("reasoning_content")
        else:
            content = self._get_content_string()
            return self._extract_between_tags(content, "search_quality_reflection", str) or self._extract_between_tags(content, "thinking", str)

    @property
    def thinking(self) -> Optional[str]:
        """Extract thinking content from the raw response."""
        content = self._get_content_string()
        return self._extract_between_tags(content, "thinking", str)

    @property
    def search_quality(self) -> Optional[int]:
        """Extract search quality score from the raw response."""
        content = self._get_content_string()
        return self._extract_between_tags(content, "search_quality_score", int)

    def _get_content_string(self) -> str:
        """Get the content as a string from the raw response."""
        # Handle AIMessage format (Claude)
        if hasattr(self.raw_response, "content"):
            content = self.raw_response.content
            
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        parts.append(block["text"])
                    elif hasattr(block, "text"):
                        parts.append(block.text)
                return " ".join(parts)
            elif isinstance(content, str):
                return content
            else:
                return str(content)
        
        # Handle raw dict format (Groq, OpenAI)
        if isinstance(self.raw_response, dict):
            if "content" in self.raw_response:
                return self.raw_response["content"]
            elif "choices" in self.raw_response and self.raw_response["choices"]:
                choice = self.raw_response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
                elif "text" in choice:
                    return choice["text"]
        
        # Fallback for different response structures
        if hasattr(self.raw_response, "choices") and self.raw_response.choices:
            first_choice = self.raw_response.choices[0]
            if hasattr(first_choice, "message") and hasattr(first_choice.message, "content"):
                return first_choice.message.content
            elif hasattr(first_choice, "text"):
                return first_choice.text
        
        return ""

    def _parse_content(self) -> str:
        """Parse the actual result content, removing thinking/reasoning tags."""
        content = self._get_content_string()
        
        # Remove thinking and reasoning sections
        if self.thinking:
            content = self._remove_xml_section(content, "thinking")
        if self.reasoning and self.reasoning != self.thinking:
            content = self._remove_xml_section(content, "search_quality_reflection")
        if self.search_quality:
            content = self._remove_xml_section(content, "search_quality_score")
            
        return content.strip()

    @classmethod
    def parse_plain_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        """Create LlmResponse from raw response, storing it for lazy parsing."""
        return cls(raw_response=resp, llm_type=llm_type.name)

    @classmethod
    def parse_structured_response(cls, resp, llm_type: LlmType) -> 'LlmResponse':
        """Parse structured responses, potentially modifying the actual_result."""
        instance = cls.parse_plain_response(resp, llm_type)
        text = instance._parse_content().strip()  # Get raw parsed content without structured override
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            json_block = match.group(1).strip()
            try:
                json.loads(json_block)
                instance._structured_result = json_block
            except Exception:
                logger.warning("Structured parse: invalid JSON")
        return instance

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
