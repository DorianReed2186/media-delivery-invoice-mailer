from typing import Any

import pytest

from invoice_dispatcher import DeliveryInvoiceRequest, InfraiClient, InvoiceDispatcher


class FakeClient(InfraiClient):
    def __init__(self) -> None:
        super().__init__(api_key="test-key")
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((path, body))
        if path == "/v1/email/send":
            return {"message_id": "msg-104"}
        return {}


def delivery(status: str = "delivered") -> DeliveryInvoiceRequest:
    return DeliveryInvoiceRequest(
        customer_email="buyer@example.com",
        customer_name="Rae Chen",
        asset_id="asset-104",
        processing_job_id="job-104",
        creator_delivery_id="delivery-104",
        processing_status=status,
        amount_cents=1250,
        currency="usd",
    )


def test_delivered_job_generates_pdf_then_sends_customer_notice() -> None:
    client = FakeClient()

    issued = InvoiceDispatcher(client).issue(delivery())

    assert issued.message_id == "msg-104"
    assert [call[0] for call in client.calls] == ["/v1/pdf/generate", "/v1/email/send"]
    assert client.calls[0][1]["store"] is False
    assert client.calls[1][1]["to"] == "buyer@example.com"
    assert "body" in client.calls[1][1]
    assert "text" not in client.calls[1][1]


def test_processing_job_does_not_issue_invoice() -> None:
    client = FakeClient()

    with pytest.raises(ValueError, match="creator delivery is complete"):
        InvoiceDispatcher(client).issue(delivery("processing"))

    assert client.calls == []
