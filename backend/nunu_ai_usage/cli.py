import argparse
import json
import sys

from nunu_ai_usage.widget_data import build_widget_data


def widget_data_command():
    data = build_widget_data()

    json.dump(
        data,
        sys.stdout,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    sys.stdout.write("\n")


def main():
    parser = argparse.ArgumentParser(
        prog="nunu-ai-usage"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser(
        "widget-data",
        help="Print sanitized widget data as JSON",
    )

    args = parser.parse_args()

    if args.command == "widget-data":
        widget_data_command()
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
