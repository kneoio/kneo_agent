from typing import Any

def debug_log(message: str, data: Any = None):
    if data is not None:
        print(f"[DEBUG] {message}: {data}")
    else:
        print(f"[DEBUG] {message}")
