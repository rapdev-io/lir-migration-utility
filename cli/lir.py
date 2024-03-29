import requests
import json
import logging

logger = logging.getLogger(__name__)
lfh = logging.FileHandler("{0}.log".format(__name__))
logger.addHandler(lfh)


class LIR:
    def __init__(self, lirtoken, url):
        """Class for creating resources in LIR.

        Args:
            lirtoken (str): LIR authentication token
            url (str): Base URL of LIR instance
        """

        self.url = url
        self.lirtoken = lirtoken
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"IRToken {self.lirtoken}",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def post_request(self, url, payload):
        """Invokes a post request to LIR.

        Notes:
            When any kind of exception is returned, we log the error
            and swallow it, so as not to interupt the rest of the process.
            In this case, we return a 599 (just to keep the return format)
            and a dict with the error flag set to true, and the message.

        Args:
            url (str): API path for desired endpoint
            payload (str): json payload for API endpoint

        Returns:
            tuple: (status code, response json)
        """
        try:
            logger.debug(f"Sending POST request to {url} with payload: {payload}")
            response = self.session.post(url, data=payload)
            logger.debug(f"POST request to {url} returned code {response.status_code}")
            return response.status_code, response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Encountered request error to url {url}: {e}")
            return (599, {"error": True, "message": e})

    def create_user(self, payload):
        """Convenience method for creating a user.

        Args:
            payload (str): json payload for API endpoint

        Returns:
            tuple: (status code, response json)
        """
        return self.post_request(f"{self.url}/api/now/ir/user", json.dumps(payload))

    def create_team(self, payload):
        """Convenience method for creating a team.

        Args:
            payload (str): json payload for API endpoint

        Returns:
            tuple: (status code, response json)
        """
        return self.post_request(f"{self.url}/api/now/ir/team", json.dumps(payload))

    def create_service(self, payload):
        """Convenience method for creating a service.

        Args:
            payload (str): json payload for API endpoint

        Returns:
            tuple: (status code, response json)
        """
        return self.post_request(f"{self.url}/api/now/ir/service", json.dumps(payload))

    def create_shift(self, payload):
        """Convenience method for creating a shift.

        Args:
            payload (str): json payload for API endpoint

        Returns:
            tuple: (status code, response json)
        """
        return self.post_request(f"{self.url}/api/now/ir/shift", json.dumps(payload))

    def create_escalation(self, payload):
        """Convenience method for creating an escalation policy.

        Args:
            payload (str): json payload for API endpoint

        Returns:
            tuple: (status code, response json)
        """
        return self.post_request(
            f"{self.url}/api/now/ir/escalation_policy", json.dumps(payload)
        )
