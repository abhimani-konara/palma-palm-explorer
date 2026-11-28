from pathlib import Path
from getpass import getpass
from secrets import token_hex
import subprocess

from dotenv import dotenv_values, set_key
from werkzeug.security import generate_password_hash

env_path = Path(".env")
gitignore_path = Path(".gitignore")

tracked = subprocess.run(
    ["git", "ls-files", "--error-unmatch", ".env"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=False
)

if tracked.returncode == 0:
    raise SystemExit(
        "STOP: .env is tracked by Git. Secure it before continuing."
    )

ignore = (
    gitignore_path.read_text(encoding="utf-8")
    if gitignore_path.exists()
    else ""
)

if ".env" not in ignore.splitlines():
    with gitignore_path.open("a", encoding="utf-8") as f:
        f.write("\n.env\n")

print("PALMA BIOMETRIC ADMIN SETUP")
print("---------------------------")
print("Choose a password with at least 12 characters.")
print("Your password will not appear while typing.")

password = getpass("New Admin Password: ")
confirm = getpass("Confirm Admin Password: ")

if len(password) < 12:
    raise SystemExit("Password must have at least 12 characters.")

if password != confirm:
    raise SystemExit("Passwords do not match.")

if not env_path.exists():
    env_path.write_text("", encoding="utf-8")

existing = dotenv_values(env_path)

set_key(
    str(env_path),
    "PALMA_ADMIN_PASSWORD_HASH",
    generate_password_hash(password),
    quote_mode="always"
)

if not existing.get("SECRET_KEY"):
    set_key(
        str(env_path),
        "SECRET_KEY",
        token_hex(32),
        quote_mode="always"
    )

# Do not replace an encryption key for an existing enrollment database.
if not existing.get("PALMA_BIOMETRIC_KEY"):
    import sqlite3
    from cryptography.fernet import Fernet

    existing_db = Path("biometric_data.sqlite3")
    if existing_db.is_file():
        try:
            with sqlite3.connect(existing_db) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM enrollments"
                ).fetchone()[0]
        except sqlite3.Error:
            raise SystemExit(
                "Existing biometric database found but cannot be inspected. "
                "Restore its original key before proceeding."
            )
        if count:
            raise SystemExit(
                "Existing enrollments detected without PALMA_BIOMETRIC_KEY. "
                "Restore the original encryption key; never replace it."
            )

    set_key(
        str(env_path),
        "PALMA_BIOMETRIC_KEY",
        Fernet.generate_key().decode("ascii"),
        quote_mode="always"
    )
    print("New biometric encryption key securely configured in local .env.")

print("---------------------------")
print("Admin password hash saved securely.")
print("Session secret configured.")
print("Local .env protection configured.")
print("Setup completed successfully.")
