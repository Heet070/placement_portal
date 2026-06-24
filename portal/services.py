import pandas as pd
from google import genai
from google.genai import types
import re
import io
import os
from django.db import connections

def is_safe_query(sql_query):
    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", 
        "TRUNCATE", "REPLACE", "GRANT", "REVOKE", "EXEC"
    ]
    pattern = r'\b(' + '|'.join(forbidden_keywords) + r')\b'
    return not bool(re.search(pattern, sql_query, re.IGNORECASE))

def get_db_schema():
    vendor = connections['readonly'].vendor
    schema_info = ""
    
    if vendor == 'sqlite':
        with connections['readonly'].cursor() as cursor:
            # Get user tables, excluding Django internal tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                  AND name NOT LIKE 'sqlite_%' 
                  AND name NOT LIKE 'django_%' 
                  AND name NOT LIKE 'auth_%'
                  AND name NOT LIKE 'admin_%';
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table_name in tables:
                schema_info += f"\nTable: {table_name}\n"
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                for col in columns:
                    # col[1] is name, col[2] is type
                    schema_info += f" - {col[1]} ({col[2]})\n"
    else:  # postgresql or standard SQL
        with connections['readonly'].cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                  AND table_name NOT LIKE 'django_%'
                  AND table_name NOT LIKE 'auth_%'
                  AND table_name NOT LIKE 'admin_%';
            """)
            rows = cursor.fetchall()
            
        current_table = ""
        for table_name, column_name, data_type in rows:
            if table_name != current_table:
                schema_info += f"\nTable: {table_name}\n"
                current_table = table_name
            schema_info += f" - {column_name} ({data_type})\n"
            
    return schema_info

def get_model_metadata():
    import json
    metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metadata.json')
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.dumps(json.load(f), indent=2)
        except Exception as e:
            print("Error loading metadata JSON:", e)
    return ""

def generate_excel_from_prompt(user_prompt):
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize Google Gemini API
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
    client = genai.Client(api_key=api_key)
    schema = get_db_schema()
    metadata = get_model_metadata()
    
    system_prompt = f"""
    You are an expert SQL data analyst. 
    Given the following database schema and model field metadata (which defines enums/choices), write a valid SQL query to answer the user's question. 
    
    Database Schema:
    {schema}
    
    Model Fields & Choice Options (Enums):
    {metadata}
    
    Instructions:
    1. Return ONLY the raw SQL query. Do not wrap the SQL query in markdown blocks like ```sql or ```.
    2. Pay close attention to enum choices (e.g. `placement_status` options: 'Unplaced', 'Placed', 'PPO', 'Summer Internship'). Match the capitalization and values exactly as defined in the metadata choices.
    3. If the user asks for 'placed' or 'placements', handle it appropriately based on the context (e.g. check for 'Placed', 'PPO', or 'Summer Internship' statuses as needed).
    4. AVOID SELECTING RAW FOREIGN KEY IDs. When the query requires displaying a reference to another table:
       - Instead of selecting raw ID fields (like `company_id`, `branch_id`, `profile_id`, `drive_id`, `cmp_id`, `round_id`), perform an INNER JOIN or LEFT JOIN with the target table and select the human-readable string column (e.g. select `company.cmp_name` instead of `student.company_id`, `branch.branch_name` instead of `student.branch_id`, `profile.profile_name` instead of `student.profile_id`, `drive.drive_name` instead of `student.drive_id`, `interview_round.round_name` instead of `round_student.round_id`, and `student.std_name` instead of `round_student.student_id`).
       - Ensure you alias columns appropriately (e.g. `AS company_name`, `AS branch_name`, `AS round_name`, `AS student_name`, etc.) so the generated Excel headers are clean and descriptive.
    5. When the user asks about recruitment rounds, shortlists, or student interview progress, query the `interview_round` and `round_student` tables. For example:
       - To find students in a specific round, join `student` and `interview_round` via `round_student`.
       - To check if a round is the interview shortlist, check `interview_round.is_interview_shortlist = true` or `1`.
       - To check if a round is the final results round, check `interview_round.is_final = true` or `1`.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        )
    )
    
    raw_sql = response.text.strip().replace('```sql', '').replace('```', '')
    if not is_safe_query(raw_sql):
        raise ValueError("Unsafe SQL query generated.")

    db_settings = connections['readonly'].settings_dict
    vendor = connections['readonly'].vendor
    
    if vendor == 'sqlite':
        db_path = db_settings['NAME']
        engine_uri = f"sqlite:///{db_path}"
    else:
        engine_uri = f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
    
    df = pd.read_sql_query(raw_sql, engine_uri)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    
    excel_buffer.seek(0) 
    return excel_buffer
