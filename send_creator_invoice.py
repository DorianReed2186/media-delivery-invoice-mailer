"""Runnable delivery invoice example."""

from invoice_dispatcher import DeliveryInvoiceRequest, InfraiClient, InvoiceDispatcher


def main() -> None:
    request = DeliveryInvoiceRequest(
        customer_email="customer@example.com",
        customer_name="Mina Patel",
        asset_id="asset-clip-104",
        processing_job_id="job-transcode-104",
        creator_delivery_id="delivery-104",
        processing_status="delivered",
        amount_cents=4900,
        currency="USD",
    )
    client = InfraiClient.from_environment()
    issued = InvoiceDispatcher(client).issue(request)
    print(f"Invoice notice sent: {issued.message_id}")


if __name__ == "__main__":
    main()
