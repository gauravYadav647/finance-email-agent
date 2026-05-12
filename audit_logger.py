from db import log_email
import os

def mask_email(email: str) -> str:
    if '@' not in email:
        return email
    first, domain = email.split('@', 1)
    return f"{first[0]}**@{domain}" if first else f"**@{domain}"

def log_audit_event(invoice_no: str, client_name: str, contact_email: str, amount_due: float, days_overdue: int, followup_count: int, tone_stage: int, subject: str, body: str, send_status: str, error_message: str):
    masked_email = mask_email(contact_email)
    print(f"[{send_status}] Email to: {masked_email}")
    body_preview = body[:100] if body else ""
    log_email(
        invoice_no=invoice_no,
        client_name=client_name,
        amount_due=amount_due,
        days_overdue=days_overdue,
        followup_count=followup_count,
        tone_stage=tone_stage,
        subject=subject,
        body_preview=body_preview,
        send_status=send_status,
        error_message=error_message
    )
