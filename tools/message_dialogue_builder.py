from mcp.server.llm_response import LlmResponse
from tools.dj_state import DJState
from util.file_util import debug_log

async def build_message_dialogue(self, state: DJState) -> DJState:
    song = state["song_fragments"][0]
    voice_a = self.agent_config.get("preferredVoice", "9BWtsMINqrJLrRacOk9x")
    voice_b = self.agent_config.get("secondaryVoice", "IKne3meq5aSn9XLyUdCD")
    guest_name = self.agent_config.get("secondaryVoiceName", "Music Expert")
    messages = state["messages"]

    if messages:
        senders = [m.get("from", "a listener") for m in messages]
        combined = " ".join(m.get("content", "") or "" for m in messages)
        sender = ", ".join(senders)
        text = combined.strip()
    else:
        sender = "a listener"
        text = ""

    tl = text.lower()
    debug_log(f"messages arrived: {messages}")

    lex = {
        "SHOUTOUT": [
            "shout out", "shoutout", "say hi", "hi to", "hello to", "hello", "hi",
            "hey", "what’s up", "greetings", "salut", "olá", "привет", "сәлем",
            "um abraço para", "beijo para", "olá para",
            "передай привет", "privet", "сәлем айт", "салем айт", "dedicate to", "dedication to"
        ],
        "CONGRATS": [
            "happy birthday", "hb", "congrats", "congratulations", "parabéns",
            "feliz aniversário", "с днём рождения", "с днем рождения",
            "құтты болсын", "туған күнің", "anniversary", "wedding",
            "new job", "graduation", "baby", "🎉", "🥳"
        ],
        "THANKS": [
            "thank you", "thanks", "love the show", "great show", "amazing", "awesome",
            "you rock", "adoro", "amo", "obrigado", "спасибо", "рахмет", "❤️", "🙏"
        ],
        "CONDOLENCES": [
            "rip", "condolences", "sorry for your loss", "rest in peace", "luto",
            "meus pêsames", "мои соболезнования", "қайғыңа ортақпын", "🖤", "🕯", "😢"
        ],
        "COMPLAINT": [
            "too loud", "ads", "commercials", "skip", "boring", "lag", "buffering",
            "not working", "bug", "problem", "issue", "broken", "terrible", "hate",
            "talk too much", "muitos anúncios", "publicidade", "реклама", "жарнама"
        ],
        "QUESTION": [
            "?", "when", "what", "who", "how", "onde", "quando", "como",
            "почему", "когда", "как", "where", "can you", "could you"
        ],
        "PROMO": [
            "event", "tonight", "today", "live", "ticket", "venue", "party", "festival",
            "release", "out now", "new single", "new album", "pre-save", "preorder",
            "launch", "aniversário", "birthday party"
        ],
    }

    scores = {k: 0 for k in lex}
    for k, words in lex.items():
        for w in words:
            if w == "?":
                scores[k] += 1 if "?" in tl else 0
            elif w in tl:
                scores[k] += 1

    detected = max(scores.items(), key=lambda x: x[1])[0] if any(scores.values()) else "GENERAL"

    tone = {
        "CONGRATS": "celebratory",
        "SHOUTOUT": "warm",
        "THANKS": "appreciative",
        "CONDOLENCES": "empathetic",
        "COMPLAINT": "calm and helpful",
        "QUESTION": "informative",
        "PROMO": "energetic",
        "GENERAL": "friendly",
    }[detected]

    action = {
        "CONGRATS": "deliver concise congratulations",
        "SHOUTOUT": "relay the listeners’ greetings to the audience and respond naturally",
        "THANKS": "acknowledge and thank the listener",
        "CONDOLENCES": "express brief condolences, keep it respectful",
        "COMPLAINT": "acknowledge the issue and promise to look into it without committing specifics",
        "QUESTION": "give a brief, direct answer if obvious; otherwise acknowledge and say you’ll check",
        "PROMO": "highlight the announcement briefly",
        "GENERAL": "react naturally and keep it light",
    }[detected]

    context = (
        f"DetectedIntent: {detected}\n"
        f"Tone: {tone}\n"
        f"Senders: {sender}\n"
        f"RawMessage: {text}\n"
        f"Instruction: {self.ai_dj_name} and {guest_name} should {action}."
    )

    context += (
        "\nAll listener messages are meant for on-air broadcast. "
        "DJs should speak to the audience, not directly to the sender. "
        "They are relaying what the listener said, possibly reacting or adding brief commentary."
    )


    prompt = (
        "Generate a short 2–4 line dialogue between two radio hosts as a JSON array of objects "
        "with keys 'text' and 'voice_id'. Keep lines concise; you may use brief tags like [warm], [excited], [soft].\n"
        + context
        + "\nIf DetectedIntent is SHOUTOUT, both hosts should briefly relay the listeners’ greeting to the audience and reply naturally on air.\n"
        f'Voices: host→{voice_a}, cohost→{voice_b}\n'
        f'Example: [{{"text":"[warm] Thanks for writing in!", "voice_id":"{voice_a}"}}, '
        f'{{"text":"[soft] We appreciate you, {sender}.", "voice_id":"{voice_b}"}}]'
    )

    response = await self.llm.ainvoke(messages=[{"role": "user", "content": prompt}])
    llm_response = LlmResponse.parse_structured_response(response, self.llm_type)
    song.introduction_text = llm_response.actual_result
    self.ai_logger.info(
        f"{self.brand} FINAL_RESULT (DIALOG): {llm_response.actual_result}, \nREASONING: {llm_response.reasoning}\n"
    )
    debug_log(f"Messages based dialogue intro: {song.introduction_text}, song: {song.title}, brand: {self.brand}")
    self._reset_message(state.get("messages"))
    return state
