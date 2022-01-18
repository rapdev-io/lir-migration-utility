from .air import AIR
from .pagerduty import PagerDuty
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


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
        """Create a user from PagerDuty in AIR, or a mock user if in noop mode."""
        for user in self.pd.users:
            pd_id = user.pop("id")
            if self.noop:
                self.users[pd_id] = f"noop - pd user {user['emailAddress']}"
            else:
                code, json = self.air.create_user(user)
                if "error" in json:
                    logger.error(
                        f'[USER] Attempted to create user "{user["emailAddress"]}"; received response code {code} and error "{json["message"]}"'
                    )
                    continue
                logger.info(
                    f'[USER] Created user for "{user["emailAddress"]}"; sysId "{json["sysId"]}"'
                )
                self.users[pd_id] = json["sysId"]

    def map_team_members(self):
        """Associate users with their teams."""
        for team in self.pd.teams:
            pd_id = team.get("id")
            self.team_members[pd_id] = {}
            self.team_members[pd_id]["members"] = []
            self.team_members[pd_id]["manager"] = self.users.get(team["manager"])
            for member in team["members"]:
                self.team_members[pd_id]["members"].append(self.users.get(member))

    def map_teams(self):
        """Create a team from PagerDuty in AIR, or a mock team if in noop mode."""
        for team in self.pd.teams:
            team_id = team.pop("id")
            team["members"] = self.team_members.get(team_id).get("members")
            team["manager"] = self.team_members.get(team_id).get("manager")
            team["teamState"] = "complete"
            if self.noop:
                team["name"] = f"noop - {team['name']}"
                team["sysId"] = f"noop - pd team {team_id}"
            else:
                code, json = self.air.create_team(team)
                if "error" in json:
                    logger.error(
                        f'[TEAM] Attempted to create team "{team["name"]}"; received response code {code} and error message "{json["message"]}"'
                    )
                    continue
                team["sysId"] = json["sysId"]
                logger.info(
                    f'[TEAM] Created team "{team["name"]}" with sysId {json["sysId"]}'
                )
            self.teams[team_id] = team

    def create_team_from_escal_policy(self, escal_id, name):
        """Create a team in AIR that is inferred from an escalation policy in PagerDuty.

        Notes:
            A team must be associated with an escalation policy in AIR, but PagerDuty does
            not require a team. This function will read the PD escalation policy and create a
            team in AIR based on the members in the escalation policy in order to create
            the policy in AIR with a team.

        Args:
            escal_id (str): PagerDuty ID for the escalation policy
            name (str): Name of the PagerDuty escalation policy

        Returns:
            dict: JSON response from AIR after creating the team
        """
        members = []
        escal = self.pd.get_details(f"escalation_policies/{escal_id}")
        for rule in escal["escalation_rules"]:
            for target in rule["targets"]:
                if target["type"] == "user_reference":
                    members.append(self.users.get(target["id"]))
        team_name = f"{name} (service based team)"
        payload = {
            "members": members,
            "teamState": "complete",
            "name": team_name,
            "description": f"Team inferred from escalation policy of service '{name}'",
        }
        if self.noop:
            payload["sysId"] = f"noop - {escal_id} {name}"
            self.teams[f"{escal_id} {name}"] = payload
        else:
            code, json = self.air.create_team(payload)
            if "error" in json:
                logger.error(
                    f'[TEAM] Attempted to create team for service "{name}"; received response code {code} and error message "{json["message"]}"'
                )
                return None
            logger.info(
                f'[TEAM] Created team "{team_name}" from escalation policy with sysId {json["sysId"]}'
            )
            return json

    def map_services(self):
        """Create a service from PagerDuty in AIR, or a mock service if in noop mode."""
        for service in self.pd.services:
            service_teams = service.pop("teams")
            if not service_teams:
                service_details = self.pd.get_details(f"services/{service['id']}")
                if service_details.get("escalation_policy", {}).get("id"):
                    resp = self.create_team_from_escal_policy(
                        service_details["escalation_policy"]["id"], service["name"]
                    )
                    if resp:
                        self.services[service["id"]] = {
                            "name": f"{service['name']}",
                            "description": service["description"],
                            "team": resp["sysId"],
                        }
                else:
                    logger.info(
                        f'[SERVICE] There is no escalation policy associated with service "{service["name"]}" - cannot infer team members. Creating service without team.'
                    )
                    self.services[service["id"]] = {
                        "name": f"{service['name']} (No Team Assigned)",
                        "description": service["description"],
                    }
            for team in service_teams:
                self.services[service["id"]] = {
                    "name": f"{service['name']} ({self.teams.get(team['id']).get('name')})",
                    "team": self.teams.get(team["id"]).get("sysId"),
                    "description": service["description"],
                }
            if not self.noop:
                code, json = self.air.create_service(self.services[service["id"]])
                if "error" in json:
                    logger.error(
                        f'[SERVICE] Attempted to create service "{service["name"]}"; received response code {code} and error message "{json["message"]}"'
                    )
                    continue
                logger.info(
                    f'[SERVICE] Created service "{service["name"]}" with sysId {json["sysId"]}"'
                )

    def map_schedules(self):
        """Create a schedule from PagerDuty in AIR, or a mock schedule if in noop mode."""
        for sched in self.pd.schedules:
            if not sched["teams"]:
                logger.warning(
                    f'[SHIFT] Schedule "{sched["name"]}" does not have an associated team and cannot be migrated.'
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
                        else (parse(layer["start"]) + relativedelta(hours=12)).strftime(
                            "%H:%M"
                        ),
                        "repeatUntil": parse(layer["start"]).strftime("%Y-%m-%d")
                        if layer["end"]
                        else (parse(layer["start"]) + relativedelta(years=5)).strftime(
                            "%Y-%m-%d"
                        ),
                        "rotationType": self.rotation.get(
                            layer["rotation_turn_length_seconds"], "weekly"
                        ),
                        "timeZone": sched["timeZone"],
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
                        logger.error(
                            f'[SHIFT] Attempted to create shift "{sched["name"]}"; received response code {code} and error "{json["message"]}"'
                        )
                        continue
                    logger.info(
                        f'[SHIFT] Created shift "{sched["name"]}" with sysId "{json["sysId"]}"'
                    )

    def map_escalations(self):
        """Create an escalation policy from PagerDuty in AIR, or a mock policy if in noop mode."""
        for escal in self.pd.escalations:
            if not escal["teams"]:
                logger.warning(
                    f'[ESCALATION] Escalation policy "{escal["name"]}" is not associated with a team and cannot be migrated'
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
                        members = []
                        if target["type"] == "user_reference":
                            members.append(self.users.get(target["id"]))

                        elif target["type"] == "schedule_reference":

                            schedule = self.shifts.get(target["id"])
                            for layer in schedule:
                                members += layer["primaryMembers"]
                        else:
                            logger.warning(
                                f'[ESCALATION] Cannot migrate target type "{target["type"]}" for step {rule_index} in escalation "{escal["name"]}"'
                            )
                            continue
                        audience.append({"type": "users", "users": members})
                    if audience:
                        step["audience"] = audience
                        steps.append(step)
                        escalation["steps"] = steps
                    else:
                        logger.warning(
                            f'[ESCALATION] No audience for rule {rule_index} in escalation "{escal["name"]}" - skipping layer.'
                        )
                    rule_index += 1
            if "steps" in escalation:
                escalation["priorities"] = [
                    i for i in range(1, len(escalation["steps"]) + 1)
                ]
                self.escalations[escal["id"]] = escalation
            else:
                logger.warning(
                    f'[ESCALATION] No steps found or no audience found for escalation "{escal["name"]}" - cannot migrate.'
                )
                continue
            if not self.noop:
                code, json = self.air.create_escalation(escalation)
                if "error" in json:
                    logger.error(
                        f'[ESCALATION] Attempted to create escalation "{escal["name"]}"; received response code {code} and error "{json["message"]}"'
                    )
                    continue
                logger.info(
                    f'[ESCALATION] Created escalation "{escal["name"]}" with sysId {json["sysId"]}'
                )

    def noop_output(self):
        """Print a noop report to console."""
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
