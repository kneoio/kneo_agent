#!/usr/bin/env python3
# tools/audience_engagement.py - Audience Engagement tool

import logging
from typing import Dict, Any, List, Optional
import json
import time
from datetime import datetime
import os
import threading
import queue

from tools.base_tool import BaseTool


class AudienceEngagement(BaseTool):
    """Tool for tracking and analyzing audience engagement and feedback."""

    def _initialize(self):
        """Initialize the Audience Engagement tool."""
        self.feedback_queue = queue.Queue()
        self.feedback_history = []
        self.current_mood = "neutral"
        self.current_energy = "medium"
        self.max_history = self.config.get("max_history", 100)
        self.save_path = self.config.get("save_path", "data/audience_feedback.json")
        self.auto_save = self.config.get("auto_save", True)
        self.sentiment_analysis = self.config.get("sentiment_analysis", False)

        # Create directory if it doesn't exist
        if self.auto_save:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

        # Load feedback history if available
        if self.auto_save and os.path.exists(self.save_path):
            self._load_feedback_history()

        # Start the feedback processing thread
        self.processing_thread = threading.Thread(target=self._process_feedback_queue, daemon=True)
        self.processing_thread.start()

    @property
    def name(self) -> str:
        """Get the name of the tool."""
        return "audience_engagement"

    @property
    def description(self) -> str:
        """Get a description of the tool."""
        return "Tracks and analyzes audience engagement and feedback."

    @property
    def category(self) -> str:
        """Get the category of the tool."""
        return "interaction"

    def get_capabilities(self) -> List[str]:
        """Get a list of capabilities provided by this tool."""
        return [
            "add_feedback",
            "get_recent_feedback",
            "get_mood_analysis",
            "get_energy_level",
            "get_engagement_metrics",
            "analyze_trend",
            "search_feedback",
            "get_top_phrases"
        ]

    def add_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """
        Add audience feedback to the queue for processing.

        Args:
            feedback_data: Dictionary containing feedback information

        Returns:
            bool: True if successful, False otherwise
        """
        # Validate required fields
        if "type" not in feedback_data:
            self.logger.error("Cannot add feedback: missing required field 'type'")
            return False

        # Add timestamp if not provided
        if "timestamp" not in feedback_data:
            feedback_data["timestamp"] = datetime.now().isoformat()

        # Add to queue for processing
        self.feedback_queue.put(feedback_data)
        self.logger.debug(f"Added feedback to queue: {feedback_data.get('type')}")
        return True

    def add_text_feedback(self, message: str, source: str = "anonymous") -> bool:
        """
        Add text-based feedback from audience.

        Args:
            message: The feedback message
            source: Source of the feedback (e.g., username)

        Returns:
            bool: True if successful, False otherwise
        """
        feedback_data = {
            "type": "text",
            "message": message,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        return self.add_feedback(feedback_data)

    def add_reaction(self, reaction_type: str, source: str = "anonymous") -> bool:
        """
        Add a reaction-based feedback (like, dislike, etc.).

        Args:
            reaction_type: Type of reaction
            source: Source of the reaction

        Returns:
            bool: True if successful, False otherwise
        """
        feedback_data = {
            "type": "reaction",
            "reaction": reaction_type,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        return self.add_feedback(feedback_data)

    def get_recent_feedback(self, limit: int = 10, feedback_type: str = None) -> List[Dict[str, Any]]:
        """
        Get recent feedback from the audience.

        Args:
            limit: Maximum number of feedback items to return
            feedback_type: Optional filter for feedback type

        Returns:
            List of recent feedback items
        """
        if not self.feedback_history:
            return []

        # Filter by type if specified
        if feedback_type:
            filtered_history = [f for f in self.feedback_history if f.get("type") == feedback_type]
        else:
            filtered_history = self.feedback_history

        # Return the most recent items
        return filtered_history[-limit:]

    def get_mood_analysis(self) -> Dict[str, Any]:
        """
        Get an analysis of the audience mood based on feedback.

        Returns:
            Dictionary containing mood analysis
        """
        # Count different mood indicators from recent feedback
        recent_feedback = self.get_recent_feedback(limit=20)

        mood_counts = {
            "positive": 0,
            "neutral": 0,
            "negative": 0
        }

        for feedback in recent_feedback:
            if feedback.get("type") == "reaction":
                reaction = feedback.get("reaction", "")
                if reaction in ["like", "love", "happy"]:
                    mood_counts["positive"] += 1
                elif reaction in ["dislike", "angry", "sad"]:
                    mood_counts["negative"] += 1
                else:
                    mood_counts["neutral"] += 1
            elif feedback.get("type") == "text" and "sentiment" in feedback:
                sentiment = feedback.get("sentiment", "neutral")
                mood_counts[sentiment] += 1

        # Determine overall mood
        if not recent_feedback:
            overall_mood = "neutral"
        elif mood_counts["positive"] > mood_counts["negative"] + mood_counts["neutral"]:
            overall_mood = "positive"
        elif mood_counts["negative"] > mood_counts["positive"] + mood_counts["neutral"]:
            overall_mood = "negative"
        else:
            overall_mood = "neutral"

        # Update current mood
        self.current_mood = overall_mood

        return {
            "overall_mood": overall_mood,
            "mood_counts": mood_counts,
            "sample_size": len(recent_feedback),
            "timestamp": datetime.now().isoformat()
        }

    def get_energy_level(self) -> Dict[str, Any]:
        """
        Get an estimate of the audience energy level.

        Returns:
            Dictionary containing energy level analysis
        """
        # Analyze recent feedback for energy indicators
        recent_feedback = self.get_recent_feedback(limit=20)

        energy_counts = {
            "high": 0,
            "medium": 0,
            "low": 0
        }

        for feedback in recent_feedback:
            if feedback.get("type") == "reaction":
                reaction = feedback.get("reaction", "")
                if reaction in ["love", "excited", "dance"]:
                    energy_counts["high"] += 1
                elif reaction in ["like", "happy"]:
                    energy_counts["medium"] += 1
                else:
                    energy_counts["low"] += 1
            elif feedback.get("type") == "text" and "energy" in feedback:
                energy = feedback.get("energy", "medium")
                energy_counts[energy] += 1

        # Determine overall energy level
        if not recent_feedback:
            overall_energy = "medium"
        elif energy_counts["high"] > energy_counts["medium"] + energy_counts["low"]:
            overall_energy = "high"
        elif energy_counts["low"] > energy_counts["high"] + energy_counts["medium"]:
            overall_energy = "low"
        else:
            overall_energy = "medium"

        # Update current energy
        self.current_energy = overall_energy

        return {
            "overall_energy": overall_energy,
            "energy_counts": energy_counts,
            "sample_size": len(recent_feedback),
            "timestamp": datetime.now().isoformat()
        }

    def get_engagement_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about audience engagement.

        Returns:
            Dictionary containing engagement metrics
        """
        if not self.feedback_history:
            return {
                "feedback_count": 0,
                "reaction_rate": 0,
                "text_feedback_rate": 0,
                "latest_feedback": None,
                "timestamp": datetime.now().isoformat()
            }

        # Calculate time windows
        now = datetime.now()

        # Convert timestamp strings to datetime objects
        parsed_timestamps = []
        for feedback in self.feedback_history:
            try:
                timestamp_str = feedback.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    parsed_timestamps.append(timestamp)
            except (ValueError, TypeError):
                # Skip invalid timestamps
                pass

        # Sort timestamps
        parsed_timestamps.sort()

        # Calculate metrics
        total_count = len(self.feedback_history)
        reaction_count = len([f for f in self.feedback_history if f.get("type") == "reaction"])
        text_count = len([f for f in self.feedback_history if f.get("type") == "text"])

        # Calculate recent engagement (last 10 minutes)
        ten_min_ago = now - timedelta(minutes=10)
        recent_count = len([t for t in parsed_timestamps if t >= ten_min_ago])

        # Calculate rate (per minute)
        if parsed_timestamps:
            oldest = parsed_timestamps[0]
            newest = parsed_timestamps[-1]
            time_span_minutes = max(1, (newest - oldest).total_seconds() / 60)
            rate_per_minute = total_count / time_span_minutes
        else:
            rate_per_minute = 0

        return {
            "feedback_count": total_count,
            "reaction_count": reaction_count,
            "text_count": text_count,
            "recent_count": recent_count,
            "rate_per_minute": rate_per_minute,
            "mood": self.current_mood,
            "energy": self.current_energy,
            "timestamp": now.isoformat()
        }

    def analyze_trend(self, window_minutes: int = 30) -> Dict[str, Any]:
        """
        Analyze trends in audience feedback over time.

        Args:
            window_minutes: Window size in minutes for trend analysis

        Returns:
            Dictionary containing trend analysis
        """
        if not self.feedback_history:
            return {
                "trend": "neutral",
                "confidence": 0,
                "timestamp": datetime.now().isoformat()
            }

        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        half_window = now - timedelta(minutes=window_minutes // 2)

        # Separate feedback into first and second half of the window
        first_half = []
        second_half = []

        for feedback in self.feedback_history:
            try:
                timestamp_str = feedback.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if window_start <= timestamp < half_window:
                        first_half.append(feedback)
                    elif half_window <= timestamp <= now:
                        second_half.append(feedback)
            except (ValueError, TypeError):
                # Skip invalid timestamps
                pass

        # If not enough data, return neutral trend
        if len(first_half) < 3 or len(second_half) < 3:
            return {
                "trend": "neutral",
                "confidence": 0,
                "first_half_count": len(first_half),
                "second_half_count": len(second_half),
                "timestamp": now.isoformat()
            }

        # Calculate mood scores for each half
        # (positive = 1, neutral = 0, negative = -1)
        first_score = 0
        second_score = 0

        # Function to get mood score
        def get_mood_score(feedback):
            if feedback.get("type") == "reaction":
                reaction = feedback.get("reaction", "")
                if reaction in ["like", "love", "happy"]:
                    return 1
                elif reaction in ["dislike", "angry", "sad"]:
                    return -1
                else:
                    return 0
            elif feedback.get("type") == "text" and "sentiment" in feedback:
                sentiment = feedback.get("sentiment", "neutral")
                if sentiment == "positive":
                    return 1
                elif sentiment == "negative":
                    return -1
                else:
                    return 0
            return 0

        # Calculate scores
        for feedback in first_half:
            first_score += get_mood_score(feedback)

        for feedback in second_half:
            second_score += get_mood_score(feedback)

        # Normalize scores
        first_score = first_score / len(first_half)
        second_score = second_score / len(second_half)

        # Calculate trend
        score_diff = second_score - first_score

        if score_diff > 0.2:
            trend = "improving"
        elif score_diff < -0.2:
            trend = "declining"
        else:
            trend = "stable"

        # Calculate confidence based on sample size
        sample_size = len(first_half) + len(second_half)
        confidence = min(1.0, sample_size / 20)

        return {
            "trend": trend,
            "score_difference": score_diff,
            "first_half_score": first_score,
            "second_half_score": second_score,
            "first_half_count": len(first_half),
            "second_half_count": len(second_half),
            "confidence": confidence,
            "window_minutes": window_minutes,
            "timestamp": now.isoformat()
        }

    def search_feedback(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for specific feedback containing the query.

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of matching feedback items
        """
        query = query.lower()
        results = []

        for feedback in self.feedback_history:
            if feedback.get("type") == "text":
                message = feedback.get("message", "").lower()
                if query in message:
                    results.append(feedback)
            elif feedback.get("type") == "reaction":
                reaction = feedback.get("reaction", "").lower()
                if query in reaction:
                    results.append(feedback)

        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return results[:limit]

    def get_top_phrases(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most common phrases from text feedback.

        Args:
            limit: Maximum number of phrases to return

        Returns:
            List of top phrases with their counts
        """
        # This is a simplified implementation
        # A real implementation would use NLP techniques for phrase extraction

        # Extract all text feedback
        text_feedback = [f.get("message", "") for f in self.feedback_history if f.get("type") == "text"]

        # Count word frequencies (simple approach)
        word_counts = {}
        for text in text_feedback:
            words = text.lower().split()
            for word in words:
                # Clean the word (remove punctuation)
                clean_word = ''.join(c for c in word if c.isalnum())
                if clean_word and len(clean_word) > 2:  # Skip short words
                    word_counts[clean_word] = word_counts.get(clean_word, 0) + 1

        # Sort by count
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

        # Format results
        results = [{"phrase": word, "count": count} for word, count in sorted_words[:limit]]

        return results

    def _process_feedback_queue(self):
        """Process the feedback queue in a separate thread."""
        while True:
            try:
                # Get the next feedback item from the queue
                feedback = self.feedback_queue.get()

                # Perform sentiment analysis if enabled
                if self.sentiment_analysis and feedback.get("type") == "text":
                    feedback["sentiment"] = self._analyze_sentiment(feedback.get("message", ""))

                # Add to history
                self.feedback_history.append(feedback)

                # Trim history if needed
                if len(self.feedback_history) > self.max_history:
                    self.feedback_history = self.feedback_history[-self.max_history:]

                # Auto-save if enabled
                if self.auto_save:
                    self._save_feedback_history()

                # Mark the task as done
                self.feedback_queue.task_done()

                # Add a small delay to avoid hammering the CPU
                time.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Error processing feedback queue: {e}")
                # Continue processing the queue despite errors

    def _analyze_sentiment(self, text: str) -> str:
        """
        Analyze the sentiment of text.
        This is a placeholder - a real implementation would use a proper NLP library.

        Args:
            text: The text to analyze

        Returns:
            Sentiment classification (positive, neutral, negative)
        """
        # This is a very simplistic sentiment analysis for demonstration
        # A real implementation would use a proper NLP model

        # Convert to lowercase
        text = text.lower()

        # Define sentiment word lists
        positive_words = ["good", "great", "awesome", "excellent", "love", "like", "happy", "best"]
        negative_words = ["bad", "terrible", "awful", "hate", "dislike", "worse", "worst", "sad"]

        # Count occurrences
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        # Determine sentiment
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _save_feedback_history(self) -> bool:
        """
        Save the feedback history to a file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.save_path, 'w') as f:
                json.dump(self.feedback_history, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save feedback history: {e}")
            return False

    def _load_feedback_history(self) -> bool:
        """
        Load the feedback history from a file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.save_path, 'r') as f:
                self.feedback_history = json.load(f)

            self.logger.info(f"Loaded {len(self.feedback_history)} feedback items from {self.save_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load feedback history: {e}")
            return False
