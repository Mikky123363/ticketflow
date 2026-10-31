"""Creates an admin user. Run it from the project folder:

    uv run python -m app.scripts.create_admin --username admin --email admin@example.com

Admins cannot register through the API (so nobody can make themselves admin).
"""
import argparse
import getpass

from sqlalchemy import select

from app import models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a TicketFlow admin user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", default="Administrator")
    args = parser.parse_args()

    password = getpass.getpass("Password (min 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        exists = db.execute(
            select(User).where((User.username == args.username) | (User.email == args.email.lower()))
        ).scalar_one_or_none()
        if exists:
            raise SystemExit("A user with that username or email already exists.")

        db.add(
            User(
                username=args.username,
                email=args.email.lower(),
                full_name=args.full_name,
                hashed_password=hash_password(password),
                role="admin",
            )
        )
        db.commit()
    print(f"Admin '{args.username}' created.")


if __name__ == "__main__":
    main()
