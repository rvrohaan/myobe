"""Manage institutional plans for the MyOBE web app (owner-only tool).

Usage:
    python create_institution.py create                    # new institution + super admin
    python create_institution.py topup <slug> <amount>     # refill the token pool
    python create_institution.py list                      # list institutions
    python create_institution.py set-admin <slug> <user>   # promote a member to admin
    python create_institution.py remove-admin <slug> <user># demote an admin to member
    python create_institution.py deactivate <slug>         # suspend (members revert to personal tokens)
    python create_institution.py activate <slug>           # re-enable a suspended institution
"""
import getpass
import json
import os
import re
import sys
import time

from werkzeug.security import generate_password_hash

from generate_po_mapping import COLLEGE_TYPE_META

_DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
USERS_FILE        = os.path.join(_DATA_DIR, "users.json")
INSTITUTIONS_FILE = os.path.join(_DATA_DIR, "institutions.json")


def _load(path) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to {path}")


def cmd_create():
    institutions = _load(INSTITUTIONS_FILE)

    slug = input("Institution id (slug, e.g. demo-college): ").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,}", slug):
        print("Slug must be 3+ chars: lowercase letters, digits and hyphens.")
        sys.exit(1)
    if slug in institutions:
        print(f"Institution '{slug}' already exists.")
        sys.exit(1)

    name = input("Institution name: ").strip()
    if not name:
        print("Name cannot be empty.")
        sys.exit(1)

    try:
        pool = int(input("Initial pool tokens: ").strip())
        if pool < 0:
            raise ValueError
    except ValueError:
        print("Pool tokens must be a non-negative integer.")
        sys.exit(1)

    print("College types: " + ", ".join(sorted(COLLEGE_TYPE_META)))
    college_type = input("Default college type: ").strip().lower()
    if college_type not in COLLEGE_TYPE_META:
        print(f"Unknown college type '{college_type}'.")
        sys.exit(1)

    users = _load(USERS_FILE)
    admin = input("Super-admin username (existing user, or a new one to create): ").strip()
    if not admin or len(admin) < 3 or not all(c.isalnum() or c in "-_" for c in admin):
        print("Username must be 3+ chars: letters, numbers, - and _.")
        sys.exit(1)

    if admin in users:
        if users[admin].get("institution"):
            print(f"User '{admin}' already belongs to institution "
                  f"'{users[admin]['institution']}'.")
            sys.exit(1)
        users[admin]["institution"] = slug
        users[admin]["inst_role"]   = "admin"
        users[admin]["college_type"] = college_type
        action = f"Designated existing user '{admin}' as super admin."
    else:
        email = input("Super-admin email: ").strip().lower()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            print("Please enter a valid email address.")
            sys.exit(1)
        if any(d.get("email", "").lower() == email
               for d in users.values() if isinstance(d, dict)):
            print("An account with that email address already exists.")
            sys.exit(1)
        password = getpass.getpass("Super-admin password: ")
        if len(password) < 6:
            print("Password must be at least 6 characters.")
            sys.exit(1)
        if password != getpass.getpass("Confirm password: "):
            print("Passwords do not match.")
            sys.exit(1)
        users[admin] = {
            "password":     generate_password_hash(password),
            "tokens":       0,
            "email":        email,
            "college_type": college_type,
            "branch":       "",
            "institution":  slug,
            "inst_role":    "admin",
        }
        action = f"Created super admin '{admin}'."

    institutions[slug] = {
        "name":                 name,
        "pool_tokens":          pool,
        "active":               True,
        "default_college_type": college_type,
        "created":              int(time.time()),
        "usage":                {},
    }
    _save(INSTITUTIONS_FILE, institutions)
    _save(USERS_FILE, users)
    print(f"Created institution '{name}' ({slug}) with {pool} pool tokens. {action}")


def cmd_topup(slug, amount):
    institutions = _load(INSTITUTIONS_FILE)
    if slug not in institutions:
        print(f"Institution '{slug}' not found.")
        sys.exit(1)
    try:
        amount = int(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        print("Amount must be a positive integer.")
        sys.exit(1)
    institutions[slug]["pool_tokens"] = institutions[slug].get("pool_tokens", 0) + amount
    _save(INSTITUTIONS_FILE, institutions)
    print(f"Added {amount} tokens. '{slug}' pool is now "
          f"{institutions[slug]['pool_tokens']}.")


def cmd_list():
    institutions = _load(INSTITUTIONS_FILE)
    if not institutions:
        print("No institutions configured.")
        return
    users = _load(USERS_FILE)
    print(f"{'Slug':<20} {'Name':<32} {'Pool':>7} {'Active':<7} Members")
    print("-" * 78)
    for slug in sorted(institutions):
        inst = institutions[slug]
        members = sum(1 for d in users.values()
                      if isinstance(d, dict) and d.get("institution") == slug)
        print(f"{slug:<20} {inst.get('name', ''):<32} "
              f"{inst.get('pool_tokens', 0):>7} "
              f"{str(inst.get('active', True)):<7} {members}")


def _set_role(slug, username, role):
    institutions = _load(INSTITUTIONS_FILE)
    if slug not in institutions:
        print(f"Institution '{slug}' not found.")
        sys.exit(1)
    users = _load(USERS_FILE)
    if username not in users or users[username].get("institution") != slug:
        print(f"User '{username}' is not a member of '{slug}'.")
        sys.exit(1)
    users[username]["inst_role"] = role
    _save(USERS_FILE, users)
    print(f"'{username}' is now a {role} of '{slug}'.")


def _set_active(slug, active):
    institutions = _load(INSTITUTIONS_FILE)
    if slug not in institutions:
        print(f"Institution '{slug}' not found.")
        sys.exit(1)
    institutions[slug]["active"] = active
    _save(INSTITUTIONS_FILE, institutions)
    print(f"'{slug}' is now {'active' if active else 'inactive'}.")


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "create":
        cmd_create()
    elif cmd == "topup" and len(args) == 3:
        cmd_topup(args[1], args[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "set-admin" and len(args) == 3:
        _set_role(args[1], args[2], "admin")
    elif cmd == "remove-admin" and len(args) == 3:
        _set_role(args[1], args[2], "member")
    elif cmd == "deactivate" and len(args) == 2:
        _set_active(args[1], False)
    elif cmd == "activate" and len(args) == 2:
        _set_active(args[1], True)
    else:
        print(__doc__.strip())
