"""
User database tools used by the Support Agent.
Queries the mock SQLite database for user account information.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

DATABASE_URL = "sqlite:///data/infinitepay_users.db"


def get_engine():
    return create_engine(DATABASE_URL)


def get_account_status(user_id: str) -> str:
    """Get account status, KYC status, and plan for a user."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()

            if not result:
                return f"No account found for user_id: {user_id}"

            return (
                f"Account Status: {result.account_status}\n"
                f"KYC Status: {result.kyc_status}\n"
                f"Plan: {result.plan}\n"
                f"Name: {result.name}\n"
                f"Member since: {result.created_at}"
            )
    except Exception as e:
        return f"Database error: {str(e)}"


def get_recent_transactions(user_id: str, limit: int = 5) -> str:
    """Get recent transactions for a user."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            results = conn.execute(
                text("""
                    SELECT * FROM transactions
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "limit": limit}
            ).fetchall()

            if not results:
                return f"No transactions found for user_id: {user_id}"

            formatted = []
            for t in results:
                formatted.append(
                    f"- {t.created_at} | {t.type} | "
                    f"R${t.amount:.2f} | {t.status} | {t.description}"
                )

            return "Recent transactions:\n" + "\n".join(formatted)
    except Exception as e:
        return f"Database error: {str(e)}"


def check_transfer_limits(user_id: str) -> str:
    """Check transfer limits and identify if transfers are blocked."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM account_limits WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()

            if not result:
                return f"No limit information found for user_id: {user_id}"

            remaining = result.daily_transfer_limit - result.used_today
            status = "✓ Available" if remaining > 0 else "✗ Limit reached"

            response = (
                f"Daily transfer limit: R${result.daily_transfer_limit:.2f}\n"
                f"Used today: R${result.used_today:.2f}\n"
                f"Remaining: R${remaining:.2f} — {status}\n"
                f"Pix limit: R${result.pix_limit:.2f}"
            )

            if result.reason_if_blocked:
                response += f"\nNote: {result.reason_if_blocked}"

            return response
    except Exception as e:
        return f"Database error: {str(e)}"


def get_login_status(user_id: str) -> str:
    """Check if a user can log in and why they might be blocked."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT account_status, kyc_status FROM users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()

            if not result:
                return f"No account found for user_id: {user_id}"

            if result.account_status == "active":
                return "Account is active. Login should work normally."
            elif result.account_status == "blocked":
                return "Account is blocked. This may be due to a security review or policy violation. Please contact support."
            elif result.account_status == "suspended":
                return "Account is suspended. Login is currently disabled. Please contact support to resolve this."
            elif result.account_status == "pending":
                return f"Account is pending activation. KYC status: {result.kyc_status}. Please complete identity verification."
            else:
                return f"Account status: {result.account_status}. Please contact support."
    except Exception as e:
        return f"Database error: {str(e)}"


def create_support_ticket(user_id: str, summary: str) -> str:
    """Create a support ticket for escalation."""
    import random
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    return (
        f"Support ticket created successfully.\n"
        f"Ticket ID: {ticket_id}\n"
        f"User: {user_id}\n"
        f"Summary: {summary}\n"
        f"Status: Open\n"
        f"A support agent will contact you within 24 hours."
    )


if __name__ == "__main__":
    print("Testing user_db tools with client789...")
    print("\n--- Account Status ---")
    print(get_account_status("client789"))
    print("\n--- Recent Transactions ---")
    print(get_recent_transactions("client789"))
    print("\n--- Transfer Limits ---")
    print(check_transfer_limits("client789"))
    print("\n--- Login Status ---")
    print(get_login_status("client789"))
    print("\n--- Support Ticket ---")
    print(create_support_ticket("client789", "Test ticket"))