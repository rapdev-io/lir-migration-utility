import requests
import json


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
            response = requests.request("POST", url, headers=self.headers, data=payload)
            return response
        except requests.exceptions.RequestException as e:
            return e

    def create_user(self, payload):
        url = f"{self.url}/api/now/ir/user"
        response = self.post_request(url, json.dumps(payload))
        return response.json()

    def create_team(self, payload):
        url = f"{self.url}/api/now/ir/team"
        response = self.post_request(url, json.dumps(payload))
        return response

    def add_team_member(self, team, member):
        url = f"{self.url}/api/now/ir/team/{team}/members/add"
        payload = json.dumps({"member": member})
        response = self.post_request(url, payload)
        return response

    def create_team(self, payload):
        url = f"{self.url}/api/now/ir/service"
        response = self.post_request(url, json.dumps(payload))
        return response

    def create_team(self, payload):
        url = f"{self.url}/api/now/ir/shift"
        response = self.post_request(url, json.dumps(payload))
        return response

    def create_escalation(self, payload):
        url = f"{self.url}/api/now/ir/escalation_policy"
        response = self.post_request(url, json.dumps(payload))
        return response
