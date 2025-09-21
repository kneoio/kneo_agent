from typing import Tuple

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
        formatted_events = "\n".join([
            f"- {event.get('type', 'UNKNOWN')}: {event.get('description', '')}"
            for event in events if isinstance(event, dict)
        ])

    formatted_history = ""
    if history:
        formatted_history = "\n".join([
            f"- Played: {item.get('title', '')} by {item.get('artist', '')}"
            for item in history if isinstance(item, dict)
        ])

    formatted_listeners = ""
    if listeners:
        formatted_listeners = "\n".join([
            f"- {listener.get('name', listener.get('id'))}"
            for listener in listeners if isinstance(listener, dict)
        ])

    formatted_genres = ""
    if genres:
        formatted_genres = "\n".join([
            f"- {str(genre)}" for genre in genres
        ])

    formatted_messages = ""
    if messages:
        formatted_messages = "\n".join([
            f"- Message from {msg.get('name') or msg.get('from', 'Unknown')}: {msg.get('content', '')}"
            for msg in messages if isinstance(msg, dict)
        ])

    formatted_context = ""
    if context:
        if isinstance(context, list) and len(context) == 1 and isinstance(context[0], dict):
            formatted_context = "\n".join([
                f"- {k}: {v}" for k, v in context[0].items() if v
            ])
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
