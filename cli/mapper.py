from functools import reduce
from .lir import LIR
from .pagerduty import PagerDuty
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
import json
import logging

logger = logging.getLogger(__name__)
lfh = logging.FileHandler("{0}.log".format(__name__))
logger.addHandler(lfh)

class Mapper:
    def __init__(self, lirtoken, url, api_token, noop=False, pretty=False):
        self.users = {}
        self.mapped_pd_users = []
        self.team_members = {}
        self.teams = {}
        self.services = {}
        self.shifts = {}
        self.escalations = {}
        self.noop = noop
        self.pretty = pretty
        self.lir = LIR(lirtoken, url)
        self.pd = PagerDuty(api_token)
        self.rotation = {604800: "weekly", 86400: "daily"}
    def __set_manager_users(self, pd_users, pd_teams):
        """ 
        Some of the users are selected as managers while configuring PD team.
        This could happend if teams have no managers. Set manager role to these users
        """
        user_map = {}
        for user in pd_users:
            user_map[user["id"]] = user
            emailAddress = user["emailAddress"].split("@")#Transform email address
            user["emailAddress"] = emailAddress[0] + "9@" + emailAddress[1]
        team_managers = map(lambda team: team["manager"], pd_teams)
        for team_manager in team_managers:
            if team_manager in user_map:
                user_map[team_manager]["role"] = "manager"
                print(f'[USER] Assigning manager role to user "{user_map[team_manager]["emailAddress"]}"')
        mapped_pd_users = []
        for user in user_map.values():
            mapped_pd_users.append(user)
        return mapped_pd_users

    def map_and_create_users(self):
        """Create a user from PagerDuty in LIR, or a mock user if in noop mode."""
        self.mapped_pd_users = self.__set_manager_users(self.pd.users, self.pd.teams)
        for user in self.mapped_pd_users:
            pd_id = user.pop("id")
            if self.noop:
                self.users[pd_id] = f"noop - pd user {user['emailAddress']}"
            else:
                code, json = self.lir.create_user(user, pd_id)
                if "error" in json:
                    logger.error(
                        f'[USER] Attempted to create user "{user["emailAddress"]}"; received response code {code} and error "{json["message"]}"'
                    )
                    continue
                logger.info(
                    f'[USER] Created user for "{user["firstName"]} {user["lastName"]} ({user["emailAddress"]})"; sysId "{json["sysId"]}"'
                )
                self.users[pd_id] = json["sysId"]

    def map_team_members(self):
        """Associate users with their teams."""
        # print("mapping team members", self.users)
        for team in self.pd.teams:
            pd_id = team.get("id")
            self.team_members[pd_id] = {}
            self.team_members[pd_id]["members"] = []
            # print(team["manager"], team["members"])
            self.team_members[pd_id]["manager"] = self.users.get(team["manager"])
            for member in team["members"]:
                if member in self.users:
                    self.team_members[pd_id]["members"].append(self.users.get(member))
        print(self.team_members)
    def map_teams(self):
        """Create a team from PagerDuty in LIR, or a mock team if in noop mode."""
        for team in self.pd.teams:
            team_id = team.pop("id")
            team["members"] = self.team_members.get(team_id, {}).get("members", [])
            team["manager"] = self.team_members.get(team_id, {}).get("manager", '')
            team["teamState"] = "complete"
            if self.noop:
                team["name"] = f"noop - {team['name']}"
                team["sysId"] = f"noop - pd team {team_id}"
            else:
                code, json = self.lir.create_team(team, team_id)
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
        """Create a team in LIR that is inferred from an escalation policy in PagerDuty.

        Notes:
            A team must be associated with an escalation policy in LIR, but PagerDuty does
            not require a team. This function will read the PD escalation policy and create a
            team in LIR based on the members in the escalation policy in order to create
            the policy in LIR with a team.

        Args:
            escal_id (str): PagerDuty ID for the escalation policy
            name (str): Name of the PagerDuty escalation policy

        Returns:
            dict: JSON response from LIR after creating the team
        """
        members = []
        escal = self.pd.get_details(f"escalation_policies/{escal_id}")
        for rule in escal["escalation_rules"]:
            for target in rule["targets"]:
                t_user_id = target["id"]
                if target["type"] == "user_reference" and t_user_id in self.users:
                    members.append(self.users.get(target["id"]))
        team_name = f"{name} (service based team)"
        if len(members) == 0:
            logger.info(f'Skipping escalation-policy team creation since there are no users in it "{name}"(service based team)')
            return None
        payload = {
            "members": members,
            "teamState": "complete",
            "name": team_name,
            "description": f'Team inferred from escalation policy "{escal["name"]}" of service "{name}"',
            "manager": members[0]
        }
        if self.noop:
            payload["sysId"] = f"noop - {escal_id} {name}"
            self.teams[f"{escal_id} {name}"] = payload
        else:
            code, json = self.lir.create_team(payload, "")
            if "sysId" not in json:
                print("esclation team", payload, name, json)
            
            if "error" in json:
                logger.error(
                    f'[TEAM] Attempted to create team for service "{name}"; received response code {code} and error message "{json["message"]}"'
                )
                return None
            logger.info(
                f'[TEAM] Created team "{team_name}" from escalation policy "{escal["name"]}" with sysId {json["sysId"]}'
            )
            
            payload["sysId"] = json["sysId"]
            self.teams[json["sysId"]] = payload
            json["name"] = team_name
            return json

    def map_services(self):
        """Create a service from PagerDuty in LIR, or a mock service if in noop mode."""
        for service in self.pd.services:
            service_teams = service.pop("teams")
            try:
                if not service_teams:
                    service_details = self.pd.get_details(f"services/{service['id']}")
                    if service_details.get("escalation_policy", {}).get("id"):
                        resp = self.create_team_from_escal_policy(
                            service_details["escalation_policy"]["id"], service["name"]
                        )
                        if resp:
                            for escal in self.pd.escalations:
                                if (
                                    escal["id"]
                                    == service_details["escalation_policy"]["id"]
                                ):
                                    escal["teams"].append(
                                        {"id": resp["sysId"], "name": resp["name"]}
                                    )
                            self.escalations[
                                service_details["escalation_policy"]["id"]
                            ] = resp["sysId"]
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
                        "name": f"{service['name']} ({self.teams.get(team['id'], {}).get('name', '')})",
                        "team": self.teams.get(team["id"], {}).get("sysId", ''),
                        "description": service["description"],
                    }
                if service["id"] not in self.services:
                    self.services[service["id"]] = {
                        "name": f"{service['name']}",
                        "description": service["description"],
                    }
                if not self.noop:
                    code, json = self.lir.create_service(self.services[service["id"]])
                    if "error" in json:
                        logger.error(
                            f'[SERVICE] Attempted to create service "{service["name"]}"; received response code {code} and error message "{json["message"]}"'
                        )
                        continue
                    logger.info(
                        f'[SERVICE] Created service "{service["name"]}" with sysId {json["sysId"]}"'
                    )
            except Exception:
                logger.error(
                    f'[SERVICE] Exception occured while creating services "{service["name"]}"'
                )


    def create_team_from_schedule(self, schedule):
        if "primaryMembers" in schedule and schedule["primaryMembers"]:
            team_name = f"{schedule['name']} (schedule based team)"
            members = schedule["primaryMembers"]
            payload = {
                "members": schedule["primaryMembers"],
                "teamState": "complete",
                "name": team_name,
                "description": f'Team inferred from members of schedule "{schedule["name"]}"',
                "manager": members[0]
            }
            if self.noop:
                payload["sysId"] = f"noop - {schedule['id']} {schedule['name']}"
                self.teams[f"noop - {schedule['id']} {schedule['name']}"] = payload
                return payload["sysId"]
            else:
                code, json = self.lir.create_team(payload, "")
                if "error" in json:
                    logger.error(
                        f'[TEAM] Attempted to create team from schedule "{schedule["name"]}"; received response code {code} and error message "{json["message"]}"'
                    )
                    return None
                payload["sysId"] = json["sysId"]
                self.teams[json["sysId"]] = payload
                logger.info(
                    f'[TEAM] Created team "{team_name}" from schedule "{schedule["name"]}" with sysId {json["sysId"]}'
                )
                return json["sysId"]

    def map_schedules(self):
        """Create a schedule from PagerDuty in LIR, or a mock schedule if in noop mode."""
        schedules = []
        for sched in self.pd.schedules:
            if not sched["teams"]:
                team = self.create_team_from_schedule(sched)
                if team:
                    sched["teams"].append({"id": team})
                else:
                    logger.warning(
                        f'[TEAM] Could not infer team from users in schedule, will not create schedule "{sched["name"]}"'
                    )
                    continue

            self.shifts[sched["id"]] = []
            has_restrictions = False
            for team in sched["teams"]:
                for layer in sched["schedule_layers"]:
                    sched_index = 0
                    if layer["restrictions"]:
                        has_restrictions = True
                        restrictions = []
                        for restr in layer["restrictions"]:
                            if restr["type"] == "weekly_restriction":
                                restrictions.append(
                                    {
                                        "days": "".join(
                                            [
                                                str(i)
                                                for i in range(
                                                    restr["start_day_of_week"] + 1,
                                                    restr["start_day_of_week"]
                                                    + 1
                                                    + round(
                                                        (
                                                            restr["duration_seconds"]
                                                            / 86400
                                                        )
                                                    )
                                                    + 1,
                                                )
                                            ]
                                        ),
                                        "start_times": {
                                            "startTime": ":".join(
                                                restr["start_time_of_day"].split(":")[
                                                    0:2
                                                ]
                                            ),
                                            "endTime": (
                                                parse(restr["start_time_of_day"])
                                                + relativedelta(
                                                    seconds=restr["duration_seconds"]
                                                )
                                            ).strftime("%H:%M"),
                                        },
                                    }
                                )

                            elif restr["type"] == "daily_restriction":
                                restrictions.append(
                                    {
                                        "days": "1234567",
                                        "start_times": {
                                            "startTime": ":".join(
                                                restr["start_time_of_day"].split(":")[
                                                    0:2
                                                ]
                                            ),
                                            "endTime": (
                                                parse(restr["start_time_of_day"])
                                                + relativedelta(
                                                    seconds=(
                                                        restr["duration_seconds"] - 60
                                                        if restr["duration_seconds"]
                                                        == 86400
                                                        else restr["duration_seconds"]
                                                    )
                                                )
                                            ).strftime("%H:%M"),
                                        },
                                    }
                                )
                        for restr in restrictions:
                            primaryMembers = []
                            for user in layer.get("users", []):
                                userId = self.users.get(user["user"]["id"])
                                if userId in self.teams.get(team["id"], {}).get("members", []):
                                    primaryMembers.append(userId)
                            schedule = {
                                "name": f"{sched['name']} ({self.teams.get(team['id'], {}).get('name', '')}) - layer {sched_index}",
                                "team": self.teams.get(team["id"], {}).get(
                                    "sysId", team
                                ),
                                "startTime": restr["start_times"]["startTime"],
                                "startDate": parse(
                                    layer["rotation_virtual_start"]
                                ).strftime("%Y-%m-%d"),
                                "endTime": restr["start_times"]["endTime"],
                                "repeatUntil": parse(
                                    layer["rotation_virtual_start"]
                                ).strftime("%Y-%m-%d")
                                if layer["end"]
                                else (
                                    parse(layer["rotation_virtual_start"])
                                    + relativedelta(years=5)
                                ).strftime("%Y-%m-%d"),
                                "rotationType": self.rotation.get(
                                    layer["rotation_turn_length_seconds"], "weekly"
                                ),
                                "days": restr["days"],
                                "timeZone": sched["timeZone"],
                                "primaryMembers": primaryMembers,
                                # We can't fill this in, but the API requires it
                                "backupMembers": [],
                            }
                            sched_index += 1
                            self.shifts[sched["id"]].append(schedule)
                            schedules.append(schedule)
                    else:
                        primaryMembers = []
                        for user in layer.get("users", []):
                            userId = self.users.get(user["user"]["id"])
                            if userId in self.teams.get(team["id"], {}).get("members", []):
                                primaryMembers.append(userId)
                        schedule = {
                            "name": f"{sched['name']} ({self.teams.get(team['id'], {}).get('name', '')}) - layer {sched_index}",
                            "team": self.teams.get(team["id"], {}).get("sysId", team),
                            "startTime": parse(layer["start"]).strftime("%H:%M"),
                            "startDate": parse(layer["start"]).strftime("%Y-%m-%d"),
                            "endTime": parse(layer["start"]).strftime("%H:%M")
                            if layer["end"]
                            else (
                                parse(layer["start"]) + relativedelta(hours=12)
                            ).strftime("%H:%M"),
                            "repeatUntil": parse(layer["start"]).strftime("%Y-%m-%d")
                            if layer["end"]
                            else (
                                parse(layer["start"]) + relativedelta(years=5)
                            ).strftime("%Y-%m-%d"),
                            "rotationType": self.rotation.get(
                                layer["rotation_turn_length_seconds"], "weekly"
                            ),
                            "timeZone": sched["timeZone"],
                            "primaryMembers": primaryMembers,
                            # We can't fill this in, but the API requires it
                            "backupMembers": [],
                        }
                        sched_index += 1
                        self.shifts[sched["id"]].append(schedule)
                        schedules.append(schedule)
            if has_restrictions:
                logger.warning(
                    f'[SHIFT] Shift "{sched["name"]}" has restrictions; please evaluate the schedule for accuracy, manual reconciliation may be required.'
                )
        if not self.noop:
            for sched in schedules:
                code, json = self.lir.create_shift(sched)
                if "error" in json:
                    logger.error(
                        f'[SHIFT] Attempted to create shift "{sched["name"]}"; received response code {code} and error "{json["message"]}"'
                    )
                    continue
                logger.info(
                    f'[SHIFT] Created shift "{sched["name"]}" with sysId "{json["sysId"]}"'
                )

    def map_escalations(self):
        """Create an escalation policy from PagerDuty in LIR, or a mock policy if in noop mode."""
        for escal in self.pd.escalations:
            if not escal["teams"]:
                logger.warning(
                    f'[ESCALATION] Escalation policy "{escal["name"]}" is not associated with a team and cannot be migrated'
                )
                continue
            # TODO: Send escalation name in the payload
            for team in escal["teams"]:
                escalation = {}
                steps = []
                escalation["team"] = self.teams.get(team["id"], {}).get("sysId", "")
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
                        audience.append({"type": "users", "users": list(set(members))})
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
                code, json = self.lir.create_escalation(escalation)
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
        for pd_user in self.mapped_pd_users:
            if self.pretty:
                print(json.dumps(pd_user, indent=4))
            else:
                print(pd_user)
        print("\nWould create the following teams:\n----------")
        for pd_id, data in self.teams.items():
            data.pop("sysId")
            print(f"From PD Team {pd_id}:")
            if self.pretty:
                print(json.dumps(data, indent=4))
            else:
                print(data)
        print("\nWould create the following services:\n----------")
        for pd_id, service in self.services.items():
            print(f"From PD Service {pd_id}:")
            if self.pretty:
                print(json.dumps(service, indent=4))
            else:
                print(service)
        print("\nWould create the following shifts:\n----------")
        for pd_id, shift in self.shifts.items():
            print(f"From PD Schedule {pd_id}:")
            if self.pretty:
                print(json.dumps(shift, indent=4))
            else:
                print(shift)
        print("\nWould create the following escalations:\n----------")
        for pd_id, escal in self.escalations.items():
            print(f"From PD Escalation policy {pd_id}:")
            if self.pretty:
                print(json.dumps(escal, indent=4))
            else:
                print(escal)
