import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.services.qr import make_qr_png

logger = logging.getLogger("ticketflow.email")


def send_ticket_email(
    to_email: str,
    customer_name: str,
    event_name: str,
    event_date: str,
    venue: str,
    tickets: list[dict],
) -> None:
    """Emails the tickets with a QR code image for each one.

    This runs in the background after the API has already answered the customer.
    A failed email is logged but never crashes the request.
    """
    message = EmailMessage()
    message["Subject"] = f"Your tickets for {event_name}"
    message["From"] = settings.email_from
    message["To"] = to_email

    lines = [
        f"Hi {customer_name},",
        "",
        f"Your payment is confirmed. Here are your tickets for {event_name}.",
        f"When: {event_date}",
        f"Where: {venue}",
        "",
    ]
    for ticket in tickets:
        seat = f" - seat {ticket['seat']}" if ticket["seat"] else ""
        lines.append(f"{ticket['type']}{seat} - code {ticket['code']}")
    lines += ["", "Show the attached QR code at the entrance."]
    message.set_content("\n".join(lines))

    for ticket in tickets:
        message.add_attachment(
            make_qr_png(ticket["code"]),
            maintype="image",
            subtype="png",
            filename=f"ticket-{ticket['code'][:8]}.png",
        )

    if not settings.smtp_host:
        logger.warning(
            "SMTP is not configured, so the email to %s was NOT sent (%d tickets).",
            to_email,
            len(tickets),
        )
        return

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password or "")
            server.send_message(message)
        logger.info("Ticket email sent to %s", to_email)
    except Exception:
        logger.exception("Could not send ticket email to %s", to_email)
