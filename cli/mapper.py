from air import AIR
from pagerduty import PagerDuty


class Mapper:
    def __init__(self, irtoken, url, api_token, noop=False):
        self.users = {}
        self.team_members = {}
        self.teams = {}
        self.services = {}
        self.shifts = {}
        self.noop = noop
        self.air = AIR(irtoken, url)
        self.pd = PagerDuty(api_token)

    def map_and_create_users(self):
        for user in self.pd.users:
            pd_id = user.pop("id")
            if self.noop:
                self.users[pd_id] = f"noop - pd user {user['emailAddress']}"
            else:
                air_user = self.air.create_user(user)
                self.users[pd_id] = air_user["sysId"]

    def map_team_members(self):
        for team in self.pd.teams:
            pd_id = team.get("id")
            self.team_members[pd_id] = {}
            self.team_members[pd_id]["members"] = []
            self.team_members[pd_id]["manager"] = self.users.get(team["manager"])
            for member in team["members"]:
                self.team_members[pd_id]["members"].append(self.users.get(member))

    def map_teams(self):
        for team in self.pd.teams:
            team_id = team.pop("id")
            team["members"] = self.team_members.get(team_id).get("members")
            team["manager"] = self.team_members.get(team_id).get("manager")
            if self.noop:
                team["name"] = f"noop - {team['name']}"
                team["sysId"] = f"noop - pd team {team_id}"
                self.teams[team_id] = team
            else:
                air_team = self.air.create_team(team)
                team["sysId"] = air_team["sysId"]
                self.teams[team_id] = team

    def map_services(self):
        for service in self.pd.services:
            service_teams = service.pop("teams")
            if not service_teams:
                self.services[service["id"]] = {
                    "name": f"{service['name']} (No Team Assigned)",
                    "description": service["description"],
                }
            for team in service_teams:
                self.services[service["id"]] = {
                    "name": f"{service['name']} ({self.teams.get(team['id']).get('name')})",
                    "team": self.teams.get(team["id"]).get("name"),
                    "description": service["description"],
                }
# {
#     "name": "Night Shift6",
#     "team": "3f06eca3b700011048e5f4dfbe11a92e",
#     "startTime": "02:00",
#     "endTime": "08:00",
#     "startDate": "2021-11-08",
#     "repeatUntil": "2022-11-10",
#     "days": "1234567",
#     "rotationType": "daily",
#     "timeZone": "America/Los_Angeles",
#     "primaryMembers": [
#         "69de204ab3a210102674a72256a8dc9e"
#     ],
#     "backupMembers": [
#         "69de204ab3a210102674a72256a8dc9e"
#     ]
# }
    def map_schedules(self):
        ...

m = Mapper(
    "271c720c1bdc099041654081b24bcb4e1234567890ab",
    "https://airworkertest3.service-now.com",
    "u+CYnCRVp2Wu3Zctvp8g",
    noop=True,
)

m.map_and_create_users()
m.map_team_members()
m.map_teams()
m.map_services()
print("")
