from unittest.mock import patch
from cli.mapper import Mapper
from . import fixture_data as fd
import copy


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_mapper_init(pd, air):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    assert mapper.users == {}
    assert mapper.team_members == {}
    assert mapper.teams == {}
    assert mapper.shifts == {}
    assert mapper.escalations == {}
    assert mapper.noop == False
    assert mapper.rotation == {604800: "weekly", 86400: "daily"}
    assert hasattr(mapper, "air")
    assert hasattr(mapper, "pd")
    pd.assert_called_with("pdtoken")
    air.assert_called_with("irtoken", "http://example.com")


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_and_create_users_noop(pd, air):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken", noop=True)
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.map_and_create_users()
    assert mapper.users == {
        "abc123": "noop - pd user john@example.com",
        "xyz789": "noop - pd user jane@example.com",
    }


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_and_create_users(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.air.create_user.side_effect = [
        (200, {"sysId": "sysidabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_and_create_users()
    mapper.air.create_user.assert_any_call(fd.air_user_john)
    mapper.air.create_user.assert_any_call(fd.air_user_jane)
    assert mapper.users["abc123"] == "sysidabc123"
    assert (
        '[USER] Created user for "john@example.com"; sysId "sysidabc123"'
        in caplog.messages
    )
    assert (
        '[USER] Attempted to create user "jane@example.com"; received response code 599 and error "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_team_members(pd, air):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.teams = copy.deepcopy(fd.pd_teams)
    mapper.air.create_user.side_effect = [
        (200, {"sysId": "abc123"}),
        (200, {"sysId": "xyz789"}),
    ]
    mapper.map_and_create_users()
    mapper.map_team_members()
    assert mapper.team_members == {
        "tabc123": {"members": ["abc123", "xyz789"], "manager": "xyz789"},
        "txyz789": {"members": ["abc123"], "manager": "abc123"},
    }


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_teams_noop(pd, air):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken", noop=True)
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


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_teams(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.teams = copy.deepcopy(fd.pd_teams)
    mapper.team_members = fd.pd_team_members
    mapper.air.create_team.side_effect = [
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


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_escal_policy(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.get_details.side_effect = [fd.team_from_escalation]
    mapper.users = {"abc123": "sysIdabc123"}
    mapper.air.create_team.side_effect = [(200, {"sysId": "foobar"})]
    resp = mapper.create_team_from_escal_policy("123", "test team policy")
    assert resp == {"sysId": "foobar"}
    mapper.pd.get_details.assert_called_with("escalation_policies/123")
    mapper.air.create_team.assert_called_with(
        {
            "members": ["sysIdabc123"],
            "teamState": "complete",
            "name": "test team policy (service based team)",
            "description": "Team inferred from escalation policy of service 'test team policy'",
        }
    )
    assert (
        '[TEAM] Created team "test team policy (service based team)" from escalation policy with sysId foobar'
        in caplog.messages
    )


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_escal_policy_error(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.get_details.side_effect = [fd.team_from_escalation]
    mapper.users = {"abc123": "sysIdabc123"}
    mapper.air.create_team.side_effect = [
        (599, {"error": True, "message": "this is an error"})
    ]
    resp = mapper.create_team_from_escal_policy("123", "test team policy")
    assert resp == None
    mapper.pd.get_details.assert_called_with("escalation_policies/123")
    mapper.air.create_team.assert_called_with(
        {
            "members": ["sysIdabc123"],
            "teamState": "complete",
            "name": "test team policy (service based team)",
            "description": "Team inferred from escalation policy of service 'test team policy'",
        }
    )
    assert (
        '[TEAM] Attempted to create team for service "test team policy"; received response code 599 and error message "this is an error"'
        in caplog.messages
    )


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_create_team_from_escal_policy_noop(pd, air):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken", noop=True)
    mapper.pd.users = copy.deepcopy(fd.pd_user_list)
    mapper.pd.get_details.side_effect = [fd.team_from_escalation]
    mapper.users = {"abc123": "sysIdabc123"}
    resp = mapper.create_team_from_escal_policy("123", "test team policy")
    assert resp == None
    mapper.pd.get_details.assert_called_with("escalation_policies/123")
    mapper.air.create_team.assert_not_called()
    assert mapper.teams == {
        "123 test team policy": {
            "members": ["sysIdabc123"],
            "teamState": "complete",
            "name": "test team policy (service based team)",
            "description": "Team inferred from escalation policy of service 'test team policy'",
            "sysId": "noop - 123 test team policy",
        }
    }


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_services(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.services = copy.deepcopy(fd.services)
    mapper.teams = {"abc123": {"sysId": "sysIdabc123", "name": "test team"}}
    mapper.air.create_service.side_effect = [
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
@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_services_no_team(pd, air, escal, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.services = copy.deepcopy(fd.services_no_teams)
    mapper.pd.get_details.side_effect = [{"escalation_policy": {"id": "abc123"}}, {}]
    escal.return_value = {"sysId": "sysIdabc123"}
    mapper.air.create_service.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_services()
    mapper.pd.get_details.assert_any_call("services/abc123")
    mapper.pd.get_details.assert_any_call("services/xyz789")
    escal.assert_called_with("abc123", "important service")
    mapper.air.create_service.assert_any_call(
        {"name": "important service", "description": "foobar", "team": "sysIdabc123"}
    )
    mapper.air.create_service.assert_any_call(
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


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_schedules(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
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
    mapper.air.create_shift.side_effect = [
        (200, {"sysId": "sysIdabc123"}),
        (599, {"error": True, "message": "this is an error"}),
    ]
    mapper.map_schedules()
    assert mapper.shifts == fd.rendered_shifts
    assert (
        '[SHIFT] Schedule "test schedule 1" does not have an associated team and cannot be migrated.'
        in caplog.messages
    )
    assert (
        '[SHIFT] Created shift "test schedule 2" with sysId "sysIdabc123"'
        in caplog.messages
    )
    assert (
        '[SHIFT] Attempted to create shift "test schedule 3"; received response code 599 and error "this is an error"'
        in caplog.messages
    )
    mapper.air.create_shift.assert_any_call(
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
    mapper.air.create_shift.assert_any_call(
        {
            "name": "test schedule 3 (test team 2) - layer 0",
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


@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_map_escalations(pd, air, caplog):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.pd.escalations = fd.rendered_escalation
    mapper.pd.schedules = fd.rendered_shifts
    mapper.users = {"abc123": "abc123"}
    mapper.shifts = fd.rendered_shifts
    mapper.teams = fd.mapper_teams
    mapper.air.create_escalation.side_effect = [
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
    mapper.air.create_escalation.assert_any_call(
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
@patch("cli.mapper.AIR")
@patch("cli.mapper.PagerDuty")
def test_noop_output(pd, air, _print):
    mapper = Mapper("irtoken", "http://example.com", "pdtoken")
    mapper.users = {"abc123": "testuser"}
    mapper.teams = {"abc123": {"sysId": "sysabc123", "foo": "bar"}}
    mapper.services = {"abc123": {"service1": "example"}}
    mapper.shifts = {"abc123": {"test": "shift"}}
    mapper.escalations = {"abc123": {"test": "escalation"}}
    mapper.noop_output()
    _print.assert_any_call("PD User ID: abc123 AIR User: testuser")
    _print.assert_any_call({"foo": "bar"})
    _print.assert_any_call({"service1": "example"})
    _print.assert_any_call({"test": "shift"})
    _print.assert_any_call({"test": "escalation"})
