from locust import HttpUser, task, between
import random

class TokenGatewayLoadUser(HttpUser):
    # Minimal wait time between 1ms and 5ms to hammer the gateway
    wait_time = between(0.001, 0.005)

    @task
    def post_completions(self):
        # Distribute across 500 virtual tenants so rate limiters don't bottle traffic on a single key
        tenant_id = random.randint(1, 500)
        self.client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer sk-gw-tenant-{tenant_id}"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Benchmark token proxy overhead."}]
            },
            name="/v1/chat/completions"
        )
