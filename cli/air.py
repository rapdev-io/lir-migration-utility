import requests
import json
import logging

logger = logging.getLogger(__name__)


class AIR:
    def __init__(self, irtoken, url):

        self.url = url
        self.irtoken = irtoken
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"IRToken {self.irtoken}",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def post_request(self, url, payload):
        try:
            logger.debug(f"Sending POST request to {url} with payload: {payload}")
            response = self.session.post(url, data=payload)
            logger.debug(f"POST request to {url} returned code {response.status_code}")
            return response.status_code, response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Encountered request error to url {url}: {e}")
            return (599, {"error": True, "message": e})

    def create_user(self, payload):
        return self.post_request(f"{self.url}/api/now/ir/user", json.dumps(payload))

    def create_team(self, payload):
        return self.post_request(f"{self.url}/api/now/ir/team", json.dumps(payload))

    def create_service(self, payload):
        return self.post_request(f"{self.url}/api/now/ir/service", json.dumps(payload))

    def create_shift(self, payload):
        return self.post_request(f"{self.url}/api/now/ir/shift", json.dumps(payload))

    def create_escalation(self, payload):
        return self.post_request(
            f"{self.url}/api/now/ir/escalation_policy", json.dumps(payload)
        )
