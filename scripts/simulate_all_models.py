import asyncio
import random
import httpx

GATEWAY_URL = "http://127.0.0.1:8000/v1/chat/completions"

TENANTS = [
    "sk-gw-tenant-prod-001",
    "sk-gw-tenant-alpha-001",
    "sk-gw-tenant-live-888"
]

MODELS = [
    "gpt-4o",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "deepseek-ai/deepseek-v3",
    "meta-llama/llama-3.3-70b-instruct",
    "claude-3-5-sonnet",
    "gpt-4o-failing"  # Triggers cascade to Gemini
]

PROMPTS = [
    "Summarize customer feedback for Q3.",
    "Draft a concise product announcement.",
    "Explain micro-batch ClickHouse ingestion.",
    "Generate SQL for tenant cost attribution.",
    "Compare token pricing across models."
]

async def send_traffic(client, tenant, model, prompt):
    try:
        resp = await client.post(
            GATEWAY_URL,
            headers={
                "Authorization": f"Bearer {tenant}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": random.choice([True, False])
            },
            timeout=10.0
        )
        print(f"[{resp.status_code}] Key: {tenant[:16]}... | Model: {model} | Stream: {resp.headers.get('content-type', '')[:10]}")
    except Exception as e:
        print(f"Error sending request: {e}")

async def main():
    print("Firing 20 universal multi-model requests across tenants...")
    async with httpx.AsyncClient() as client:
        for _ in range(7):
            batch = [
                send_traffic(
                    client,
                    random.choice(TENANTS),
                    random.choice(MODELS),
                    random.choice(PROMPTS)
                )
                for _ in range(3)
            ]
            await asyncio.gather(*batch)
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
