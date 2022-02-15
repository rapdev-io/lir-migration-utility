from argparse import ArgumentParser
from .mapper import Mapper
import logging
import sys


def parse_args(args):
    """Parse command line arguments

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--pd", action="store", required=True, help="PagerDuty API token"
    )
    parser.add_argument(
        "--lirtoken", action="store", required=True, help="LIR API token"
    )
    parser.add_argument("--apiurl", action="store", required=True, help="LIR API URL")
    parser.add_argument(
        "--noop",
        action="store_true",
        default=False,
        help="Output actions without making them",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Output noop with pretty print json",
    )
    parser.add_argument(
        "--level",
        action="store",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args(args)


def setup_logger(args):
    """Setup logger format and level based on command line args.

    Args:
        args (argparse.Namespace): Parsed arguments
    """
    logger = logging.getLogger()
    logger.setLevel(level=args.level)
    handler = logging.StreamHandler()
    handler.setLevel(args.level)
    if args.level == "DEBUG":
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s"
        )
    else:
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main(args):
    setup_logger(args)
    mapper = Mapper(
        args.lirtoken, args.apiurl, args.pd, noop=args.noop, pretty=args.pretty
    )
    mapper.map_and_create_users()
    mapper.map_team_members()
    mapper.map_teams()
    mapper.map_services()
    mapper.map_schedules()
    mapper.map_escalations()
    if args.noop:
        mapper.noop_output()


if __name__ == "__main__":  # pragma: no cover
    args = parse_args(sys.argv[1:])
    main(args)
