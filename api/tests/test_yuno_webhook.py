from app.security.yuno_webhook import (
    compute_yuno_webhook_signature,
    verify_yuno_webhook_signature,
)


def test_signature_is_base64_hmac_sha256_of_exact_raw_bytes() -> None:
    payload = b'{"event":"payment.updated","value":125.50}'
    signature = compute_yuno_webhook_signature(payload, "webhook-secret")

    assert signature == "x6x/nTbMRYXX115QCH2B399Z6FdtuoeGWLX7WoAGPR4="
    assert verify_yuno_webhook_signature(payload, signature, "webhook-secret")


def test_signature_rejects_reformatted_or_altered_payload() -> None:
    payload = b'{"event":"payment.updated","value":125.50}'
    signature = compute_yuno_webhook_signature(payload, "webhook-secret")

    assert not verify_yuno_webhook_signature(
        b'{"value":125.50,"event":"payment.updated"}',
        signature,
        "webhook-secret",
    )
    assert not verify_yuno_webhook_signature(payload + b"\n", signature, "webhook-secret")


def test_signature_rejects_wrong_secret_missing_and_malformed_headers() -> None:
    payload = b"{}"
    signature = compute_yuno_webhook_signature(payload, "webhook-secret")

    assert not verify_yuno_webhook_signature(payload, signature, "wrong-secret")
    assert not verify_yuno_webhook_signature(payload, None, "webhook-secret")
    assert not verify_yuno_webhook_signature(payload, "not base64!", "webhook-secret")
