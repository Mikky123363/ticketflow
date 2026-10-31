"""Small reusable checks that endpoints plug in with Depends(...)."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import Event, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


def _user_from_token(token: str, db: Session) -> User:
    bad_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise bad_credentials

    user = db.get(User, user_id)
    if user is None:
        raise bad_credentials
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account is {user.status}",
        )
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Reads the token and returns the logged-in user."""
    return _user_from_token(token, db)


def get_optional_user(
    token: str | None = Depends(oauth2_optional), db: Session = Depends(get_db)
) -> User | None:
    """Like get_current_user, but returns None when nobody is logged in."""
    if token is None:
        return None
    return _user_from_token(token, db)


def require_roles(*allowed_roles: str):
    """Builds a dependency that only lets users with one of these roles through."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to do this",
            )
        return user

    return checker


get_organizer = require_roles("organizer", "admin")
get_admin = require_roles("admin")


def get_visible_event(
    event_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Event:
    """Active events are public. Other events are only visible to their organizer and admins."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.status != "active":
        is_owner = user is not None and user.id == event.organizer_id
        is_admin = user is not None and user.role == "admin"
        if not (is_owner or is_admin):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def get_owned_event(
    event_id: int,
    user: User = Depends(get_organizer),
    db: Session = Depends(get_db),
) -> Event:
    """Finds the event and checks the user is its organizer (or an admin)."""
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if user.role != "admin" and event.organizer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own events",
        )
    return event
