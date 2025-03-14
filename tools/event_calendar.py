#!/usr/bin/env python3
# tools/event_calendar.py - Event Calendar tool

import logging
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime, timedelta
import sqlite3

from tools.base_tool import BaseTool


class EventCalendar(BaseTool):
    """Tool for managing and accessing the event calendar."""

    def _initialize(self):
        """Initialize the Event Calendar."""
        self.db_path = self.config.get("db_path", "data/events.db")
        self.create_if_missing = self.config.get("create_if_missing", True)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Check if database exists, create if needed
        db_exists = os.path.exists(self.db_path)
        if not db_exists and not self.create_if_missing:
            self.logger.error(f"Database file not found: {self.db_path}")
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        # Connect to database and create tables if needed
        self.conn = self._connect_to_db()
        if not db_exists and self.create_if_missing:
            self._create_tables()

        self.logger.info(f"Connected to event database at {self.db_path}")

    def _get_name(self) -> str:
        """Get the name of the tool."""
        return "event_calendar"

    def _get_description(self) -> str:
        """Get a description of the tool."""
        return "Manages and accesses the event calendar for scheduling and announcements."

    def _get_category(self) -> str:
        """Get the category of the tool."""
        return "scheduling"

    def get_capabilities(self) -> List[str]:
        """Get a list of capabilities provided by this tool."""
        return [
            "add_event",
            "remove_event",
            "update_event",
            "get_event",
            "get_events_by_date",
            "get_current_events",
            "get_upcoming_events",
            "set_reminder",
            "get_reminders",
            "import_events",
            "export_events"
        ]

    def _connect_to_db(self) -> sqlite3.Connection:
        """
        Connect to the SQLite database.

        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return results as dictionaries
        return conn

    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Create events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            location TEXT,
            event_type TEXT,
            recurring TEXT,
            recurring_end_date TIMESTAMP,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create reminders table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            reminder_time TIMESTAMP NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
        ''')

        # Create event_tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_tags (
            event_id INTEGER,
            tag TEXT,
            PRIMARY KEY (event_id, tag),
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
        ''')

        # Commit the changes
        self.conn.commit()
        self.logger.info("Created event database tables")

    def add_event(self, event_info: Dict[str, Any]) -> Optional[int]:
        """
        Add a new event to the calendar.

        Args:
            event_info: Dictionary containing event information

        Returns:
            ID of the added event or None if unsuccessful
        """
        # Validate required fields
        required_fields = ["title", "start_time"]
        for field in required_fields:
            if field not in event_info:
                self.logger.error(f"Cannot add event: missing required field '{field}'")
                return None

        cursor = self.conn.cursor()

        # Prepare the query for events table
        fields = []
        placeholders = []
        values = []

        for key, value in event_info.items():
            if key != "id" and key != "tags":  # Skip ID and tags
                fields.append(key)
                placeholders.append("?")

                # Convert datetime objects to ISO format strings
                if isinstance(value, datetime):
                    value = value.isoformat()

                values.append(value)

        query = f"INSERT INTO events ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"

        try:
            cursor.execute(query, values)
            event_id = cursor.lastrowid

            # Add tags if provided
            if "tags" in event_info and event_info["tags"]:
                for tag in event_info["tags"]:
                    cursor.execute(
                        "INSERT INTO event_tags (event_id, tag) VALUES (?, ?)",
                        (event_id, tag)
                    )

            self.conn.commit()
            self.logger.info(f"Added event: {event_info['title']} (ID: {event_id})")
            return event_id
        except Exception as e:
            self.logger.error(f"Failed to add event: {e}")
            self.conn.rollback()
            return None

    def remove_event(self, event_id: int) -> bool:
        """
        Remove an event from the calendar.

        Args:
            event_id: ID of the event to remove

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            self.conn.commit()

            if cursor.rowcount > 0:
                self.logger.info(f"Removed event with ID {event_id}")
                return True
            else:
                self.logger.warning(f"Event with ID {event_id} not found, nothing to remove")
                return False
        except Exception as e:
            self.logger.error(f"Failed to remove event: {e}")
            self.conn.rollback()
            return False

    def update_event(self, event_id: int, event_info: Dict[str, Any]) -> bool:
        """
        Update an existing event.

        Args:
            event_id: ID of the event to update
            event_info: Dictionary containing updated event information

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()

        # Check if event exists
        cursor.execute("SELECT id FROM events WHERE id = ?", (event_id,))
        if not cursor.fetchone():
            self.logger.error(f"Cannot update event: event with ID {event_id} not found")
            return False

        # Prepare the query
        set_clauses = []
        values = []

        for key, value in event_info.items():
            if key != "id" and key != "tags":  # Skip ID and tags
                set_clauses.append(f"{key} = ?")

                # Convert datetime objects to ISO format strings
                if isinstance(value, datetime):
                    value = value.isoformat()

                values.append(value)

        # Add updated_at timestamp
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE events SET {', '.join(set_clauses)} WHERE id = ?"
        values.append(event_id)

        try:
            cursor.execute(query, values)

            # Update tags if provided
            if "tags" in event_info:
                # Remove existing tags
                cursor.execute("DELETE FROM event_tags WHERE event_id = ?", (event_id,))

                # Add new tags
                if event_info["tags"]:
                    for tag in event_info["tags"]:
                        cursor.execute(
                            "INSERT INTO event_tags (event_id, tag) VALUES (?, ?)",
                            (event_id, tag)
                        )

            self.conn.commit()
            self.logger.info(f"Updated event with ID {event_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update event: {e}")
            self.conn.rollback()
            return False

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an event by its ID.

        Args:
            event_id: ID of the event to retrieve

        Returns:
            Event information or None if not found
        """
        cursor = self.conn.cursor()

        try:
            # Get event information
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            event = cursor.fetchone()

            if not event:
                self.logger.warning(f"Event with ID {event_id} not found")
                return None

            event_dict = dict(event)

            # Get event tags
            cursor.execute("SELECT tag FROM event_tags WHERE event_id = ?", (event_id,))
            tags = [row["tag"] for row in cursor.fetchall()]
            event_dict["tags"] = tags

            return event_dict
        except Exception as e:
            self.logger.error(f"Failed to get event: {e}")
            return None

    def get_events_by_date(self, date: datetime, include_recurring: bool = True) -> List[Dict[str, Any]]:
        """
        Get events for a specific date.

        Args:
            date: The date to get events for
            include_recurring: Whether to include recurring events

        Returns:
            List of events on the specified date
        """
        cursor = self.conn.cursor()
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0).isoformat()
        end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59).isoformat()

        # Query for one-time events on the specified day
        query = """
        SELECT * FROM events 
        WHERE (start_time BETWEEN ? AND ?) 
        OR (end_time BETWEEN ? AND ?) 
        OR (start_time <= ? AND end_time >= ?)
        """

        params = [start_of_day, end_of_day, start_of_day, end_of_day, start_of_day, end_of_day]

        if include_recurring:
            # Add conditions for recurring events
            query += """
            OR (recurring IS NOT NULL 
                AND (recurring_end_date IS NULL OR recurring_end_date >= ?)
            )
            """
            params.append(start_of_day)

        try:
            cursor.execute(query, params)
            events = [dict(row) for row in cursor.fetchall()]

            # Filter out recurring events that don't occur on the specified date
            if include_recurring:
                filtered_events = []
                for event in events:
                    if event["recurring"]:
                        if self._is_recurring_event_on_date(event, date):
                            filtered_events.append(event)
                    else:
                        filtered_events.append(event)
                events = filtered_events

            # Add tags to each event
            for event in events:
                cursor.execute("SELECT tag FROM event_tags WHERE event_id = ?", (event["id"],))
                tags = [row["tag"] for row in cursor.fetchall()]
                event["tags"] = tags

            return events
        except Exception as e:
            self.logger.error(f"Failed to get events by date: {e}")
            return []

    def _is_recurring_event_on_date(self, event: Dict[str, Any], date: datetime) -> bool:
        """
        Check if a recurring event occurs on the specified date.

        Args:
            event: The recurring event to check
            date: The date to check against

        Returns:
            bool: True if the event occurs on the date, False otherwise
        """
        recurring_type = event["recurring"]
        start_time = datetime.fromisoformat(event["start_time"]) if isinstance(event["start_time"], str) else event[
            "start_time"]

        # Check if the date is before the event start date
        if date.date() < start_time.date():
            return False

        # Check if the date is after the event end date (if any)
        if event["recurring_end_date"]:
            end_date = datetime.fromisoformat(event["recurring_end_date"]) if isinstance(event["recurring_end_date"],
                                                                                         str) else event[
                "recurring_end_date"]
            if date.date() > end_date.date():
                return False

        # Check based on recurrence type
        if recurring_type == "daily":
            return True
        elif recurring_type == "weekly":
            return date.weekday() == start_time.weekday()
        elif recurring_type == "monthly":
            return date.day == start_time.day
        elif recurring_type == "yearly":
            return date.month == start_time.month and date.day == start_time.day
        elif recurring_type.startswith("weekdays"):
            return date.weekday() < 5  # Monday to Friday
        elif recurring_type.startswith("weekends"):
            return date.weekday() >= 5  # Saturday and Sunday