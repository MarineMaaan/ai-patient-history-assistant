"""Local seed/reset commands; the app never deletes records on a rerun."""
import argparse

from .db import Database
from .seed import DEFAULT_DB, reset, seed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seed", "reset"])
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        if args.command == "reset":
            reset(DEFAULT_DB, args.confirm)
        else:
            seed(Database(DEFAULT_DB))
    except ValueError as exc:
        parser.error(str(exc))
    print("Synthetic demo database ready in local/history.sqlite3")


if __name__ == "__main__":
    main()
