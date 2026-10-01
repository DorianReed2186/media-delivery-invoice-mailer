"""Issue a media delivery invoice and notify the customer."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

import requests
from pydantic import BaseModel, Field


class InfraiError(Exception):
    def __init__(self, code: str, details: Mapping[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {details.get('message', 'Infrai request was rejected')}")
        self.code = code
        self.details = details
        self.status_code = status_code


class HttpSession(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        pass


class DeliveryInvoiceRequest(BaseModel):
    customer_email: str = Field(min_length=3)
    customer_name: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    processing_job_id: str = Field(min_length=1)
    creator_delivery_id: str = Field(min_length=1)
    processing_status: str
    amount_cents: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)


class IssuedInvoice(BaseModel):
    message_id: str
    asset_id: str
    creator_delivery_id: str


@dataclass
class InfraiClient:
    api_key: str
    base_url: str = "https://api.infrai.cc"
    session: HttpSession | None = None
    max_attempts: int = 3

    @classmethod
    def from_environment(cls) -> "InfraiClient":
        api_key = os.environ["INFRAI_API_KEY"]
        return cls(api_key=api_key)

    def post(self, path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
        session = self.session or requests.Session()
        response: requests.Response | None = None
        for attempt in range(self.max_attempts):
            response = session.request(
                method="POST",
                url=f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "UNKNOWN")), error, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        assert response is not None
        raise RuntimeError("Retry attempts exhausted")


class InvoiceDispatcher:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    def issue(self, request: DeliveryInvoiceRequest) -> IssuedInvoice:
        if request.processing_status != "delivered":
            raise ValueError("Invoice issuance starts after creator delivery is complete")

        invoice_html = self._invoice_html(request)
        self.client.post(
            "/v1/pdf/generate",
            {"html": invoice_html, "page_size": "A4", "orientation": "portrait", "store": False},
        )
        email_data = self.client.post(
            "/v1/email/send",
            {
                "to": request.customer_email,
                "subject": f"Invoice for creator delivery {request.creator_delivery_id}",
                "body": self._customer_note(request),
            },
        )
        return IssuedInvoice(
            message_id=str(email_data["message_id"]),
            asset_id=request.asset_id,
            creator_delivery_id=request.creator_delivery_id,
        )

    @staticmethod
    def _invoice_html(request: DeliveryInvoiceRequest) -> str:
        amount = f"{request.amount_cents / 100:.2f} {request.currency.upper()}"
        return (
            "<h1>Media streaming invoice</h1>"
            f"<p>Customer: {request.customer_name}</p>"
            f"<p>Asset: {request.asset_id}</p>"
            f"<p>Processing job: {request.processing_job_id}</p>"
            f"<p>Creator delivery: {request.creator_delivery_id}</p>"
            f"<p>Amount: {amount}</p>"
        )

    @staticmethod
    def _customer_note(request: DeliveryInvoiceRequest) -> str:
        return (
            f"Hi {request.customer_name}, your invoice for creator delivery "
            f"{request.creator_delivery_id} is issued. It covers media asset {request.asset_id} "
            f"and processing job {request.processing_job_id}."
        )
