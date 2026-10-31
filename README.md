# TicketFlow - Event Ticketing System API

A REST API for creating events, selling tickets and managing purchases, built with
**FastAPI**, **PostgreSQL**, **SQLAlchemy** and **uv**.

## What it does

| Priority | Feature | Where |
|---|---|---|
| P0 | Register / login (JWT) | `app/routers/auth.py` |
| P0 | Event management (create, read, update, delete) | `app/routers/events.py` |
| P0 | Ticket types and quantities (VIP, Regular, ...) | `app/routers/ticket_types.py` |
| P0 | Seat selection (seat map + choosing seats) | `app/routers/seats.py` |
| P0 | Purchase flow: reserve -> confirm | `app/routers/orders.py`, `app/services/orders.py` |
| P1 | QR code for every ticket | `app/services/qr.py` |
| P1 | Email with QR codes (background task) | `app/services/email.py` |
| P1 | Rate limiting | `app/core/rate_limit.py` |
| P1 | Admin dashboard and moderation | `app/routers/admin.py` |

Not built yet (P2): payment gateway, refunds, analytics reports, audit logs.
The "pay" step is simulated by `POST /orders/{id}/confirm`.

## Project structure

```
app/
  main.py            app setup, includes all routers
  dependencies.py    login / role / ownership checks
  core/              config, database, security (JWT + hashing), rate limiter
  models/            database tables (User, Event, TicketType, Seat, Order, Ticket)
  schemas/           Pydantic models (what valid input and output look like)
  routers/           the API endpoints
  services/          business logic (reservations, inventory, QR, email)
  scripts/           create_admin.py
```

## Setup

1. Install [uv](https://docs.astral.sh/uv/) and PostgreSQL.
2. Create the database:
   ```
   psql -U postgres -c "CREATE DATABASE ticketflow;"
   ```
3. Copy `.env.example` to `.env` and fill in `DATABASE_URL` and `SECRET_KEY`.
   Generate a key with:
   ```
   uv run python -c "import secrets; print(secrets.token_hex(32))"
   ```
4. Install packages:
   ```
   uv sync
   ```
5. Create an admin (admins cannot register through the API):
   ```
   uv run python -m app.scripts.create_admin --username admin --email admin@example.com
   ```
6. Run the server (tables are created automatically on startup):
   ```
   uv run uvicorn app.main:app --reload
   ```
7. Open http://127.0.0.1:8000/docs

## How the purchase flow works

1. `POST /orders/reserve` holds the seats/tickets for `RESERVATION_MINUTES` (default 10).
2. `POST /orders/{id}/confirm` confirms the order. The QR codes are emailed in the background.
3. If the customer does not confirm in time, the reservation expires and the seats become available again.
   `POST /orders/{id}/cancel` releases a reservation early.

**No double-selling:** before checking a seat or a ticket count, the database rows are locked
(`SELECT ... FOR UPDATE`). If two customers try to buy the same seat at the same moment,
the second one waits, then sees the seat is taken and gets `409 Conflict`.

## Roles

- **customer** (default): browse events, view seats, reserve and confirm orders.
- **organizer**: everything a customer can do, plus create events, ticket types and seats, and view sales.
- **admin**: manage all events and users, see platform stats. Created with the script above.

## Endpoints

Auth and users
- `POST /auth/register`, `POST /auth/token`, `GET /users/me`

Events
- `POST /events/` (organizer), `GET /events/` (public, `?search=`), `GET /events/mine`,
  `GET /events/{id}`, `PUT /events/{id}`, `DELETE /events/{id}`, `GET /events/{id}/sales`

Ticket types
- `POST/GET /events/{id}/ticket-types/`, `PUT/DELETE /events/{id}/ticket-types/{type_id}`

Seats
- `POST /events/{id}/seats/` (generate a block of seats), `GET /events/{id}/seats/` (`?status=available`)

Orders
- `POST /orders/reserve`, `GET /orders/me`, `GET /orders/{id}`, `POST /orders/{id}/confirm`,
  `POST /orders/{id}/cancel`, `GET /orders/{id}/tickets/{ticket_id}/qr`

Admin
- `GET /admin/events`, `PATCH /admin/events/{id}/status`, `GET /admin/users`,
  `PATCH /admin/users/{id}/status`, `GET /admin/stats`

## Settings (.env)

See `.env.example`. `REQUIRE_EVENT_APPROVAL=true` makes new events start as `pending`
until an admin approves them.
Without `SMTP_HOST`, emails are only written to the server log (not sent).

## Known limits

- The rate limiter keeps counters in memory (resets on restart, single process only). Use Redis in production.
- Tables are created with `create_all`, not migrations. Use Alembic for real schema changes.
- Payment is simulated. Refunds, analytics reports and audit logs are not built yet.
