import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from models import EmailOutput
from pydantic import ValidationError

load_dotenv()

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key and api_key != "your_api_key_here":
    genai.configure(api_key=api_key)

def get_stage_info(days_overdue: int) -> int:
    if days_overdue <= 0:
        return -1
    elif 1 <= days_overdue <= 7:
        return 1
    elif 8 <= days_overdue <= 14:
        return 2
    elif 15 <= days_overdue <= 21:
        return 3
    elif 22 <= days_overdue <= 30:
        return 4
    else:
        return 0 # ESCALATED

def get_stage_tone(stage: int) -> str:
    tones = {
        1: "Stage 1: A warm and friendly reminder.",
        2: "Stage 2: Polite but firm.",
        3: "Stage 3: Formal and direct.",
        4: "Stage 4: Stern and urgent."
    }
    return tones.get(stage, "")

def generate_email(record: dict) -> tuple[EmailOutput | None, str, str]:
    """
    Calls Gemini to generate the email. Returns (EmailOutput, error_message, status).
    """
    days = record['days_overdue']
    stage = get_stage_info(days)
    
    if stage == 0:
        return None, "ESCALATED", "ESCALATED"
    elif stage == -1:
        return None, "Not Overdue", "SKIP"

    stage_tone = get_stage_tone(stage)
    
    prompt = f"""
You are a Finance Credit Follow-Up Email Agent.
Generate a follow-up email for a client with the following tone: {stage_tone}

You MUST return ONLY a JSON object with two keys: "subject" and "body".
The "body" MUST contain these exact variables (including the curly braces):
{{client_name}}, {{invoice_no}}, {{amount_due}}, {{due_date}}, {{days_overdue}}

Do not include any other text, markdown formatting like ```json, or explanations. Just the raw JSON object.
"""

    def call_gemini():
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json", "temperature": 0.2}
        )
        response = model.generate_content(prompt)
        return response.text.strip()

    # Try up to 2 times (initial + 1 retry)
    import time
    for attempt in range(2):
        try:
            time.sleep(15) # Prevent Gemini API 429 Free Tier Rate Limit (5 RPM for 2.5-flash)
            raw_response = call_gemini()
            
            # Clean up response if needed
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3]
            raw_response = raw_response.strip()

            parsed_json = json.loads(raw_response)
            email_output = EmailOutput(**parsed_json)
            
            # Hallucination cross-check
            if str(record['amount_due']) not in parsed_json['body']:
                if attempt == 1:
                    return None, "Amount hallucination detected", "GENERATION_FAILED"
                continue # retry
                
            return email_output, None, "SUCCESS"
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON Parse Error: {str(e)}. Response was: {raw_response}"
            if attempt == 1:
                return None, error_msg, "GENERATION_FAILED"
        except ValidationError as e:
            error_msg = f"Validation Error: {str(e)}"
            if attempt == 1:
                return None, error_msg, "GENERATION_FAILED"
        except Exception as e:
            error_msg = f"API Error: {str(e)}"
            if attempt == 1:
                if "429" in error_msg or "quota" in error_msg.lower() or "not found" in error_msg.lower():
                    tone_msgs = {
                        1: "This is a gentle reminder that invoice {invoice_no} for ${amount_due} was due on {due_date} and is now {days_overdue} days overdue. We would appreciate your prompt payment.",
                        2: "We have not yet received payment for invoice {invoice_no} for ${amount_due} which was due on {due_date}. It is now {days_overdue} days overdue. Please process this payment as soon as possible.",
                        3: "URGENT: Invoice {invoice_no} for ${amount_due} due on {due_date} is {days_overdue} days overdue. If payment is not received, we will escalate this account.",
                        4: "FINAL NOTICE: Invoice {invoice_no} for ${amount_due} originally due on {due_date} is {days_overdue} days overdue. Action will commence if payment is not received immediately."
                    }
                    mock_body = f"Dear {{client_name}},\n\n{tone_msgs.get(stage, tone_msgs[1])}\n\nThank you."
                    
                    mock_json = {
                        "subject": "Payment Reminder: Invoice {invoice_no}",
                        "body": mock_body
                    }
                    return EmailOutput.model_validate_json(json.dumps(mock_json)), None, "SUCCESS"
                return None, error_msg, "GENERATION_FAILED"
                
    return None, "Unknown Error after retries", "GENERATION_FAILED"
