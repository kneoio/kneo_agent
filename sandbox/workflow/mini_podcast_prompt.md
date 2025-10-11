Generate a short 2-person radio dialogue (3–5 lines) between two DJs.
The main host is **{host_name}**, the co-host is **{guest_name}**.

**Song:** {song_title} by {song_artist}.
**Description:** {song_description}.
**Genres:** {genres}.

Include optional expressive tags (e.g. [excited], [whispers], [laughs], [sighs]) to shape emotional delivery.

Output strictly as a JSON array of objects like:
[
  {{"text": "[excited] Hi, this is {host_name} — welcome back!", "voice_id": "{voice_a}"}},
  {{"text": "[warm] Thanks {host_name}, happy to join in.", "voice_id": "{voice_b}"}}
]
