from locust import HttpUser, task, between

class PolicyUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def evaluate_policy(self):
        self.client.get("/api/policy/evaluate/policy:123")


#locust -f locustfile.py
