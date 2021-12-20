from pdpyras import APISession
import json


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
        return [data for data in self.session.iter_all(category)]

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
        return services

    def get_all_schedules(self):
        # need: starttime, endtime, startdate, repeatuntil, days, rotation type
        # possibly primary/backup members
        # Q: how do we define backup members?
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
        # Q: How do we handle a schedule with multiple teams?
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
                print(
                    f"Multiple managers found for team '{config['name']}', selecting {managers[0]['user']} as manager"
                )
                config["manager"] = managers[0]["id"]

    def get_service_data(self):
        # Q: how do we handle a service with multiple teams?
        for config in self.services.values():
            service = self.session.rget(f'services/{service["id"]}')
            config["team"] = service["teams"]


# pd = PagerDuty("u+Y33RtpsQusiBajGnQg")
# pd.get_team_members()
# print("")
