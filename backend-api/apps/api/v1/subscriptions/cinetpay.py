"""CinetPay hosted checkout. Never trust the browser redirect as proof of payment.

Provider endpoints: https://docs.cinetpay.com/api/1.0-fr/checkout/
"""
import os
from decimal import Decimal
from urllib.parse import urlparse

import requests


class CheckoutConfigurationError(Exception):
    pass


class CheckoutProviderError(Exception):
    pass


_CREATE = "https://api-checkout.cinetpay.com/v2/payment"
_CHECK = "https://api-checkout.cinetpay.com/v2/payment/check"


def configuration():
    apikey = os.environ.get("CINETPAY_API_KEY", "").strip()
    site_id = os.environ.get("CINETPAY_SITE_ID", "").strip()
    api_origin = os.environ.get("GCONNECT_PUBLIC_API_URL", "").strip().rstrip("/")
    web_origin = os.environ.get("GCONNECT_WEB_APP_URL", "").strip().rstrip("/")
    valid_api = urlparse(api_origin)
    valid_web = urlparse(web_origin)
    ready = bool(
        apikey and site_id and api_origin and web_origin
        and valid_api.scheme == "https" and valid_api.hostname
        and valid_web.scheme == "https" and valid_web.hostname
        and not valid_api.username and not valid_web.username
        and not valid_api.fragment and not valid_web.fragment
    )
    return {
        "enabled": ready, "provider": "cinetpay",
        "api_key": apikey if ready else "",
        "site_id": site_id if ready else "",
        "notify_url": api_origin + "/api/v1/subscriptions/checkout/notify/" if ready else "",
        "web_origin": web_origin if ready else "",
    }


def public_configuration():
    return {"enabled": configuration()["enabled"], "provider": "cinetpay", "currency": "XOF"}


def _response(url, payload):
    try:
        answer = requests.post(url, json=payload, timeout=(5, 20), allow_redirects=False)
        answer.raise_for_status()
        body = answer.json()
        if not isinstance(body, dict):
            raise ValueError("Réponse invalide.")
        return body
    except (requests.RequestException, ValueError) as error:
        raise CheckoutProviderError("Le fournisseur de paiement ne répond pas.") from error


def create_checkout(order):
    config = configuration()
    if not config["enabled"]:
        raise CheckoutConfigurationError("Paiement non configuré. Contactez G-Connect.")
    if order.currency != "XOF" or order.amount <= 0 or order.amount != order.amount.to_integral_value():
        raise CheckoutConfigurationError("Seuls les montants entiers XOF sont acceptés.")
    amount = int(order.amount)
    if amount % 5:
        raise CheckoutConfigurationError("Le montant XOF doit être un multiple de 5.")
    portal = "entreprise" if order.enterprise_id else "etablissement"
    payload = {
        "apikey": config["api_key"], "site_id": config["site_id"],
        "transaction_id": str(order.transaction_id).replace("-", ""),
        "amount": amount, "currency": order.currency,
        "description": "Abonnement G Connect "+portal,
        "return_url": config["web_origin"]+"/"+portal+"?checkout="+str(order.transaction_id)+"#subscription",
        "notify_url": config["notify_url"],
        "channels": "ALL", "lang": "fr",
        "metadata": str(order.pk),
    }
    body = _response(_CREATE, payload)
    link = body.get("data", {}).get("payment_url") if isinstance(body.get("data"), dict) else None
    if str(body.get("code")) != "201" or not isinstance(link, str):
        raise CheckoutProviderError("Le fournisseur n'a pas pu préparer le paiement.")
    parsed = urlparse(link)
    if (parsed.scheme != "https" or parsed.hostname != "checkout.cinetpay.com"
            or parsed.username or parsed.password):
        raise CheckoutProviderError("Adresse de paiement retournée non autorisée.")
    return link


def verify_checkout(order):
    config = configuration()
    if not config["enabled"]:
        raise CheckoutConfigurationError("Vérification de paiement indisponible.")
    body = _response(_CHECK, {
        "apikey": config["api_key"], "site_id": config["site_id"],
        "transaction_id": str(order.transaction_id).replace("-", ""),
    })
    data = body.get("data")
    if not isinstance(data, dict):
        raise CheckoutProviderError("Vérification du paiement impossible.")
    status = str(data.get("status", "")).upper()
    if status == "ACCEPTED":
        try:
            amount = Decimal(str(data.get("amount")))
        except (ValueError, TypeError):
            raise CheckoutProviderError("Montant de paiement non vérifiable.")
        if str(body.get("code")) != "00" or amount != order.amount or data.get("currency") != order.currency:
            raise CheckoutProviderError("Incohérence de montant ou de devise. Activation suspendue.")
        return "accepted"
    if status in ("REFUSED", "CANCELLED", "CANCELED"):
        return "refused"
    return "pending"
