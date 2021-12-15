from argparse import ArgumentParser


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
    return parser.parse_args()
