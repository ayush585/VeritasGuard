import os
from urllib.parse import urlencode

import httpx


async def send_whatsapp_message(*, to_number: str, body: str) -> tuple[bool, str]:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886").strip()

    if not account_sid or not auth_token:
        return False, "Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN."

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = {
        "From": from_number,
        "To": to_number,
        "Body": body,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                content=urlencode(payload),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth=(account_sid, auth_token),
            )
            response.raise_for_status()
            sid = response.json().get("sid", "")
            return True, sid
    except Exception as e:
        return False, str(e)
