from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import date

class InvoiceRecord(BaseModel):
    invoice_no: str
    client_name: str
    amount_due: float
    due_date: str # keeping as string to match csv format easily
    contact_email: EmailStr
    days_overdue: int
    followup_count: int

class EmailOutput(BaseModel):
    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email containing required variables")

    @field_validator('body')
    @classmethod
    def check_required_variables(cls, v: str):
        required_vars = ["{client_name}", "{invoice_no}", "{amount_due}", "{due_date}", "{days_overdue}"]
        missing_vars = [var for var in required_vars if var not in v]
        if missing_vars:
            raise ValueError(f"Missing required variables in body: {', '.join(missing_vars)}")
        return v
