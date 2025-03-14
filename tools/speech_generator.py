#!/usr/bin/env python3
# tools/speech_generator.py - Speech Generator tool

import logging
from typing import Dict, Any, List, Optional
import os
import json
from datetime import datetime
import tempfile
import subprocess
import threading
import queue

from tools.base_tool import BaseTool


class SpeechGenerator(BaseTool):
    """Tool for generating speech announcements and introductions."""

    def _initialize(self):
        """Initialize the Speech Generator."""
        self.output_dir = self.config.get("output_dir", "data/speech")
        self.tts_engine = self.config.get("tts_engine", "system")
        self.voice = self.config.get("voice", "default")
        self.speaking_rate = self.config.get("speaking_rate", 1.0)
        self.pitch = self.config.get("pitch", 0.0)
        self.volume = self.config.get("volume", 1.0)
        self.max_history = self.config.get("max_history", 100)
        self.history = []
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.current_speech = None

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Start the speech processing thread
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()

    def _get_name(self) -> str:
        """Get the name of the tool."""
        return "speech_generator"

    def _get_description(self) -> str:
        """Get a description of the tool."""
        return "Generates speech for announcements, introductions, and other spoken content."

    def _get_category(self) -> str:
        """Get the category of the tool."""
        return "presentation"

    def get_capabilities(self) -> List[str]:
        """Get a list of capabilities provided by this tool."""
        return [
            "generate_speech",
            "generate_introduction",
            "generate_announcement",
            "generate_weather_update",
            "generate_time_announcement",
            "get_history",
            "get_current_speech"
        ]

    def generate_speech(self, text: str, priority: int = 1) -> str:
        """
        Generate speech from text.

        Args:
            text: The text to convert to speech
            priority: Priority level (lower number = higher priority)

        Returns:
            Path to the generated audio file
        """
        # Create a unique file name based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"speech_{timestamp}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        # Create speech item for the queue
        speech_item = {
            "text": text,
            "file_path": file_path,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "status": "queued"
        }

        # Add to history
        self.history.append(speech_item)

        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Add to speech queue
        self.speech_queue.put(speech_item)

        self.logger.info(f"Queued speech: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        return file_path

    def generate_introduction(self, song_info: Dict[str, Any]) -> str:
        """
        Generate an introduction for a song.

        Args:
            song_info: Dictionary containing song information

        Returns:
            Path to the generated audio file
        """
        # Extract song information
        title = song_info.get("title", "Unknown title")
        artist = song_info.get("artist", "Unknown artist")
        album = song_info.get("album", "")
        year = song_info.get("release_year", "")

        # Create introduction text
        text = f"Now playing: {title} by {artist}"
        if album and year:
            text += f", from the {year} album {album}"
        elif album:
            text += f", from the album {album}"
        elif year:
            text += f", released in {year}"

        return self.generate_speech(text, priority=2)

    def generate_announcement(self, message: str, event_name: str = None) -> str:
        """
        Generate an announcement.

        Args:
            message: The announcement message
            event_name: Optional name of the associated event

        Returns:
            Path to the generated audio file
        """
        text = message
        if event_name:
            text = f"Announcement for {event_name}: {message}"

        return self.generate_speech(text, priority=1)

    def generate_weather_update(self, weather_info: Dict[str, Any]) -> str:
        """
        Generate a weather update announcement.

        Args:
            weather_info: Dictionary containing weather information

        Returns:
            Path to the generated audio file
        """
        # Extract weather information
        condition = weather_info.get("condition", "Unknown")
        temperature = weather_info.get("temperature", "")
        feels_like = weather_info.get("feels_like", "")
        humidity = weather_info.get("humidity", "")
        wind = weather_info.get("wind", "")

        # Create weather update text
        text = f"Weather update: Currently {condition}"
        if temperature:
            text += f", with a temperature of {temperature}"
        if feels_like and feels_like != temperature:
            text += f", feels like {feels_like}"
        if humidity:
            text += f". Humidity is {humidity}%"
        if wind:
            text += f", and wind is {wind}"

        return self.generate_speech(text, priority=3)

    def generate_time_announcement(self, custom_format: str = None) -> str:
        """
        Generate a time announcement.

        Args:
            custom_format: Optional custom format for the time announcement

        Returns:
            Path to the generated audio file
        """
        now = datetime.now()

        # Use custom format if provided, otherwise use a random format
        if custom_format:
            text = custom_format.format(
                hour=now.hour,
                hour12=now.hour if now.hour <= 12 else now.hour - 12,
                minute=now.minute,
                second=now.second,
                ampm="AM" if now.hour < 12 else "PM",
                day=now.day,
                month=now.month,
                year=now.year
            )
        else:
            # Use a simple format
            hour12 = now.hour if now.hour <= 12 else now.hour - 12
            if hour12 == 0:
                hour12 = 12
            ampm = "AM" if now.hour < 12 else "PM"

            if now.minute == 0:
                text = f"It's {hour12} o'clock {ampm}"
            else:
                text = f"It's {hour12}:{now.minute:02d} {ampm}"

        return self.generate_speech(text, priority=4)

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get the speech generation history.

        Args:
            limit: Maximum number of items to return (None for all)

        Returns:
            List of speech items in the history
        """
        if limit is None:
            return self.history
        return self.history[-limit:]

    def get_current_speech(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently playing speech.

        Returns:
            Current speech information or None if not speaking
        """
        return self.current_speech

    def _process_speech_queue(self):
        """Process the speech queue in a separate thread."""
        while True:
            try:
                # Get the next speech item from the queue
                speech_item = self.speech_queue.get()

                # Update status
                speech_item["status"] = "processing"
                self.is_speaking = True
                self.current_speech = speech_item

                # Generate the speech file
                success = self._generate_speech_file(
                    speech_item["text"],
                    speech_item["file_path"]
                )

                if success:
                    # Update status
                    speech_item["status"] = "playing"

                    # Play the speech file
                    self._play_speech_file(speech_item["file_path"])

                    # Update status
                    speech_item["status"] = "completed"
                else:
                    # Update status
                    speech_item["status"] = "failed"

                # Reset current speech
                self.is_speaking = False
                self.current_speech = None

                # Mark the task as done
                self.speech_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error processing speech queue: {e}")
                # Continue processing the queue despite errors

    def _generate_speech_file(self, text: str, file_path: str) -> bool:
        """
        Generate a speech file using the configured TTS engine.

        Args:
            text: Text to convert to speech
            file_path: Path to save the generated audio file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check which TTS engine to use
            if self.tts_engine == "system":
                # Use the system's TTS engine (this is a placeholder - implement based on OS)
                self._generate_with_system_tts(text, file_path)
            elif self.tts_engine == "gTTS":
                # Use Google Text-to-Speech
                self._generate_with_gtts(text, file_path)
            elif self.tts_engine == "pyttsx3":
                # Use pyttsx3
                self._generate_with_pyttsx3(text, file_path)
            else:
                # Use a placeholder for testing
                self._generate_placeholder(text, file_path)

            self.logger.debug(f"Generated speech file: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to generate speech file: {e}")
            return False

    def _generate_with_system_tts(self, text: str, file_path: str):
        """
        Generate speech using the system's TTS engine.
        This is a placeholder - implement based on the OS.

        Args:
            text: Text to convert to speech
            file_path: Path to save the generated audio file
        """
        # This is a placeholder - implement based on the OS
        # For example, on macOS:
        # subprocess.run(["say", "-o", file_path, text])

        # For now, use a placeholder
        self._generate_placeholder(text, file_path)

    def _generate_with_gtts(self, text: str, file_path: str):
        """
        Generate speech using Google Text-to-Speech.

        Args:
            text: Text to convert to speech
            file_path: Path to save the generated audio file
        """
        try:
            # This would require the gTTS package
            from gtts import gTTS

            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(file_path)
        except ImportError:
            self.logger.error("gTTS not installed. Using placeholder instead.")
            self._generate_placeholder(text, file_path)

    def _generate_with_pyttsx3(self, text: str, file_path: str):
        """
        Generate speech using pyttsx3.

        Args:
            text: Text to convert to speech
            file_path: Path to save the generated audio file
        """
        try:
            # This would require the pyttsx3 package
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty('rate', int(self.speaking_rate * 200))
            engine.setProperty('volume', self.volume)

            # Set voice if specified
            if self.voice != "default":
                voices = engine.getProperty('voices')
                for voice in voices:
                    if self.voice in voice.id:
                        engine.setProperty('voice', voice.id)
                        break

            engine.save_to_file(text, file_path)
            engine.runAndWait()
        except ImportError:
            self.logger.error("pyttsx3 not installed. Using placeholder instead.")
            self._generate_placeholder(text, file_path)

    def _generate_placeholder(self, text: str, file_path: str):
        """
        Generate a placeholder audio file for testing.

        Args:
            text: Text to convert to speech (not used)
            file_path: Path to save the generated audio file
        """
        # Create a simple WAV file with 1 second of silence
        with open(file_path, 'wb') as f:
            # WAV header (44 bytes)
            # File header
            f.write(b'RIFF')  # ChunkID
            f.write((36).to_bytes(4, byteorder='little'))  # ChunkSize
            f.write(b'WAVE')  # Format

            # Format chunk
            f.write(b'fmt ')  # Subchunk1ID
            f.write((16).to_bytes(4, byteorder='little'))  # Subchunk1Size
            f.write((1).to_bytes(2, byteorder='little'))  # AudioFormat (PCM)
            f.write((1).to_bytes(2, byteorder='little'))  # NumChannels (Mono)
            f.write((8000).to_bytes(4, byteorder='little'))  # SampleRate
            f.write((8000).to_bytes(4, byteorder='little'))  # ByteRate
            f.write((1).to_bytes(2, byteorder='little'))  # BlockAlign
            f.write((8).to_bytes(2, byteorder='little'))  # BitsPerSample

            # Data chunk
            f.write(b'data')  # Subchunk2ID
            f.write((8000).to_bytes(4, byteorder='little'))  # Subchunk2Size

            # 1 second of silence (8000 samples)
            f.write(b'\x80' * 8000)  # 8-bit PCM silence is 0x80

    def _play_speech_file(self, file_path: str):
        """
        Play a speech file.

        Args:
            file_path: Path to the audio file to play
        """
        try:
            # This is a placeholder - implement based on the OS
            # For example, on Linux:
            # subprocess.run(["aplay", file_path])

            # For testing, just log that the file would be played
            self.logger.info(f"Would play speech file: {file_path}")

            # Simulate playing by sleeping
            import time
            time.sleep(2)  # Simulate a 2-second audio clip
        except Exception as e:
            self.logger.error(f"Failed to play speech file: {e}")