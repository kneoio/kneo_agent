import asyncio
from repos.interaction_log_repo import interaction_log_repo

async def check_logs():
    # Get recent logs for a brand
    logs = await interaction_log_repo.get_by_brand('SunoNation', limit=5)
    
    for log in logs:
        print(f"\n=== Event: {log['event_type']} ===")
        print(f"Timestamp: {log['timestamp']}")
        print(f"Message: {log['message']}")
        print(f"Metadata: {log['metadata']}")
        if log['metadata']:
            if 'full_prompt' in log['metadata']:
                print(f"Full Prompt: {log['metadata']['full_prompt'][:200]}...")
            if 'response_content' in log['metadata']:
                print(f"Response: {log['metadata']['response_content'][:200]}...")

if __name__ == "__main__":
    asyncio.run(check_logs())
