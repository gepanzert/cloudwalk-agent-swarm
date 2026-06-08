"""
CRM Agent — creates support tickets in Freshdesk when a conversation
is escalated to human support. Complements the Slack Handoff Agent.
"""

import os
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)


def create_freshdesk_ticket(
    user_id: str,
    summary: str,
    priority: str = "medium",
    sentiment: str = "normal",
) -> dict:
    """
    Create a support ticket in Freshdesk.

    Args:
        user_id: InfinitePay user identifier
        summary: conversation summary from Summarization Agent
        priority: low, medium, high, urgent
        sentiment: normal, frustrated, urgent, distressed

    Returns:
        dict with ticket_id and ticket_url, or error info
    """
    domain = os.getenv("FRESHDESK_DOMAIN", "luisayamauchi.freshdesk.com")
    api_key = os.getenv("FRESHDESK_API_KEY")

    if not api_key:
        return {"error": "FRESHDESK_API_KEY not configured", "ticket_id": None}

    # Map priority to Freshdesk priority values
    # 1=Low, 2=Medium, 3=High, 4=Urgent
    priority_map = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "urgent": 4,
        "critical": 4,
    }
    freshdesk_priority = priority_map.get(priority.lower(), 2)

    # Map sentiment to Freshdesk tags
    tags = ["agent-swarm", f"sentiment-{sentiment}", f"user-{user_id}"]

    subject = f"[InfinitePay Support] Escalation — User {user_id}"
    description = f"""
<b>Escalation from InfinitePay Agent Swarm</b><br><br>
<b>User ID:</b> {user_id}<br>
<b>Sentiment:</b> {sentiment}<br>
<b>Priority:</b> {priority}<br><br>
<b>Conversation Summary:</b><br>
{summary}
"""

    payload = {
        "subject": subject,
        "description": description,
        "email": f"{user_id}@infinitepay-support.com",
        "priority": freshdesk_priority,
        "status": 2,  # Open
        "tags": tags,
    }

    try:
        response = requests.post(
            f"https://{domain}/api/v2/tickets",
            json=payload,
            auth=(api_key, "X"),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 201:
            ticket = response.json()
            ticket_id = ticket.get("id")
            ticket_url = f"https://{domain}/helpdesk/tickets/{ticket_id}"
            return {
                "ticket_id": ticket_id,
                "ticket_url": ticket_url,
                "status": "created",
            }
        else:
            return {
                "error": f"Freshdesk API error: {response.status_code}",
                "detail": response.text,
                "ticket_id": None,
            }

    except requests.exceptions.Timeout:
        return {"error": "Freshdesk API timeout", "ticket_id": None}
    except Exception as e:
        return {"error": str(e), "ticket_id": None}


if __name__ == "__main__":
    result = create_freshdesk_ticket(
        user_id="client789",
        summary="User reported inability to process sales. Account active, no blocks found. Issue may be connectivity or app-related.",
        priority="high",
        sentiment="urgent",
    )
    print("Freshdesk ticket result:")
    print(result)