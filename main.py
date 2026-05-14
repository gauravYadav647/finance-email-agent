import os
import argparse
from db import init_db
from data_loader import load_and_sanitize_csv
from email_generator import generate_email, get_stage_info
from audit_logger import log_audit_event

def run_agent():
    print("Initializing Database...")
    init_db()
    
    csv_file = "sample_data.csv"
    print(f"Loading data from {csv_file}...")
    records = load_and_sanitize_csv(csv_file)
    
    if not records:
        print("No valid records found.")
        return

    print(f"Processing {len(records)} valid records...\n")
    
    for record in records:
        invoice_no = record['invoice_no']
        days_overdue = record['days_overdue']
        stage = get_stage_info(days_overdue)
        
        print(f"--- Processing {invoice_no} (Days overdue: {days_overdue}) ---")
        
        if stage == 0:
            print("Action: ESCALATED. Skipping email.")
            log_audit_event(invoice_no, record['client_name'], record['contact_email'], record['amount_due'], days_overdue, record['followup_count'], stage, "", "", "ESCALATED", "")
            print("-" * 50 + "\n")
            continue
        elif stage == -1:
            print("Action: Not Overdue. Skipping email.")
            print("-" * 50 + "\n")
            continue
            
        print(f"Action: Generating email for Stage {stage}")
        
        # In a real app we would ensure API key is set before making calls
        if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
            print("ERROR: GEMINI_API_KEY not set in .env. Skipping API call.")
            log_audit_event(invoice_no, record['client_name'], record['contact_email'], record['amount_due'], days_overdue, record['followup_count'], stage, "", "", "API_KEY_MISSING", "GEMINI_API_KEY not set")
            print("-" * 50 + "\n")
            continue

        email, error, status = generate_email(record)
        
        if email:
            print("\n[SUCCESS] Generated Email:")
            print(f"Subject: {email.subject}")
            print(f"Body:\n{email.body}")
            dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
            send_status = "DRY_RUN" if dry_run else status
            log_audit_event(invoice_no, record['client_name'], record['contact_email'], record['amount_due'], days_overdue, record['followup_count'], stage, email.subject, email.body, send_status, "")
        else:
            print(f"\n[FAILED] Error: {error}")
            log_audit_event(invoice_no, record['client_name'], record['contact_email'], record['amount_due'], days_overdue, record['followup_count'], stage, "", "", status, error)
            
        print("-" * 50 + "\n")

def main():
    # Production: run behind firewall or VPN only
    parser = argparse.ArgumentParser(description="Finance Credit Follow-Up Email Agent")
    parser.add_argument('--run-once', action='store_true', help="Run the agent once and exit")
    args = parser.parse_args()

    if args.run_once:
        run_agent()
    else:
        import scheduler
        scheduler.start_scheduler()

if __name__ == "__main__":
    main()
