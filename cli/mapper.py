from air import AIR
from pagerduty import PagerDuty
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from pprint import pprint


class Mapper:
    def __init__(self, irtoken, url, api_token, noop=False):
        self.users = {}
        self.team_members = {}
        self.teams = {}
        self.services = {}
        self.shifts = {}
        self.escalations = {}
        self.noop = noop
        self.air = AIR(irtoken, url)
        self.pd = PagerDuty(api_token)
        self.rotation = {604800: "weekly", 86400: "daily"}

    def map_and_create_users(self):
        for user in self.pd.users:
            pd_id = user.pop("id")
            if self.noop:
                self.users[pd_id] = f"noop - pd user {user['emailAddress']}"
            else:
                code, json = self.air.create_user(user)
                if "error" in json:
                    print(
                        f'Attempted to create user "{user["emailAddress"]}"; received response code {code} and error "{json["message"]}"'
                    )
                    continue
                print(
                    f'Created user for "{user["emailAddress"]}"; sysId "{json["sysId"]}"'
                )
                self.users[pd_id] = json["sysId"]

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
            team["teamState"] = 'complete'
            if self.noop:
                team["name"] = f"noop - {team['name']}"
                team["sysId"] = f"noop - pd team {team_id}"
            else:
                code, json = self.air.create_team(team)
                if "error" in json:
                    print(
                        f'Attempted to create team "{team["name"]}"; received response code {code} and error message "{json["message"]}"'
                    )
                    continue
                team["sysId"] = json["sysId"]
                print(f'Created team "{team["name"]}" with sysId {json["sysId"]}')
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
            if not self.noop:
                code, json = self.air.create_service(self.services[service["id"]])
                if "error" in json:
                    print(
                        f'Attempted to create service "{service["name"]}"; received response code {code} and error message "{json["message"]}"'
                    )
                    continue
                print(
                    f'Created service "{service["name"]}" with sysId {json["sysId"]}"'
                )

    def map_schedules(self):
        for sched in self.pd.schedules:
            if not sched["teams"]:
                print(
                    f'Schedule {sched["name"]} does not have an associated team and cannot be migrated.'
                )
                continue
            sched_index = 0
            self.shifts[sched["id"]] = []
            for team in sched["teams"]:
                for layer in sched["schedule_layers"]:
                    schedule = {
                        "name": f"{sched['name']} ({self.teams.get(team['id'])['name']}) - layer {sched_index}",
                        "team": self.teams.get(team["id"])["sysId"],
                        "startTime": parse(layer["start"]).strftime("%H:%M"),
                        "startDate": parse(layer["start"]).strftime("%Y-%m-%d"),
                        "endTime": parse(layer["start"]).strftime("%H:%M")
                        if layer["end"]
                        else (parse(layer["start"]) + relativedelta(hours=12)).strftime("%H:%M"),
                        "repeatUntil": parse(layer["start"]).strftime("%Y-%m-%d")
                        if layer["end"]
                        else (parse(layer["start"]) + relativedelta(years=5)).strftime(
                            "%Y-%m-%d"
                        ),
                        "rotationType": self.rotation.get(
                            layer["rotation_turn_length_seconds"], "weekly"
                        ),
                        "timeZone": sched["timeZone"],
                        # Can only include members that are part of the team assigned to the shift
                        "primaryMembers": [
                            self.users.get(user["user"]["id"])
                            for user in layer["users"]
                            if self.users.get(user["user"]["id"])
                            in self.teams.get(team["id"])["members"]
                        ],
                        # We can't fill this in, but the API requires it
                        "backupMembers": [],
                    }
                    sched_index += 1
                    self.shifts[sched["id"]].append(schedule)
                if not self.noop:
                    code, json = self.air.create_shift(schedule)
                    if "error" in json:
                        print(
                            f'Attempted to create shift "{sched["name"]}"; received response code {code} and error "{json["message"]}"'
                        )
                        continue
                    print(
                        f'Created shift "{sched["name"]}" with sysId "{json["sysId"]}"'
                    )

    def map_escalations(self):
        for escal in self.pd.escalations:
            if not escal["teams"]:
                print(
                    f'Escalation policy "{escal["name"]}" is not associated with a team and cannot be migrated'
                )
                continue
            for team in escal["teams"]:
                escalation = {}
                steps = []
                escalation["team"] = self.teams.get(team["id"])["sysId"]
                rule_index = 0
                for rule in escal["rules"]:
                    step = {}
                    audience = []
                    if rule["escalation_delay_in_minutes"]:
                        step["timeToNextStepInMins"] = rule[
                            "escalation_delay_in_minutes"
                        ]
                    for target in rule["targets"]:
                        if target["type"] == "user_reference":
                            audience.append(
                                {
                                    "type": "users",
                                    "users": [self.users.get(target["id"])],
                                }
                            )
                        else:
                            print(
                                f'Cannot migrate target type {target["type"]} for step {rule_index} in escalation {escal["name"]}'
                            )
                            continue
                    if audience:
                        step["audience"] = audience
                        steps.append(step)
                        escalation["steps"] = steps
                    else:
                        print(
                            f'No audience for rule {rule_index} in escalation "{escal["name"]}"'
                        )
                    rule_index += 1
            if "steps" in escalation:
                escalation["priorities"] = [
                    i for i in range(1, len(escalation["steps"]) + 1)
                ]
                self.escalations[escal["id"]] = escalation
            else:
                print(
                    f'No steps found or no audience found for escalation "{escal["name"]}" - cannot migrate.'
                )
            if not self.noop:
                code, json = self.air.create_escalation(escalation)
                if "error" in json:
                    print(
                        f'Attempted to create escalation "{escal["name"]}"; received response code {code} and error "{json["message"]}"'
                    )
                    continue
                print(
                    f'Created escalation "{escal["name"]}" with sysId {json["sysId"]}'
                )

    def noop_output(self):
        print("\nWould create the following users:\n----------")
        for pd_user, air_user in self.users.items():
            print(f"PD User ID: {pd_user} AIR User: {air_user}")
        print("\nWould create the following teams:\n----------")
        for pd_id, data in self.teams.items():
            data.pop("sysId")
            print(f"From PD Team {pd_id}:")
            print(data)
        print("\nWould create the following services:\n----------")
        for pd_id, service in self.services.items():
            print(f"From PD Service {pd_id}:")
            print(service)
        print("\nWould create the following shifts:\n----------")
        for pd_id, shift in self.shifts.items():
            print(f"From PD Schedule {pd_id}:")
            print(shift)
        print("\nWould create the following escalations:\n----------")
        for pd_id, escal in self.escalations.items():
            print(f"From PD Escalation policy {pd_id}:")
            print(escal)


m = Mapper(
    "271c720c1bdc099041654081b24bcb4e1234567890ab",
    "https://airworkertest3.service-now.com",
    "u+Y33RtpsQusiBajGnQg",
    noop=False,
)

m.map_and_create_users()
m.map_team_members()
m.map_teams()
m.map_services()
m.map_schedules()
m.map_escalations()
m.noop_output()
print("")


# based on the service, create a virtual team based on the assigned users
# based on the shift, add all users present in a layer at the primary members only if there is a team associated with the shift
# for escalation policies, only create the escalation if there is a team associatied
# if there are not teams associatied with a shift or escalation, log a warning that the migration could not be completed
