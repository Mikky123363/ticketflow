from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (makes sure all tables are known)
from app.core.database import Base, engine
from app.routers import admin, auth, events, orders, seats, ticket_types, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the tables in PostgreSQL if they do not exist yet
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="TicketFlow API",
    description="Event ticketing system: events, ticket types, seats, and a reserve -> confirm purchase flow.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(ticket_types.router)
app.include_router(seats.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"app": "TicketFlow API", "status": "running"}
