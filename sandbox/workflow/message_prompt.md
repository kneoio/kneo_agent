Given incoming listener messages, generate a brief dialogue for the DJ.

Context:
- Detected intent: {detected}
- Tone: {tone}
- Sender(s): {sender}
- Text: {text}
- Action: {action}
- DJ: {ai_dj_name}
- Guest: {guest_name}

Voices:
- A: {voice_a}
- B: {voice_b}

Output strictly as a JSON array of objects like:
[
  {{"text": "...", "voice_id": "{voice_a}"}},
  {{"text": "...", "voice_id": "{voice_b}"}}
]
