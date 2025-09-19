
from typing import List, Dict, Any, Tuple


def flatten_data_for_prompt(events=None, history=None, listeners=None, genres=None, instant_messages=None) -> Tuple[
    str, str, str, str, str]:
    formatted_events = ""
    if events:
        formatted_events = "; ".join([
            f"Event: {event.get('type', 'unknown')} - {event.get('content', {}).get('description', str(event))}"
            for event in events
            if isinstance(event, dict)
        ])

    formatted_history = ""
    if history:
        formatted_history = "; ".join([
            f"{item.get('speaker', 'Unknown')}: {item.get('content', str(item))}"
            for item in history
            if isinstance(item, dict)
        ])

    formatted_listeners = ""
    if listeners:
        formatted_listeners = ", ".join([
            listener.get('name', listener.get('id', 'Anonymous'))
            for listener in listeners
            if isinstance(listener, dict)
        ])

    formatted_genres = ""
    if genres:
        formatted_genres = ", ".join([
            str(genre) for genre in genres
        ])

    formatted_messages = ""
    if instant_messages:
        formatted_messages = "; ".join([
            f"{msg.get('from', 'Anonymous')}: {msg.get('content', '')}"
            for msg in instant_messages
            if isinstance(msg, dict)
        ])

    return formatted_events, formatted_history, formatted_listeners, formatted_genres, formatted_messages


def format_events(events: List[Dict[str, Any]]) -> str:
    """Format a list of event objects into a readable string."""
    if not events:
        return ""

    return "; ".join([
        f"Event: {event.get('type', 'unknown')} - {event.get('content', {}).get('description', str(event))}"
        for event in events
        if isinstance(event, dict)
    ])


def format_history(history: List[Dict[str, Any]]) -> str:
    """Format conversation history into a readable string."""
    if not history:
        return ""

    return "; ".join([
        f"{item.get('speaker', 'Unknown')}: {item.get('content', str(item))}"
        for item in history
        if isinstance(item, dict)
    ])


def format_listeners(listeners: List[Dict[str, Any]]) -> str:
    """Format listener list into a readable string."""
    if not listeners:
        return ""

    return ", ".join([
        listener.get('name', listener.get('id', 'Anonymous'))
        for listener in listeners
        if isinstance(listener, dict)
    ])


def format_genres(genres: List[str]) -> str:
    """Format genre list into a readable string."""
    if not genres:
        return ""

    return ", ".join([str(genre) for genre in genres])


def format_messages(messages: List[Dict[str, Any]]) -> str:
    """Format instant messages into a readable string."""
    if not messages:
        return ""

    return "; ".join([
        f"{msg.get('from', 'Anonymous')}: {msg.get('content', '')}"
        for msg in messages
        if isinstance(msg, dict)
    ])