import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)

class ConversationSummarizer:
    def __init__(self, user_memory_manager, llm_factory, interval_minutes=30, idle_threshold_minutes=30):
        self.user_memory = user_memory_manager
        self.llm_factory = llm_factory
        self.interval_seconds = interval_minutes * 60
        self.idle_threshold_seconds = idle_threshold_minutes * 60
        self.running = False
        
    async def start(self):
        self.running = True
        logger.info(f"ConversationSummarizer started: checking every {self.interval_seconds/60}min, summarizing if idle > {self.idle_threshold_seconds/60}min")
        
        while self.running:
            try:
                await asyncio.sleep(self.interval_seconds)
                await self._check_and_summarize_conversations()
            except Exception as e:
                logger.error(f"Error in conversation summarizer: {e}", exc_info=True)
                
    async def stop(self):
        self.running = False
        logger.info("ConversationSummarizer stopped")
        
    async def _check_and_summarize_conversations(self):
        try:
            active_chats = await self.user_memory.get_all_active_chats()
            
            for chat_id, last_activity in active_chats:
                if not last_activity:
                    continue
                    
                time_since_activity = datetime.now() - last_activity
                
                if time_since_activity.total_seconds() > self.idle_threshold_seconds:
                    logger.info(f"Chat {chat_id} idle for {time_since_activity.total_seconds()/60:.1f}min, summarizing...")
                    await self._summarize_conversation(chat_id)
                    
        except Exception as e:
            logger.error(f"Error checking conversations: {e}", exc_info=True)
            
    async def _summarize_conversation(self, chat_id: int):
        try:
            data_state = await self.user_memory.load(chat_id)
            if not data_state or not data_state.get("history"):
                return
                
            history = data_state["history"]
            
            if len(history) < 10:
                logger.info(f"Chat {chat_id} history too short ({len(history)} messages), skipping summarization")
                return
                
            conversation_text = self._build_conversation_text(history)
            
            from util.template_loader import render_template
            system_prompt = render_template("summarizer/conversation_summary_system.hbs", {})
            user_prompt = render_template("summarizer/conversation_summary.hbs", {
                "conversation_text": conversation_text
            })
            
            from cnst.llm_types import LlmType
            llm_client = self.llm_factory.get_llm_client(LlmType.GROQ)
            
            from llm.llm_request import invoke_chat
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            result = await invoke_chat(llm_client=llm_client, messages=messages)
            summary = result.actual_result
            
            if not summary or len(summary) < 20:
                logger.warning(f"Chat {chat_id} summary too short, skipping")
                return
                
            new_history = [
                {"role": "assistant", "text": f"[Previous conversation summary: {summary}]"}
            ]
            
            new_history.extend(history[-3:])
            
            telegram_name = data_state.get("telegram_name", "")
            brand = data_state.get("brand", "default")
            
            await self.user_memory.save(chat_id, telegram_name, brand, new_history)
            
            logger.info(f"Chat {chat_id} summarized: {len(history)} messages → {len(new_history)} messages")
            
        except Exception as e:
            logger.error(f"Error summarizing chat {chat_id}: {e}", exc_info=True)
            
    def _build_conversation_text(self, history: list) -> str:
        conversation_text = []
        
        for msg in history:
            role = msg.get("role")
            text = msg.get("text", "")
            
            if role == "user":
                conversation_text.append(f"User: {text}")
            elif role == "assistant":
                conversation_text.append(f"Assistant: {text}")
                
        full_text = "\n".join(conversation_text[-30:])
        
        return full_text
