import asyncio
import httpx

URL = "http://127.0.0.1:8000/api/policy/evaluate"

async def send_request(client, policy_id):
    payload = {"odrl_policy": {"uid": f"policy:{policy_id}"}}
    response = await client.post(URL, json=payload)
    print(f"Policy {policy_id}: {response.status_code} - {response.text}")

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, i) for i in range(1, 101)]  # 100 concurrent requests
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
