"""
Seed script — creates and populates the mock SQLite user database.
Run once: python -m data.seed_users
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = "sqlite:///data/infinitepay_users.db"


def seed():
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Create tables
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                account_status TEXT,
                kyc_status TEXT,
                plan TEXT,
                created_at TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                type TEXT,
                amount REAL,
                status TEXT,
                description TEXT,
                created_at TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS account_limits (
                user_id TEXT PRIMARY KEY,
                daily_transfer_limit REAL,
                used_today REAL,
                pix_limit REAL,
                reason_if_blocked TEXT
            )
        """))

        # Seed users with interesting, realistic states
        users = [
            ("client789", "João Silva", "joao@email.com", "+55 11 99999-0001",
             "active", "approved", "smart", "2024-01-15"),
            ("user_blocked", "Maria Santos", "maria@email.com", "+55 11 99999-0002",
             "blocked", "approved", "smart", "2024-02-20"),
            ("user_kyc_pending", "Carlos Oliveira", "carlos@email.com", "+55 11 99999-0003",
             "pending", "pending", "basic", "2024-03-10"),
            ("user_limit_reached", "Ana Costa", "ana@email.com", "+55 11 99999-0004",
             "active", "approved", "smart", "2024-01-05"),
            ("user_login_issue", "Pedro Souza", "pedro@email.com", "+55 11 99999-0005",
             "suspended", "approved", "smart", "2023-12-01"),
        ]

        conn.execute(text("DELETE FROM users"))
        for user in users:
            conn.execute(text("""
                INSERT INTO users VALUES (
                    :user_id, :name, :email, :phone,
                    :account_status, :kyc_status, :plan, :created_at
                )
            """), {
                "user_id": user[0], "name": user[1], "email": user[2],
                "phone": user[3], "account_status": user[4],
                "kyc_status": user[5], "plan": user[6], "created_at": user[7]
            })

        # Seed transactions
        transactions = [
            ("client789", "pix_received", 1500.00, "completed",
             "Pagamento cliente", "2025-05-27 14:30:00"),
            ("client789", "pix_sent", 200.00, "completed",
             "Pagamento fornecedor", "2025-05-27 10:00:00"),
            ("client789", "card_payment", 350.00, "completed",
             "Venda cartão crédito - taxa 2.99%", "2025-05-26 16:00:00"),
            ("client789", "pix_sent", 50.00, "failed",
             "Transferência falhou - limite atingido", "2025-05-26 09:00:00"),
            ("user_limit_reached", "pix_sent", 5000.00, "failed",
             "Limite diário atingido", "2025-05-27 11:00:00"),
        ]

        conn.execute(text("DELETE FROM transactions"))
        for t in transactions:
            conn.execute(text("""
                INSERT INTO transactions
                (user_id, type, amount, status, description, created_at)
                VALUES (:user_id, :type, :amount, :status, :description, :created_at)
            """), {
                "user_id": t[0], "type": t[1], "amount": t[2],
                "status": t[3], "description": t[4], "created_at": t[5]
            })

        # Seed limits
        limits = [
            ("client789", 5000.00, 200.00, 10000.00, None),
            ("user_blocked", 0.00, 0.00, 0.00,
             "Account blocked pending fraud review"),
            ("user_kyc_pending", 500.00, 0.00, 500.00,
             "KYC verification pending — limits restricted"),
            ("user_limit_reached", 5000.00, 5000.00, 10000.00,
             "Daily limit reached"),
            ("user_login_issue", 0.00, 0.00, 0.00,
             "Account suspended — contact support"),
        ]

        conn.execute(text("DELETE FROM account_limits"))
        for l in limits:
            conn.execute(text("""
                INSERT INTO account_limits VALUES (
                    :user_id, :daily_transfer_limit,
                    :used_today, :pix_limit, :reason_if_blocked
                )
            """), {
                "user_id": l[0], "daily_transfer_limit": l[1],
                "used_today": l[2], "pix_limit": l[3],
                "reason_if_blocked": l[4]
            })

        conn.commit()
        print("✓ Database seeded successfully")
        print(f"  Users: {len(users)}")
        print(f"  Transactions: {len(transactions)}")
        print(f"  Account limits: {len(limits)}")


if __name__ == "__main__":
    seed()