"""Arifa za oda: kiungo cha WhatsApp (bure) na SMS ya hiari kupitia Africa's Talking.

SMS inawashwa tu kama mipangilio ipo (env vars au Streamlit secrets):
    AT_USERNAME   mfano "sandbox" kwa majaribio, au jina la akaunti yako
    AT_API_KEY    ufunguo wa API
    AT_SENDER_ID  (hiari) jina la mtumaji lililosajiliwa
Mipangilio ikikosekana, app inafanya kazi kwa WhatsApp pekee.
Hakuna kinachotupa kosa: kushindwa kutuma SMS hakuzuii oda.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

AT_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


def _setting(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def sms_enabled():
    return bool(_setting("AT_USERNAME") and _setting("AT_API_KEY"))


def whatsapp_link(phone, text):
    """phone = namba iliyo-normalize (2557XXXXXXXX). Kiungo kinafungua WhatsApp na ujumbe tayari."""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    return f"https://wa.me/{digits}?text={urllib.parse.quote(text)}"


def order_message(order, customer_name, customer_phone):
    """Ujumbe wa oda mpya kwa muuzaji (Kiswahili)."""
    return (
        f"Oda mpya #{order['order_id']} - Smart Food\n"
        f"Chakula: {order['dish']}\n"
        f"Sahani: {order['quantity']}\n"
        f"Jumla: TSh {int(order['total_price']):,}\n"
        f"Mteja: {customer_name}\n"
        f"Simu: 0{str(customer_phone)[3:]}\n"
        "Fungua Smart Food kuthibitisha oda."
    )


def customer_message(order_id, dish, vendor_name, confirmed=True):
    if confirmed:
        return (
            f"Oda #{order_id} ya {dish} imethibitishwa na {vendor_name}. "
            "Karibu uchukue chakula chako. - Smart Food"
        )
    return f"Oda #{order_id} ya {dish} imeghairiwa na {vendor_name}. - Smart Food"


def send_sms(phone, message):
    """Rudisha (imetumwa: bool, maelezo: str). Haitupi kosa kamwe."""
    username, api_key = _setting("AT_USERNAME"), _setting("AT_API_KEY")

    if not (username and api_key):
        return False, "SMS haijawashwa"

    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    payload = {"username": username, "to": f"+{digits}", "message": message}
    sender = _setting("AT_SENDER_ID")

    if sender:
        payload["from"] = sender

    request = urllib.request.Request(
        AT_SANDBOX_URL if username == "sandbox" else AT_URL,
        data=urllib.parse.urlencode(payload).encode(),
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode() or "{}")

        recipients = body.get("SMSMessageData", {}).get("Recipients", [])
        ok = bool(recipients) and all(r.get("statusCode") in (100, 101, 102) for r in recipients)
        return ok, "imetumwa" if ok else "Africa's Talking ilikataa ujumbe"

    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        return False, f"SMS imeshindikana: {error}"