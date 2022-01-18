from unittest.mock import patch
from cli.pagerduty import PagerDuty
from pdpyras import PDClientError
from . import fixture_data as fd


@patch("cli.pagerduty.APISession")
def test_init(session):
    pd = PagerDuty("abc132")
    assert hasattr(pd, "session")
    assert pd.users == []
    assert pd.teams == []
    assert pd.services == []
    assert pd.schedules == []
    assert pd.escalations == []


@patch("cli.pagerduty.APISession")
def test_get_data_for_category(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.return_value = [{"foo": "bar"}, {"fizz": "buzz"}]
    data = pd.get_data_for_category("foo")
    assert data == [{"foo": "bar"}, {"fizz": "buzz"}]
    assert pd.session.iter_all.has_call("foo")


@patch("cli.pagerduty.APISession")
def test_get_data_for_category_failure(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.side_effect = PDClientError("foo")
    data = pd.get_data_for_category("bar")
    assert data == []
    assert pd.session.iter_all.has_call("bar")


@patch("cli.pagerduty.APISession")
def test_get_all_users(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.return_value = fd.users
    users = pd.get_all_users()
    assert fd.user_john in users
    assert fd.user_jane in users
    assert pd.session.iter_all.has_call("users")


@patch("cli.pagerduty.APISession")
def test_get_all_teams(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.return_value = fd.teams
    teams = pd.get_all_teams()
    assert teams == fd.teams
    assert pd.session.iter_all.has_call("teams")


@patch("cli.pagerduty.APISession")
def test_get_all_services(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.return_value = fd.services
    services = pd.get_all_services()
    assert services == fd.services
    assert pd.session.iter_all.has_call("services")


@patch("cli.pagerduty.APISession")
def test_get_details(session):
    pd = PagerDuty("abc132")
    pd.session.rget.return_value = {"foo": "bar"}
    data = pd.get_details("foo")
    assert data == {"foo": "bar"}
    assert pd.session.rget.has_call("foo")


@patch("cli.pagerduty.APISession")
def test_get_details_failure(session):
    pd = PagerDuty("abc132")
    pd.session.rget.side_effect = PDClientError("foo")
    data = pd.get_details("foo")
    assert data == {}
    assert pd.session.rget.has_call("foo")


@patch("cli.pagerduty.APISession")
def test_get_all_schedules(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.return_value = fd.schedules
    pd.session.rget.return_value = fd.schedule_details
    data = pd.get_all_schedules()
    assert fd.rendered_schedule in data
    assert pd.session.iter_all.has_call("schedules")
    assert pd.session.rget.has_call("schedules/abc123")


@patch("cli.pagerduty.APISession")
def test_get_all_escalations(session):
    pd = PagerDuty("abc132")
    pd.session.iter_all.return_value = fd.escalations
    data = pd.get_all_escalations()
    assert data == fd.rendered_escalation
    assert pd.session.iter_all.has_call("escalation_policies")


@patch("cli.pagerduty.APISession")
def test_get_team_members(session):
    pd = PagerDuty("abc132")
    pd.teams = [{"id": "abc123", "name": "test team"}]
    pd.session.rget.side_effect = [
        [
            {"user": {"id": "xyz789"}, "role": "manager"},
            {"user": {"id": "abc123"}, "role": "manager"},
        ],
        fd.users[1],
        fd.users[0],
    ]
    pd.get_team_members()
    assert pd.teams == [
        {
            "id": "abc123",
            "name": "test team",
            "members": ["xyz789", "abc123"],
            "manager": "xyz789",
        }
    ]
