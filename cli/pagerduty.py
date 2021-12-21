from pdpyras import APISession, PDClientError
import logging

logger = logging.getLogger(__name__)


class PagerDuty:
    def __init__(self, api_token):
        self.session = APISession(api_token)
        self.users = self.get_all_users()
        self.teams = self.get_all_teams()
        self.get_team_members()
        self.services = self.get_all_services()
        self.schedules = self.get_all_schedules()
        self.escalations = self.get_all_escalations()

    def get_data_for_category(self, category):
        logger.debug(f"Getting data for category {category}.")
        try:
            response = [data for data in self.session.iter_all(category)]
        except PDClientError as e:
            logger.error(f"Error from PagerDuty API: {e}")
            return []
        return response

    def get_all_users(self):
        """Returns a dictionary of all users in the target PagerDuty account.

        Returns:
            dict: The key is the email of the user, and the value are the values expected
                  by AIR to be able to create a user.
        """
        users = []
        for user in self.get_data_for_category("users"):
            name = user["name"].split()
            users.append(
                {
                    "id": user["id"],
                    "firstName": name[0],
                    # It's possible to enter a single name in PagerDuty. If there is only
                    # one name, use it as the last name too. name[1:] accounts for names
                    # with multiple words, like "van winkle".
                    "lastName": " ".join(name[1:]) if len(name) > 1 else name[0],
                    "emailAddress": user["email"],
                    "role": user["role"],
                    "bio": user["description"],
                }
            )
        logger.debug(f"Gathered the following users: {users}")
        return users

    def get_all_teams(self):
        teams = []
        for team in self.get_data_for_category("teams"):
            teams.append(
                {
                    "id": team["id"],
                    "name": team["name"],
                    "description": team["description"],
                }
            )
        logging.debug(f"Gathered the following teams: {teams}")
        return teams

    def get_all_services(self):
        services = []
        for service in self.get_data_for_category("services"):
            services.append(
                {
                    "id": service["id"],
                    "description": service["description"],
                    "teams": service["teams"],
                    "name": service["name"],
                }
            )
        logging.debug(f"Gathered the following services: {services}")
        return services

    def get_details(self, endpoint):
        try:
            response = self.session.rget(endpoint)
            return response
        except PDClientError as e:
            logger.error(f"Request to endpont {endpoint} failed: {e}")
            return {}

    def get_all_schedules(self):
        schedules = []
        for schedule in self.get_data_for_category("schedules"):
            details = self.session.rget(f"schedules/{schedule['id']}")
            schedules.append(
                {
                    "name": schedule["name"],
                    "id": schedule["id"],
                    "timeZone": schedule["time_zone"],
                    "primaryMembers": [user["id"] for user in schedule["users"]],
                    "schedule_layers": details["schedule_layers"],
                    "teams": details["teams"],
                }
            )
        return schedules

    def get_all_escalations(self):
        escalations = []
        for escalation in self.get_data_for_category("escalation_policies"):
            escalations.append(
                {
                    "id": escalation["id"],
                    "rules": escalation["escalation_rules"],
                    "teams": escalation["teams"],
                    "name": escalation["name"],
                }
            )
        return escalations

    def get_team_members(self):
        for config in self.teams:
            config["members"] = []
            config["manager"] = ""
            # There may be multiple managers
            managers = []
            members = self.session.rget(f'teams/{config["id"]}/members')
            for member in members:
                config["members"].append(member["user"]["id"])
                if member["role"] == "manager":
                    managers.append(
                        {
                            "user": self.session.rget(f'/users/{member["user"]["id"]}')[
                                "email"
                            ],
                            "id": member["user"]["id"],
                        }
                    )
            if len(managers) > 1:
                logger.info(
                    f"Multiple managers found for team '{config['name']}', selecting {managers[0]['user']} as manager"
                )
                config["manager"] = managers[0]["id"]
