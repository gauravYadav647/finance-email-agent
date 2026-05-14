import os
from flask import Flask, request, jsonify, render_template
import pandas as pd
from werkzeug.utils import secure_filename
from models import InvoiceRecord
from db import init_db
from email_generator import generate_email, get_stage_info
from data_loader import sanitise_record
from audit_logger import log_audit_event
from pydantic import ValidationError

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

init_db()

@app.before_request
def check_api_key():
    if request.endpoint == 'process_csv':
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.environ.get('AGENT_API_KEY'):
            return jsonify({"error": "Unauthorized"}), 401

@app.route('/')
def index():
    return render_template('index.html', api_key=os.environ.get('AGENT_API_KEY', ''))

@app.route('/api/process', methods=['POST'])
def process_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            df = pd.read_csv(filepath)
            # Basic sanitization
            df = df.dropna(subset=['invoice_no', 'client_name', 'amount_due', 'days_overdue'])
            df = df.fillna({'due_date': '', 'contact_email': ''})
            
            results = []
            
            for index, row in df.iterrows():
                try:
                    record_dict = {k: sanitise_record(v) for k, v in row.to_dict().items()}
                    if 'followup_count' not in record_dict or pd.isna(record_dict['followup_count']):
                        record_dict['followup_count'] = 0
                    else:
                        record_dict['followup_count'] = int(record_dict['followup_count'])
                        
                    valid_record = InvoiceRecord(**record_dict).model_dump()
                    
                    invoice_no = valid_record['invoice_no']
                    days_overdue = valid_record['days_overdue']
                    stage = get_stage_info(days_overdue)
                    
                    if stage == 0:
                        log_audit_event(invoice_no, valid_record['client_name'], valid_record['contact_email'], valid_record['amount_due'], days_overdue, valid_record['followup_count'], stage, "", "", "ESCALATED", "")
                        results.append({
                            "invoice_no": invoice_no,
                            "client_name": valid_record['client_name'],
                            "days_overdue": days_overdue,
                            "status": "ESCALATED",
                            "message": "Action: ESCALATED. Skipping email generation."
                        })
                        continue
                    elif stage == -1:
                        results.append({
                            "invoice_no": invoice_no,
                            "status": "SKIP",
                            "message": "Not overdue."
                        })
                        continue
                        
                    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
                        log_audit_event(invoice_no, valid_record['client_name'], valid_record['contact_email'], valid_record['amount_due'], days_overdue, valid_record['followup_count'], stage, "", "", "API_KEY_MISSING", "GEMINI_API_KEY not set")
                        results.append({
                            "invoice_no": invoice_no,
                            "client_name": valid_record['client_name'],
                            "days_overdue": days_overdue,
                            "status": "FAILED",
                            "message": "ERROR: GEMINI_API_KEY not set in .env"
                        })
                        continue

                    email, error, status = generate_email(valid_record)
                    
                    if email:
                        dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
                        send_status = "DRY_RUN" if dry_run else status
                        log_audit_event(invoice_no, valid_record['client_name'], valid_record['contact_email'], valid_record['amount_due'], days_overdue, valid_record['followup_count'], stage, email.subject, email.body[:100], send_status, "")
                        results.append({
                            "invoice_no": invoice_no,
                            "client_name": valid_record['client_name'],
                            "days_overdue": days_overdue,
                            "status": "SUCCESS",
                            "stage": stage,
                            "email": email.model_dump()
                        })
                    else:
                        log_audit_event(invoice_no, valid_record['client_name'], valid_record['contact_email'], valid_record['amount_due'], days_overdue, valid_record['followup_count'], stage, "", "", status, error)
                        results.append({
                            "invoice_no": invoice_no,
                            "client_name": valid_record['client_name'],
                            "days_overdue": days_overdue,
                            "status": "FAILED",
                            "message": error
                        })
                except ValidationError as e:
                    results.append({
                        "invoice_no": row.get('invoice_no', 'Unknown'),
                        "status": "FAILED",
                        "message": f"Validation Error: {str(e)}"
                    })
            
            return jsonify({"results": results})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid file type. Please upload a CSV."}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)


