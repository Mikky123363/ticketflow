from decimal import Decimal

from pydantic import BaseModel


class TicketTypeSales(BaseModel):
    ticket_type_id: int
    name: str
    quantity: int
    sold: int
    revenue: Decimal


class SalesReport(BaseModel):
    event_id: int
    event_name: str
    total_tickets_sold: int
    total_revenue: Decimal
    by_ticket_type: list[TicketTypeSales]


class AdminStats(BaseModel):
    total_users: int
    users_by_role: dict[str, int]
    users_by_status: dict[str, int]
    events_by_status: dict[str, int]
    orders_by_status: dict[str, int]
    tickets_sold: int
    total_revenue: Decimal
