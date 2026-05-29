"""
Human Handoff Agent — escalates conversations to human agents.
Triggered when the Support Agent can't resolve an issue,
or when the user explicitly requests a human.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)


def run_handoff_agent(
    message: str,
    user_id: str,
    conversation_summary: str = "",
) -> str:
    """
    Escalate a conversation to a human agent.
    In production this would post to Slack/Zendesk/etc.
    Here we write to a local JSON file simulating the webhook.

    Args:
        message: the user's last message
        user_id: user identifier
        conversation_summary: summary of the conversation so far

    Returns:
        confirmation message to the user
    """
    ticket_id = f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Simulate Slack/webhook payload
    escalation_payload = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "message": message,
        "summary": conversation_summary or "No summary provided",
        "priority": "normal",
        "created_at": datetime.now().isoformat(),
        "status": "pending_human_review",
        "channel": "#customer-support",
    }

    # Write to local file (simulates Slack webhook in production)
    os.makedirs("data/escalations", exist_ok=True)
    filepath = f"data/escalations/{ticket_id}.json"
    with open(filepath, "w") as f:
        json.dump(escalation_payload, f, indent=2)

    return (
        f"I've escalated your case to our human support team.\n\n"
        f"**Ticket ID:** {ticket_id}\n"
        f"**Status:** A specialist will review your case shortly\n"
        f"**Expected response:** Within 2 business hours\n\n"
        f"You'll receive an update via email. Is there anything else "
        f"I can help you with in the meantime?"
    )


if __name__ == "__main__":
    result = run_handoff_agent(
        message="I need urgent help with my account",
        user_id="client789",
        conversation_summary="User reported inability to access account for 3 days",
    )
    print(result)
    print("\nCheck data/escalations/ for the generated ticket file.")