import asyncio
import httpx

async def send_req(client, i):
    resp = await client.post(
        "http://127.0.0.1:8000/v1/chat/completions",
        headers={"Authorization": "Bearer sk-gw-tenant-alpha-001"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": f"Ping {i}"}]}
    )
    return resp.status_code, resp.headers.get("retry-after")

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [send_req(client, i) for i in range(150)]
        results = await asyncio.gather(*tasks)
        
    success = sum(1 for code, _ in results if code == 200)
    rate_limited = sum(1 for code, _ in results if code == 429)
    retry_after = next((ra for code, ra in results if code == 429), None)
    
    print("\n================ RATE LIMIT TEST SUMMARY ================")
    print(f"Total Dispatched:    150")
    print(f"Accepted (200 OK):   {success}")
    print(f"Rate Limited (429):  {rate_limited}")
    print(f"Retry-After Header:  {retry_after}s")
    print("=========================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
