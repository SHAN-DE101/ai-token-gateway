import random
from locust import HttpUser, task, between

TENANT_KEYS = [
    "sk-gw-tenant-prod-001",
    "sk-gw-tenant-alpha-001",
]

MODELS = ["gpt-4o", "gemini-1.5-flash", "gemini-1.5-pro"]

class GatewayUser(HttpUser):
    wait_time = between(0.01, 0.05)  # Aggressive concurrent pacing

    @task(10)
    def test_chat_completions(self):
        key = random.choice(TENANT_KEYS)
        model = random.choice(MODELS)
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "x-trace-id": f"locust-trace-{random.randint(100000, 999999)}"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Benchmark token routing latency and quota commitment."}
            ]
        }
        with self.client.post("/v1/chat/completions", json=payload, headers=headers, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                # Expected when hitting rate-limit window ceiling
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def test_healthz(self):
        self.client.get("/healthz")

    @task(1)
    def test_revoked_key_isolation(self):
        # Must always be rejected with 403
        headers = {"Authorization": "Bearer sk-gw-tenant-revoked-999"}
        with self.client.post("/v1/chat/completions", json={"model": "gpt-4o", "messages": []}, headers=headers, catch_response=True) as resp:
            if resp.status_code == 403:
                resp.success()
            else:
                resp.failure(f"Revoked key was not blocked! Status: {resp.status_code}")
