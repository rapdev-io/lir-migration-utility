from unittest.mock import patch
from cli.mapper import Mapper
from . import fixture_data as fd
import copy


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_mapper_init(pd, lir):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    assert mapper.users == {}
    assert mapper.team_members == {}
    assert mapper.teams == {}
    assert mapper.shifts == {}
    assert mapper.escalations == {}
    assert mapper.noop == False
    assert mapper.rotation == {604800: "weekly", 86400: "daily"}
    assert hasattr(mapper, "lir")
    assert hasattr(mapper, "pd")
    pd.assert_called_with("pdtoken")
    lir.assert_called_with("lirtoken", "http://example.com")


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_and_create_users_noop(pd, lir):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken", noop=True)
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.map_and_create_users()
    assert mapper.users == {
        "abc123": "noop - pd user john@example.com",
        "xyz789": "noop - pd user jane@example.com",
    }


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_and_create_users(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.lir.create_user.side_effect = [
        (200, {"sysId": "sysidabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_and_create_users()
    mapper.lir.create_user.assert_any_call(fd.lir_user_john)
    mapper.lir.create_user.assert_any_call(fd.lir_user_jane)
    assert mapper.users["abc123"] == "sysidabc123"
    assert (
        '[USER] Created user for "john doe (john@example.com)"; sysId "sysidabc123"'
        in caplog.messages
    )
    assert (
        '[USER] Attempted to create user "jane@example.com"; received response code 599 and error "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_team_members(pd, lir):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.teams = copy.deepcopy(fd.pd_teams)
    mapper.lir.create_user.side_effect = [
        (200, {"sysId": "abc123"}),
        (200, {"sysId": "xyz789"}),
    ]
    mapper.map_and_create_users()
    mapper.map_team_members()
    assert mapper.team_members == {
        "tabc123": {"members": ["abc123", "xyz789"], "manager": "xyz789"},
        "txyz789": {"members": ["abc123"], "manager": "abc123"},
    }


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_teams_noop(pd, lir):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken", noop=True)
    mapper.pd.teams = copy.deepcopy(fd.pd_teams)
    mapper.team_members = fd.pd_team_members
    mapper.map_teams()
    assert mapper.teams == {
        "tabc123": {
            "name": "noop - test team 1",
            "description": "a fabulous team",
            "members": ["abc123", "xyz789"],
            "manager": "xyz789",
            "teamState": "complete",
            "sysId": "noop - pd team tabc123",
        },
        "txyz789": {
            "name": "noop - test team 2",
            "description": "a decent team",
            "members": ["abc123"],
            "manager": "abc123",
            "teamState": "complete",
            "sysId": "noop - pd team txyz789",
        },
    }


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_teams(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.teams = copy.deepcopy(fd.pd_teams)
    mapper.team_members = fd.pd_team_members
    mapper.lir.create_team.side_effect = [
        (200, {"sysId": "qwe123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_teams()
    assert mapper.teams == {
        "tabc123": {
            "name": "test team 1",
            "description": "a fabulous team",
            "members": ["abc123", "xyz789"],
            "manager": "xyz789",
            "teamState": "complete",
            "sysId": "qwe123",
        }
    }
    assert '[TEAM] Created team "test team 1" with sysId qwe123' in caplog.messages
    assert (
        '[TEAM] Attempted to create team "test team 2"; received response code 599 and error message "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_escal_policy(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.get_details.side_effect = [fd.team_from_escalation]
    mapper.users = {"abc123": "sysIdabc123"}
    mapper.lir.create_team.side_effect = [(200, {"sysId": "foobar"})]
    resp = mapper.create_team_from_escal_policy("123", "test team policy")
    assert resp == {"sysId": "foobar", "name": "test team policy (service based team)"}
    mapper.pd.get_details.assert_called_with("escalation_policies/123")
    mapper.lir.create_team.assert_called_with(
        {
            "members": ["sysIdabc123"],
            "teamState": "complete",
            "name": "test team policy (service based team)",
            "description": 'Team inferred from escalation policy "test team policy (service based team)" of service "test team policy"',
            "manager": "sysIdabc123",
            "sysId": "foobar",
        }
    )
    assert (
        '[TEAM] Created team "test team policy (service based team)" from escalation policy "test team policy (service based team)" with sysId foobar'
        in caplog.messages
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_escal_policy_error(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.get_details.side_effect = [fd.team_from_escalation]
    mapper.users = {"abc123": "sysIdabc123"}
    mapper.lir.create_team.side_effect = [
        (599, {"error": True, "message": "this is an error"})
    ]
    resp = mapper.create_team_from_escal_policy("123", "test team policy")
    assert resp == None
    mapper.pd.get_details.assert_called_with("escalation_policies/123")
    mapper.lir.create_team.assert_called_with(
        {
            "members": ["sysIdabc123"],
            "teamState": "complete",
            "name": "test team policy (service based team)",
            "description": 'Team inferred from escalation policy "test team policy (service based team)" of service "test team policy"',
            "manager": "sysIdabc123",
        }
    )
    assert (
        '[TEAM] Attempted to create team for service "test team policy"; received response code 599 and error message "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_escal_policy_noop(pd, lir):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken", noop=True)
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.get_details.side_effect = [fd.team_from_escalation]
    mapper.users = {"abc123": "sysIdabc123"}
    resp = mapper.create_team_from_escal_policy("123", "test team policy")
    assert resp == None
    mapper.pd.get_details.assert_called_with("escalation_policies/123")
    mapper.lir.create_team.assert_not_called()
    assert mapper.teams == {
        "123 test team policy": {
            "members": ["sysIdabc123"],
            "teamState": "complete",
            "name": "test team policy (service based team)",
            "description": 'Team inferred from escalation policy "test team policy (service based team)" of service "test team policy"',
            "manager": "sysIdabc123",
            "sysId": "noop - 123 test team policy",
        }
    }


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_services(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.services = copy.deepcopy(fd.services)
    mapper.teams = {"abc123": {"sysId": "sysIdabc123", "name": "test team"}}
    mapper.lir.create_service.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_services()
    assert (
        '[SERVICE] Created service "important service" with sysId sysIdabc123"'
        in caplog.messages
    )
    assert (
        '[SERVICE] Attempted to create service "another important service"; received response code 599 and error message "this is an error"'
        in caplog.messages
    )
    assert mapper.services == {
        "abc123": {
            "name": "important service (test team)",
            "team": "sysIdabc123",
            "description": "foobar",
        },
        "xyz789": {
            "name": "another important service (test team)",
            "team": "sysIdabc123",
            "description": "fizzbuzz",
        },
    }


@patch("cli.mapper.Mapper.create_team_from_escal_policy")
@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_services_no_team(pd, lir, escal, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.services = copy.deepcopy(fd.services_no_teams)
    mapper.pd.get_details.side_effect = [{"escalation_policy": {"id": "abc123"}}, {}]
    escal.return_value = {"sysId": "sysIdabc123"}
    mapper.lir.create_service.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_services()
    mapper.pd.get_details.assert_any_call("services/abc123")
    mapper.pd.get_details.assert_any_call("services/xyz789")
    escal.assert_called_with("abc123", "important service")
    mapper.lir.create_service.assert_any_call(
        {"name": "important service", "description": "foobar", "team": "sysIdabc123"}
    )
    mapper.lir.create_service.assert_any_call(
        {
            "name": "another important service (No Team Assigned)",
            "description": "fizzbuzz",
        }
    )
    assert mapper.services == {
        "abc123": {
            "name": "important service",
            "description": "foobar",
            "team": "sysIdabc123",
        },
        "xyz789": {
            "name": "another important service (No Team Assigned)",
            "description": "fizzbuzz",
        },
    }
    assert (
        '[SERVICE] Created service "important service" with sysId sysIdabc123"'
        in caplog.messages
    )
    assert (
        '[SERVICE] There is no escalation policy associated with service "another important service" - cannot infer team members. Creating service without team.'
        in caplog.messages
    )
    assert (
        '[SERVICE] Attempted to create service "another important service"; received response code 599 and error message "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_schedule(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.lir.create_team.side_effect = [
        (200, {"sysId": "abc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    for sched in fd.schedules:
        mapper.create_team_from_schedule(sched)
    mapper.lir.create_team.assert_any_call(
        {
            "members": ["abc123", "xyz789"],
            "teamState": "complete",
            "name": "test schedule 0 (schedule based team)",
            "description": 'Team inferred from members of schedule "test schedule 0"',
            "manager": "abc123",
            "sysId": "abc123",
        }
    )
    mapper.lir.create_team.assert_any_call(
        {
            "members": ["abc123", "xyz789"],
            "teamState": "complete",
            "name": "test schedule 1 (schedule based team)",
            "description": 'Team inferred from members of schedule "test schedule 1"',
            "manager": "abc123",
        }
    )
    assert (
        '[TEAM] Created team "test schedule 0 (schedule based team)" from schedule "test schedule 0" with sysId abc123'
        in caplog.messages
    )
    assert (
        '[TEAM] Attempted to create team from schedule "test schedule 1"; received response code 599 and error message "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_schedule_noop(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken", noop=True)
    for sched in fd.schedules:
        mapper.create_team_from_schedule(sched)
    assert mapper.teams == {
        "noop - abc123 test schedule 0": {
            "members": ["abc123", "xyz789"],
            "teamState": "complete",
            "name": "test schedule 0 (schedule based team)",
            "description": 'Team inferred from members of schedule "test schedule 0"',
            "manager": "abc123",
            "sysId": "noop - abc123 test schedule 0",
        },
        "noop - abc123 test schedule 1": {
            "members": ["abc123", "xyz789"],
            "teamState": "complete",
            "name": "test schedule 1 (schedule based team)",
            "description": 'Team inferred from members of schedule "test schedule 1"',
            "manager": "abc123",
            "sysId": "noop - abc123 test schedule 1",
        },
    }


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_schedules(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.schedules = fd.schedules
    mapper.users = {"abc123": "abc123"}
    mapper.teams = {
        "txyz789": {
            "name": "test team 2",
            "description": "a decent team",
            "members": ["abc123"],
            "manager": "abc123",
            "sysId": "sysIdtxyz789",
        }
    }
    mapper.lir.create_shift.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (599, {"error": True, "message": "this is an error"}),
        (200, {"sysId": "sysIdabc123"}),
        (200, {"sysId": "sysIdabc123"}),
    ]
    mapper.lir.create_team.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (200, {"sysId": "sysIdabc123"}),
    ]
    mapper.map_schedules()
    assert mapper.shifts == fd.rendered_shifts
    assert (
        '[TEAM] Created team "test schedule 0 (schedule based team)" from schedule "test schedule 0" with sysId sysIdabc123'
        in caplog.messages
    )
    assert (
        '[SHIFT] Created shift "test schedule 0 (test schedule 0 (schedule based team)) - layer 0" with sysId "sysIdabc123"'
        in caplog.messages
    )
    assert (
        '[TEAM] Could not infer team from users in schedule, will not create schedule "test schedule 3"'
        in caplog.messages
    )
    assert (
        '[SHIFT] Attempted to create shift "test schedule 1 (test schedule 1 (schedule based team)) - layer 0"; received response code 599 and error "this is an error"'
        in caplog.messages
    )
    mapper.lir.create_shift.assert_any_call(
        {
            "name": "test schedule 0 (test schedule 0 (schedule based team)) - layer 0",
            "team": "sysIdabc123",
            "startTime": "21:00",
            "startDate": "2015-11-06",
            "endTime": "09:00",
            "repeatUntil": "2020-11-06",
            "rotationType": "daily",
            "timeZone": "America/New_York",
            "primaryMembers": ["abc123"],
            "backupMembers": [],
        }
    )
    mapper.lir.create_shift.assert_any_call(
        {
            "name": "test schedule 1 (test schedule 1 (schedule based team)) - layer 0",
            "team": "sysIdabc123",
            "startTime": "21:00",
            "startDate": "2015-11-06",
            "endTime": "09:00",
            "repeatUntil": "2020-11-06",
            "rotationType": "daily",
            "timeZone": "America/New_York",
            "primaryMembers": ["abc123"],
            "backupMembers": [],
        }
    )
    mapper.lir.create_shift.assert_any_call(
        {
            "name": "test schedule 2 (test team 2) - layer 0",
            "team": "sysIdtxyz789",
            "startTime": "21:00",
            "startDate": "2015-11-06",
            "endTime": "09:00",
            "repeatUntil": "2020-11-06",
            "rotationType": "daily",
            "timeZone": "America/New_York",
            "primaryMembers": ["abc123"],
            "backupMembers": [],
        }
    )


@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_map_escalations(pd, lir, caplog):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.pd.escalations = fd.rendered_escalation
    mapper.pd.schedules = fd.rendered_shifts
    mapper.users = {"abc123": "abc123"}
    mapper.shifts = fd.rendered_shifts
    mapper.teams = fd.mapper_teams
    mapper.lir.create_escalation.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_escalations()
    assert mapper.escalations == {
        "abc123": {
            "team": "sysIdxyz789",
            "steps": [
                {
                    "timeToNextStepInMins": 30,
                    "audience": [
                        {"type": "users", "users": ["abc123"]},
                        {"type": "users", "users": ["abc123"]},
                    ],
                }
            ],
            "priorities": [1],
        },
        "xyz789": {
            "team": "sysIdxyz789",
            "steps": [
                {
                    "timeToNextStepInMins": 30,
                    "audience": [{"type": "users", "users": ["abc123"]}],
                }
            ],
            "priorities": [1],
        },
    }
    assert (
        '[ESCALATION] Created escalation "escalation policy test" with sysId sysIdabc123'
        in caplog.messages
    )
    assert (
        '[ESCALATION] Escalation policy "escalation policy test no team" is not associated with a team and cannot be migrated'
        in caplog.messages
    )
    mapper.lir.create_escalation.assert_any_call(
        {
            "team": "sysIdxyz789",
            "steps": [
                {
                    "timeToNextStepInMins": 30,
                    "audience": [
                        {"type": "users", "users": ["abc123"]},
                        {"type": "users", "users": ["abc123"]},
                    ],
                }
            ],
            "priorities": [1],
        }
    )


@patch("builtins.print")
@patch("cli.mapper.LIR")
@patch("cli.mapper.PagerDuty")
def test_noop_output(pd, lir, _print):
    mapper = Mapper("lirtoken", "http://example.com", "pdtoken")
    mapper.users = {"abc123": "testuser"}
    mapper.teams = {"abc123": {"sysId": "sysabc123", "foo": "bar"}}
    mapper.services = {"abc123": {"service1": "example"}}
    mapper.shifts = {"abc123": {"test": "shift"}}
    mapper.escalations = {"abc123": {"test": "escalation"}}
    mapper.noop_output()
    _print.assert_any_call({"foo": "bar"})
    _print.assert_any_call({"service1": "example"})
    _print.assert_any_call({"test": "shift"})
    _print.assert_any_call({"test": "escalation"})
