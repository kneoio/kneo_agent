from typing import List, Dict, Any, Tuple


def flatten_data_for_prompt(
    events=None,
    history=None,
    listeners=None,
    genres=None,
    messages=None,
    context=None
) -> Tuple[str, str, str, str, str, str]:
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
        formatted_genres = ", ".join([str(genre) for genre in genres])

    formatted_messages = "; ".join([
        f"Message from {msg.get('from', 'Anonymous')}: {msg.get('content', '')}"
        for msg in messages
        if isinstance(msg, dict)
    ])

    formatted_context = ""
    if context:
        if isinstance(context, list) and len(context) == 1 and isinstance(context[0], dict):
            formatted_context = ", ".join([f"{k}: {v}" for k, v in context[0].items() if v])
        else:
            formatted_context = str(context)

    return (
        formatted_events,
        formatted_history,
        formatted_listeners,
        formatted_genres,
        formatted_messages,
        formatted_context,
    )
