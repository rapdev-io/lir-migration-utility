from argparse import ArgumentParser
from mapper import Mapper
import logging


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--pd", action="store", required=True, help="PagerDuty API token"
    )
    parser.add_argument(
        "--irtoken", action="store", required=True, help="AIR API token"
    )
    parser.add_argument("--apiurl", action="store", required=True, help="AIR API URL")
    parser.add_argument(
        "--noop",
        action="store_true",
        default=False,
        help="Output actions without making them",
    )
    parser.add_argument(
        "--level",
        action="store",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def setup_logger(args):
    logger = logging.getLogger()
    logger.setLevel(level=args.level)
    handler = logging.StreamHandler()
    handler.setLevel(args.level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main(args):
    setup_logger(args)
    mapper = Mapper(args.irtoken, args.apiurl, args.pd, noop=args.noop)
    mapper.map_and_create_users()
    mapper.map_team_members()
    mapper.map_teams()
    mapper.map_services()
    mapper.map_schedules()
    mapper.map_escalations()
    if args.noop:
        mapper.noop_output()


if __name__ == "__main__":
    args = parse_args()
    main(args)
