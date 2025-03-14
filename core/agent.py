#!/usr/bin/env python3
import asyncio
import json
import logging
import time
from typing import Dict, Any

from anthropic import AsyncAnthropic

from api.brand_api import BrandAPI
from components.decision_executor import DecisionExecutor
from components.prompt_builder import PromptBuilder
from core.tool_registry import ToolRegistry
from models.brand import BrandManager


class DJAgent:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.claude = AsyncAnthropic(api_key=config["claude"]["api_key"])

        # Create separate Claude clients for each brand to maintain conversation history
        self.claude_clients: Dict[str, AsyncAnthropic] = {}

        self.brand_manager = BrandManager()
        self.tool_registry = ToolRegistry()

        # Initialize dictionaries
        self.conversation_history = {}

        self._initialize_brands()
        self._register_tools()

        # Initialize components
        self.prompt_builder = PromptBuilder(self.tool_registry)
        self.decision_executor = DecisionExecutor(self.brand_manager, self.tool_registry, self._get_claude_response)

    def _initialize_brands(self):
        brand_api = BrandAPI(self.config.get("api", {}))
        api_response = brand_api.get_all_brands()
        self.brand_manager = BrandManager.from_api_response(api_response)

        # Initialize Claude clients and conversation history for each brand
        for brand_slug in self.brand_manager.get_all_brand_slugs():
            self.claude_clients[brand_slug] = AsyncAnthropic(api_key=self.config["claude"]["api_key"])
            self.conversation_history[brand_slug] = []

        self.logger.info(f"Initialized {len(self.brand_manager.get_all_brand_slugs())} brands from API")

    def _register_tools(self):
        for tool_config in self.config.get("tools", []):
            try:
                module_path = tool_config["module"]
                class_name = tool_config["class"]

                import importlib
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)

                tool_config_with_brands = tool_config.get("config", {}).copy()
                tool_config_with_brands["brand_manager"] = self.brand_manager

                tool_instance = tool_class(tool_config_with_brands)
                self.tool_registry.register_tool(tool_instance)
                self.logger.info(f"Registered tool: {tool_instance.name}")

            except (ImportError, AttributeError, KeyError) as e:
                self.logger.error(f"Failed to register tool {tool_config.get('name', 'unknown')}: {e}")

    async def _get_claude_response(self, prompt: str, brand_slug: str = None) -> str:
        """Get a response from Claude based on the current context, maintaining brand-specific conversation."""
        if not brand_slug:
            self.logger.error("No brand specified for Claude response")
            return "Error: Brand not specified"

        brand = self.brand_manager.get_brand(brand_slug)
        if not brand:
            self.logger.error(f"Brand {brand_slug} not found")
            return f"Error: Brand {brand_slug} not found"

        system_prompt = self.prompt_builder.build_system_prompt(brand)

        # Get brand-specific Claude client
        claude_client = self.claude_clients.get(brand_slug, self.claude)

        # Get conversation history for this brand
        history = self.conversation_history.get(brand_slug, [])

        # Add the new message
        history.append({"role": "user", "content": prompt})

        try:
            response = await claude_client.messages.create(
                model=self.config["claude"]["model"],
                system=system_prompt,
                messages=history,
                max_tokens=self.config["claude"].get("max_tokens", 1000),
                temperature=self.config["claude"].get("temperature", 0.7),
            )

            response_text = response.content[0].text

            # Add the assistant's response to history
            history.append({"role": "assistant", "content": response_text})

            # Trim history if it gets too long (keep last 10 messages)
            if len(history) > 10:
                history = history[-10:]

            # Update the history
            self.conversation_history[brand_slug] = history

            return response_text

        except Exception as e:
            self.logger.error(f"Error getting response from Claude for brand {brand_slug}: {e}")
            return "I'm having trouble connecting to my reasoning system. Let me try again in a moment."

    async def process_cycle(self, brand_slug: str = None):
        """Process a single operation cycle for a specific brand."""
        brand = self.brand_manager.get_brand(brand_slug)
        if not brand:
            self.logger.error(f"Cannot process cycle: brand {brand_slug} not found")
            return

        # Get current state information
        current_state = brand.get_state()

        # Add brand identity details to the prompt
        brand_name = brand.slugName
        country = brand.country
        profile_name = brand.profile.name if brand.profile else "generic"

        # Ask Claude for decision on what to do next
        prompt = f"""
I'm the AI DJ for {brand_name} radio station in {country} with a {profile_name} environment.

Current state:
{json.dumps(current_state, indent=2)}

What action should I take next? Choose from:
1. Select and play a new song
2. Make an announcement
3. Check for audience feedback
4. Process a special request
5. Check for upcoming events
6. Other (specify)

Explain your decision briefly with necessary details for execution.
"""

        decision = await self._get_claude_response(prompt, brand.slugName)
        self.logger.info(f"Brand {brand.slugName} - Claude decision: {decision}")

        # Parse and execute the decision
        await self.decision_executor.execute(decision, brand.slugName)

        # Update system state after action
        brand.update_state("last_action", decision)

    async def run_async(self, duration_seconds=None):
        """Run the DJ Agent asynchronously for all brands."""
        self.logger.info("Starting DJ Agent async operation for all brands")
        start_time = time.time()

        while True:
            try:
                # Check if duration limit is reached
                if duration_seconds and (time.time() - start_time > duration_seconds):
                    self.logger.info(f"Reached time limit of {duration_seconds} seconds")
                    break

                # Process cycle for each brand using slugName
                for brand_slug in self.brand_manager.get_all_brand_slugs():
                    await self.process_cycle(brand_slug)

                # Sleep between cycles
                await asyncio.sleep(self.config.get("cycle_interval_seconds", 10))
            except Exception as e:
                self.logger.error(f"Error in process cycle: {e}")
                await asyncio.sleep(self.config.get("error_retry_seconds", 30))

    def run(self, duration_seconds=None):
        """Run the DJ Agent in a blocking manner."""
        self.logger.info("Starting DJ Agent operation")
        asyncio.run(self.run_async(duration_seconds))