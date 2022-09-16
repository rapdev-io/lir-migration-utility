from cli.cli import parse_args, setup_logger, main
import logging
from unittest.mock import patch


def test_parse_args():
    parsed_args = parse_args(
        ["--pd", "abc123", "--lirtoken", "xyz987", "--apiurl", "http://example.com"]
    )
    assert parsed_args.pd == "abc123"
    assert parsed_args.lirtoken == "xyz987"
    assert parsed_args.apiurl == "http://example.com"
    assert parsed_args.noop == False
    assert parsed_args.level == "INFO"


def test_setup_logger():
    parsed_args = parse_args(
        ["--pd", "abc123", "--lirtoken", "xyz987", "--apiurl", "http://example.com"]
    )
    setup_logger(parsed_args)
    logger = logging.getLogger()
    assert logger.handlers[-1].formatter._fmt == "[%(levelname)s] %(message)s"


def test_setup_logger_debug():
    parsed_args = parse_args(
        [
            "--pd",
            "abc123",
            "--lirtoken",
            "xyz987",
            "--apiurl",
            "http://example.com",
            "--level",
            "DEBUG",
        ]
    )
    setup_logger(parsed_args)
    logger = logging.getLogger()
    assert (
        logger.handlers[-1].formatter._fmt
        == "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s"
    )


@patch("cli.cli.Mapper")
def test_main(mapper):
    mapper_instance = mapper.return_value
    parsed_args = parse_args(
        [
            "--pd",
            "abc123",
            "--lirtoken",
            "xyz987",
            "--apiurl",
            "http://example.com",
            "--noop",
        ]
    )
    main(parsed_args)
    mapper.assert_called_with(
        "xyz987", "http://example.com", "abc123", noop=True, pretty=False
    )
    mapper_instance.map_and_create_users.assert_called_once()
    mapper_instance.map_team_members.assert_called_once()
    mapper_instance.map_teams.assert_called_once()
    mapper_instance.map_services.assert_called_once()
    mapper_instance.map_schedules.assert_called_once()
    mapper_instance.map_escalations.assert_called_once()
    mapper_instance.noop_output.assert_called_once()
