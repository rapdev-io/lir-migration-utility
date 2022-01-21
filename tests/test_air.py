from requests.exceptions import RequestException
import requests_mock
from cli.lir import LIR
from unittest.mock import patch
import json


def test_init():
    lir = LIR("testtoken", "http://example.com")
    assert lir.url == "http://example.com"
    assert lir.lirtoken == "testtoken"
    assert lir.headers == {
        "Content-Type": "application/json",
        "Authorization": f"IRToken testtoken",
    }
    assert lir.session is not None
    assert lir.session.headers.get("Content-Type") == "application/json"
    assert lir.session.headers.get("Authorization") == "IRToken testtoken"


def test_post_request():
    with requests_mock.Mocker() as mock_post:
        mock_post.post("http://example.com", json={"foo": "bar"})
        lir = LIR("testtoken", "http://example.com")
        resp = lir.post_request("http://example.com", {"foo": "bar"})
        assert mock_post.call_count == 1
        assert str(type(resp)) == "<class 'tuple'>"
        assert resp[0] == 200
        assert resp[1] == {"foo": "bar"}


@patch("requests.Session.post", side_effect=RequestException)
def test_post_request_failure(mock_post):
    lir = LIR("testtoken", "http://example.com")
    resp = lir.post_request("http://example.com", {"foo": "bar"})
    assert resp[0] == 599
    assert resp[1]["error"] == True
    assert (
        str(type(resp[1]["message"]))
        == "<class 'requests.exceptions.RequestException'>"
    )


@patch("cli.lir.LIR.post_request")
def test_create_user(mock_post):
    lir = LIR("testtoken", "http://example.com")
    lir.create_user({"foo": "bar"})
    mock_post.assert_called_with(
        "http://example.com/api/now/ir/user", json.dumps({"foo": "bar"})
    )


@patch("cli.lir.LIR.post_request")
def test_create_team(mock_post):
    lir = LIR("testtoken", "http://example.com")
    lir.create_team({"foo": "bar"})
    mock_post.assert_called_with(
        "http://example.com/api/now/ir/team", json.dumps({"foo": "bar"})
    )


@patch("cli.lir.LIR.post_request")
def test_create_service(mock_post):
    lir = LIR("testtoken", "http://example.com")
    lir.create_service({"foo": "bar"})
    mock_post.assert_called_with(
        "http://example.com/api/now/ir/service", json.dumps({"foo": "bar"})
    )


@patch("cli.lir.LIR.post_request")
def test_create_shift(mock_post):
    lir = LIR("testtoken", "http://example.com")
    lir.create_shift({"foo": "bar"})
    mock_post.assert_called_with(
        "http://example.com/api/now/ir/shift", json.dumps({"foo": "bar"})
    )


@patch("cli.lir.LIR.post_request")
def test_create_escalation(mock_post):
    lir = LIR("testtoken", "http://example.com")
    lir.create_escalation({"foo": "bar"})
    mock_post.assert_called_with(
        "http://example.com/api/now/ir/escalation_policy", json.dumps({"foo": "bar"})
    )
