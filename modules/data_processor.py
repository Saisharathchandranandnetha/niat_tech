import pandas as pd
import streamlit as st
import re

def normalize_header(header):
    """Normalize string to lowercase alphanumeric for comparison"""
    return re.sub(r'[^a-zA-Z0-9]', '', str(header).lower())

def auto_detect_schema(df):
    """
    Heuristically maps dataframe columns to standardized roles:
    - CAMPUS
    - INSTRUCTOR
    - SUBJECT
    - SECTION
    - PROGRESS / STATUS
    - WEEK / TARGET
    """
    cols = df.columns.tolist()
    normalized_cols = {c: normalize_header(c) for c in cols}
    
    schema_map = {
        "campus": None,
        "instructor": None,
        "subject": None,
        "section": None,
        "status": None,
        "week": None
    }
    
    # 1. CAMPUS / LOCATION
    # Look for: 'campus', 'location', 'center', 'branch'
    campus_keywords = ['campus', 'location', 'center', 'branch', 'university']
    for col, norm in normalized_cols.items():
        if any(k in norm for k in campus_keywords):
            schema_map['campus'] = col
            break
            
    # 2. INSTRUCTOR
    # Look for: 'instructor', 'faculty', 'trainer', 'teacher', 'mentor'
    inst_keywords = ['instructor', 'faculty', 'trainer', 'teacher', 'mentor']
    for col, norm in normalized_cols.items():
        if any(k in norm for k in inst_keywords):
            schema_map['instructor'] = col
            break
            
    # 3. SUBJECT
    # Look for: 'subject', 'course', 'module', 'topic', 'syllabus'
    subject_keywords = ['subject', 'course', 'module'] 
    # Note: Topic is slightly different but often interchangeable in simple sheets
    for col, norm in normalized_cols.items():
        if any(k in norm for k in subject_keywords):
            schema_map['subject'] = col
            break

    # 4. SECTION
    # Look for: 'section', 'batch', 'group', 'class', 'hall'
    section_keywords = ['section', 'batch', 'group', 'class', 'hall']
    for col, norm in normalized_cols.items():
        if any(k in norm for k in section_keywords):
            schema_map['section'] = col
            break
            
    # 5. STATUS / PROGRESS
    # Look for: 'status', 'progress', 'completion', 'state'
    status_keywords = ['status', 'progress', 'completion', 'state', 'remarks']
    for col, norm in normalized_cols.items():
        # Avoid "Target" columns which might be "Expected Progress"
        if any(k in norm for k in status_keywords) and 'expected' not in norm and 'target' not in norm:
            schema_map['status'] = col
            break

    # 6. WEEK / TARGET 
    # Look for: 'week', 'target', 'date', 'session'
    week_keywords = ['week', 'target', 'session', 'day']
    for col, norm in normalized_cols.items():
        if any(k in norm for k in week_keywords):
            schema_map['week'] = col
            break
            
    return schema_map

def normalize_data(df, schema_map):
    """
    Renames columns to standard names based on the map.
    Fills 'Unknown' for missing core columns.
    Calculates a numeric 'completion_score' based on Status.
    """
    # Create mapping dict only for found columns
    rename_dict = { v: k.upper() for k, v in schema_map.items() if v is not None }
    
    # Rename
    normalized_df = df.rename(columns=rename_dict).copy()
    
    # Ensure all Standard Keys exist
    required_keys = ['CAMPUS', 'INSTRUCTOR', 'SUBJECT', 'SECTION', 'STATUS', 'WEEK']
    for k in required_keys:
        if k not in normalized_df.columns:
            normalized_df[k] = "Unknown"
            
    # Normalize STATUS to Numeric Score (0-1)
    # Heuristic: 
    # Done / Completed / Finished -> 1.0
    # In Progress / Ongoing -> 0.5
    # Pending / Not Started -> 0.0
    
    def get_score(status_val):
        s = str(status_val).lower().strip()
        if s in ['done', 'completed', 'finished', 'yes', 'y', '1', '1.0']:
            return 1.0
        elif s in ['in progress', 'ongoing', 'started', 'wip']:
            return 0.5
        return 0.0
        
    normalized_df['SCORE'] = normalized_df['STATUS'].apply(get_score)
    
    return normalized_df
