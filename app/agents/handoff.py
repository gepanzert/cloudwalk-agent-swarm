"""
Human Handoff Agent — escalates conversations to human agents.
Posts to a real Slack channel via Incoming Webhook.
Triggered by Sentiment Agent (urgent/distressed) or Support Agent exhaustion.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)


PRIORITY_COLORS = {
    "low": "#36a64f",
    "medium": "#ff9900",
    "high": "#ff4444",
    "critical": "#8B0000",
}

PRIORITY_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
    "critical": "🚨",
}


def post_to_slack(payload: dict) -> bool:
    """Post escalation to Slack via Incoming Webhook."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

    if not webhook_url or webhook_url == "":
        os.makedirs("data/escalations", exist_ok=True)
        filepath = f"data/escalations/{payload['ticket_id']}.json"
        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2)
        return True

    try:
        ticket_id = payload["ticket_id"]
        user_id = payload["user_id"]
        message = payload["message"]
        priority = payload.get("priority", "medium")
        sentiment = payload.get("sentiment", "normal")
        summary = payload.get("summary", "No summary provided")
        trigger = payload.get("trigger", "manual")

        emoji = PRIORITY_EMOJI.get(priority, "🟡")
        color = PRIORITY_COLORS.get(priority, "#ff9900")

        slack_message = {
            "text": f"{emoji} New escalation — {ticket_id}",
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} Customer Escalation — {priority.upper()} Priority"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Ticket ID:*\n{ticket_id}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*User ID:*\n{user_id}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Sentiment:*\n{sentiment.capitalize()}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Trigger:*\n{trigger.replace('_', ' ').title()}"
                                }
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*User message:*\n>{message}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Summary:*\n{summary}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | InfinitePay Agent Swarm"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        response = requests.post(
            webhook_url,
            json=slack_message,
            timeout=5,
        )

        os.makedirs("data/escalations", exist_ok=True)
        filepath = f"data/escalations/{ticket_id}.json"
        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return response.status_code == 200

    except Exception as e:
        os.makedirs("data/escalations", exist_ok=True)
        filepath = f"data/escalations/{payload.get('ticket_id', 'unknown')}.json"
        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2)
        return False


def run_handoff_agent(
    message: str,
    user_id: str,
    conversation_summary: str = "",
    sentiment: str = "normal",
    priority: str = "medium",
    trigger: str = "support_exhausted",
) -> str:
    """
    Escalate a conversation to a human agent via Slack.

    Args:
        message: the user's last message
        user_id: user identifier
        conversation_summary: summary of the conversation so far
        sentiment: detected sentiment (normal/frustrated/urgent/distressed)
        priority: escalation priority (low/medium/high/critical)
        trigger: what triggered the escalation

    Returns:
        confirmation message to the user
    """
    ticket_id = f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    payload = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "message": message,
        "summary": conversation_summary or "No summary provided",
        "sentiment": sentiment,
        "priority": priority,
        "trigger": trigger,
        "created_at": datetime.now().isoformat(),
        "status": "pending_human_review",
        "channel": "#escalations",
    }

    slack_sent = post_to_slack(payload)

    priority_messages = {
        "low": "within 4 business hours",
        "medium": "within 2 business hours",
        "high": "within 30 minutes",
        "critical": "as soon as possible — this is being treated as urgent",
    }

    response_time = priority_messages.get(priority, "within 2 business hours")

    if priority == "critical":
        opening = (
            "I completely understand your frustration, and I want to make sure "
            "this gets resolved as a matter of urgency."
        )
    elif priority == "high":
        opening = (
            "I can see this is directly impacting your business right now, "
            "and I'm treating this as a priority."
        )
    else:
        opening = "I've escalated your case to our human support team."

    return (
        f"{opening}\n\n"
        f"**Ticket ID:** {ticket_id}\n"
        f"**Priority:** {priority.upper()}\n"
        f"**Expected response:** {response_time}\n\n"
        f"Our team has been notified and will reach out to you shortly. "
        f"Please keep your ticket ID handy for reference."
    )


if __name__ == "__main__":
    result = run_handoff_agent(
        message="I can't process any sales, my business is losing money RIGHT NOW",
        user_id="client789",
        conversation_summary="User reports inability to process card payments for 2 hours",
        sentiment="urgent",
        priority="high",
        trigger="sentiment_detected",
    )
    print(result)