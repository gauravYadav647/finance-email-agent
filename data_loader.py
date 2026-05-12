import pandas as pd
from pydantic import ValidationError
from models import InvoiceRecord

def sanitise_record(val):
    if not isinstance(val, str):
        return val
    val = val.strip()
    for char in ['<', '>', '{', '}', '[', ']', '|', '\\', '`', '\n', '\r']:
        val = val.replace(char, '')
    return val

def load_and_sanitize_csv(file_path: str):
    try:
        df = pd.read_csv(file_path)
        # Drop rows where critical fields are entirely missing
        df = df.dropna(subset=['invoice_no', 'client_name', 'amount_due', 'days_overdue'])
        df = df.fillna({'due_date': '', 'contact_email': ''})
        
        valid_records = []
        for index, row in df.iterrows():
            try:
                # Apply sanitise_record
                record_dict = {k: sanitise_record(v) for k, v in row.to_dict().items()}
                # Ensure followup_count defaults to 0 if not present
                if 'followup_count' not in record_dict or pd.isna(record_dict['followup_count']):
                    record_dict['followup_count'] = 0
                else:
                    record_dict['followup_count'] = int(record_dict['followup_count'])
                    
                valid_record = InvoiceRecord(**record_dict)
                valid_records.append(valid_record.model_dump())
            except ValidationError as e:
                print(f"Skipping invalid row {index}: {row.get('invoice_no', 'Unknown')}. Error: {e}")
                
        return valid_records
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []
