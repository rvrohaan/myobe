"""Manage users for the CO Generator web app.

Usage:
    python create_user.py           # add or update a user
    python create_user.py --list    # list all usernames
    python create_user.py --delete  # delete a user
"""
import json
import os
import sys
import getpass

from werkzeug.security import generate_password_hash

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")


def load() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(users: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    print(f"Saved to {USERS_FILE}")


def cmd_list():
    users = load()
    if not users:
        print("No users configured.")
    else:
        print(f"{'Username':<20} Status")
        print("-" * 30)
        for u in sorted(users):
            print(f"  {u}")


def cmd_add():
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if len(password) < 4:
        print("Password must be at least 4 characters.")
        sys.exit(1)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    users = load()
    action = "Updated" if username in users else "Created"
    users[username] = generate_password_hash(password)
    save(users)
    print(f"{action} user '{username}'.")


def cmd_delete():
    users = load()
    if not users:
        print("No users to delete.")
        sys.exit(0)
    username = input("Username to delete: ").strip()
    if username not in users:
        print(f"User '{username}' not found.")
        sys.exit(1)
    del users[username]
    save(users)
    print(f"Deleted user '{username}'.")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--list":
        cmd_list()
    elif arg == "--delete":
        cmd_delete()
    else:
        cmd_add()
