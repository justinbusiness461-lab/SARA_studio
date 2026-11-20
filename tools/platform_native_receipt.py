"""Server-side native store verified grant ingress.

A browser-supplied receipt is never an entitlement. Store verifier is host
injected, expected to call Apple App Store Server API or Google Play Developer
API and enforce environment, app/bundle ID, transaction status, product,
principal binding and revoked/refunded purchase semantics.
"""
from __future__ import annotations

import re
from platform_identity import PlatformDenied
from platform_billing import CreditLedger

def receive_verified_native_purchase(root,principal,payload,host_verify):
    if not callable(host_verify):raise PlatformDenied("STORE_VERIFICATION_REQUIRED")
    if not isinstance(payload,dict) or set(payload)!={"store","transactionId","productId","receipt"}:
        raise ValueError("INVALID_NATIVE_RECEIPT")
    store=payload["store"]
    tid=payload["transactionId"]
    product=payload["productId"]
    receipt=payload["receipt"]
    if store not in ("apple","google") or not isinstance(tid,str) or not re.fullmatch(
            r"[A-Za-z0-9._:-]{1,80}",tid) or not isinstance(product,str) or not re.fullmatch(
            r"[A-Za-z0-9._:-]{1,120}",product) or not isinstance(receipt,str) or not 8<=len(receipt)<=8192:
        raise ValueError("INVALID_NATIVE_TRANSACTION")
    # The verifier MUST use server-held provider credentials. Never treat
    # client-provided "verified", "credits", price or ownership as proof.
    verified=host_verify(store,tid,product,receipt,principal)
    if not isinstance(verified,dict) or verified.get("verified") is not True or (
      verified.get("store"),verified.get("transactionId"),verified.get("productId"),
      verified.get("principalId"))!=(store,tid,product,principal):
        raise PlatformDenied("NATIVE_TRANSACTION_NOT_HOST_VERIFIED")
    credits=verified.get("credits")
    if type(credits) is not int or not 1<=credits<=1000000:
        raise PlatformDenied("HOST_PRODUCT_CREDIT_MAPPING_UNQUALIFIED")
    event_id=f"native:{store}:{tid}"
    # The host verifier is the only trusted mint source; the existing ledger
    # owns atomic event-deduplication and cross-principal replay detection.
    ledger=CreditLedger(root)
    granted=ledger.grant_host_verified(principal,event_id,credits,
        lambda ev,quantity: ev==event_id and quantity==credits)
    return {"status":"SUCCESS","store":store,"storeTransactionId":event_id,
            "granted":granted,"credits":credits}
