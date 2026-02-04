import json
import streamlit as st
from groq import Groq

def get_groq_client(api_key):
    return Groq(api_key=api_key)

def detect_schema_with_ai(df, api_key):
    """
    Sends column names and sample data to Groq to infer the schema.
    Returns a dict mapping standard keys to actual column names.
    """
    client = get_groq_client(api_key)
    
    # Context for AI
    columns = df.columns.tolist()
    sample_data = df.head(3).to_dict(orient='records')
    
    prompt = f"""
    You are a Data Architect. I have an Excel sheet from a university.
    Your job is to map the columns to a Standard Schema.

    Standard Schema Keys needed:
    - "campus": (e.g. Campus, Location, Center)
    - "instructor": (e.g. Faculty, Trainer, Teacher)
    - "subject": (e.g. Course, Module, Topic)
    - "section": (e.g. Batch, Group)
    - "status": (e.g. Progress, Remarks, State)
    - "week": (e.g. Session, Week, Target)

    Here is the Data:
    Columns: {columns}
    Sample Row 1: {sample_data[0] if len(sample_data) > 0 else "N/A"}

    Return ONLY a JSON object. No explanation.
    Format:
    {{
        "campus": "ActualColumnNameOrNull",
        "instructor": "ActualColumnNameOrNull",
        "subject": "ActualColumnNameOrNull",
        "section": "ActualColumnNameOrNull",
        "status": "ActualColumnNameOrNull",
        "week": "ActualColumnNameOrNull"
    }}
    If a column is missing, set value to null.
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Updated model
            messages=[
                {"role": "system", "content": "You are a JSON-only response bot."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        response_content = completion.choices[0].message.content
        return json.loads(response_content)
        
    except Exception as e:
        st.error(f"AI Detection Failed: {e}")
        return None

def generate_analysis(summary_json, user_query, api_key):
    """
    Asks the AI to analyze the aggregated summary with context-aware prompting.
    """
    client = get_groq_client(api_key)
    
    context = summary_json.get("context", "overall")
    
    # 1. Base Prompt (Mandatory Rules)
    base_prompt = """
    You are an academic performance analyst assisting a university manager.
    RULES:
    - Base answers ONLY on the provided JSON data summary.
    - Do NOT invent missing data.
    - Highlight risks (low completion, delays) clearly.
    - Keep language professional, concise, and executive-friendly.
    """
    
    # 2. Context-Specific Instructions
    context_prompts = {
        "campus": "Focus on campus-wide performance, hall-wise distribution, and identifying lagging subjects/instructors within this campus.",
        "instructor": "Focus on this instructor's syllabus progress, theory vs practice balance, and specific delayed items.",
        "course": "Analyze the performance of this subject across all campuses. Compare completion rates between sections.",
        "overall": "Provide a high-level executive summary of the entire university. Highlight top-performing and lowest-performing areas."
    }
    
    specific_instruction = context_prompts.get(context, context_prompts["overall"])
    
    system_prompt = f"{base_prompt}\n\nCURRENT CONTEXT: {context.upper()}\n{specific_instruction}"
    
    user_prompt = f"""
    Here is the Aggregated Data Summary:
    {json.dumps(summary_json, indent=2)}
    
    Manager's Question: "{user_query}"
    
    Provide a concise, insight-driven answer.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3, # Low temp for factual answers
            max_tokens=600
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Analysis Failed: {e}"
