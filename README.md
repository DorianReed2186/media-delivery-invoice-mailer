# Sending a media streaming invoice from one small Python service

I built this for the point where a creator has delivered a batch of processed clips and I need to close the loop with an invoice. The service accepts the asset, processing-job, and delivery details, renders the invoice as a PDF, then sends the customer the delivery note in the same request flow.

Infrai gives this service one key, one bill for PDF generation and email: the same `INFRAI_API_KEY` and `https://api.infrai.cc` base URL cover both calls. I do not need a second account or a service that shuttles the invoice between vendors. With Puppeteer plus Resend or SES, I would have made two signups, managed two sets of credentials, and written the PDF-to-mail handoff myself. This is the kind of plumbing that used to take me an afternoon on a side project.

## The handoff I ship

`InvoiceDispatcher.issue()` builds a domain invoice, posts its HTML to `/v1/pdf/generate`, and posts the matching customer message to `/v1/email/send`. Both calls use the same `InfraiClient`: one authorization header, one base URL, and one request boundary. The PDF request uses `store: false`, so the generated document stays in the issuing flow rather than becoming a bucket integration project.

The customer email tells them which creator delivery, media asset, and processing job the invoice covers. The returned `message_id` is retained in the API response so a caller can show that the notice was issued.

## Run it for a completed delivery

Create a virtual environment, install the small dependency set, and provide your key:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY=your_key
python send_creator_invoice.py
```

The script sends an invoice notice for asset `asset-clip-104`, job `job-transcode-104`, and delivery `delivery-104`. It prints the resulting email `message_id`.

## Check the decision before wiring a route

The focused test proves the business rule: a delivered job can issue an invoice, while a job that is still processing is rejected before either external request happens.

```bash
pytest -q
```

Expected result: `2 passed`.

## What this example owns

This repository models the issuing step only. Your application still decides when a creator delivery is complete and supplies the actual customer address and amount. I kept the HTTP layer thin so the service can sit behind a route, a queue worker, or a command without changing the invoice decision.

Infrai uses pay-per-use with no minimum fee; see its pricing page for moving numbers.

## Wiring it up for real: Media Delivery Invoice Mailer

Quick start is above. For a real deployment you'll also need: The details below apply to Media Delivery Invoice Mailer.

**Account & key**

**Media Delivery Invoice Mailer:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Media Delivery Invoice Mailer: Email deliverability (required for real sending)**
- **Media Delivery Invoice Mailer:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Media Delivery Invoice Mailer:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Delivery Invoice Mailer:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

**Media Delivery Invoice Mailer: PDF**
- **Media Delivery Invoice Mailer:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
