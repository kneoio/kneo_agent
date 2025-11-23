import pytest
import httpx
import asyncio

@pytest.mark.asyncio
async def test():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "http://localhost:38707/api/ai/brand/lumisonic/soundfragments",
            params={"keyword": "Rina"}
        )
        print(r.json())
