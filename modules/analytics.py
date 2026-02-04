import pandas as pd

def compute_kpis(df):
    """
    Computes global overhead figures:
    - Total Campuses
    - Total Instructors
    - Completion %
    - At-Risk Count
    """
    if df.empty:
        return {}
        
    total_records = len(df)
    completed_score_sum = df['SCORE'].sum() # Sum of 1s (Done) and 0.5s (In Progress)
    
    # Global Completion % (Average of scores)
    global_completion = (completed_score_sum / total_records * 100) if total_records > 0 else 0
    
    # At Risk Analysis
    # Define At Risk: Instructor average completion < 50%
    instructor_scores = df.groupby('INSTRUCTOR')['SCORE'].mean()
    at_risk_count = len(instructor_scores[instructor_scores < 0.5])
    
    return {
        "num_campuses": df['CAMPUS'].nunique(),
        "num_instructors": df['INSTRUCTOR'].nunique(),
        "num_subjects": df['SUBJECT'].nunique(),
        "global_completion": round(global_completion, 1),
        "at_risk_instructors": at_risk_count
    }

def compute_instructor_performance(df):
    """
    Aggregates data by Instructor for the drill-down table.
    """
    if df.empty:
        return pd.DataFrame()
        
    # Group by Instructor + Campus
    grouped = df.groupby(['INSTRUCTOR', 'CAMPUS']).agg(
        Total_Items=('SUBJECT', 'count'),
        Completed_Score_Sum=('SCORE', 'sum')
    ).reset_index()
    
    # Calculate %
    grouped['Completion_Pct'] = (grouped['Completed_Score_Sum'] / grouped['Total_Items']) * 100
    grouped['Completion_Pct'] = grouped['Completion_Pct'].round(1)
    
    # Determine Status Label based on Pct
    def label_status(pct):
        if pct >= 80: return "On Track ✅"
        elif pct >= 50: return "Delayed ⚠️"
        return "Critical 🔴"
        
    grouped['Status'] = grouped['Completion_Pct'].apply(label_status)
    
    return grouped.sort_values(by='Completion_Pct', ascending=True) # Show worst first?

def compute_risk_factors(df):
    """
    Identifies specific risky entities.
    Returns lists of:
    - Critical Departments (Campus)
    - Critical Instructors
    """
    if df.empty:
        return {"campuses": [], "instructors": []}
        
    # Campus Risk
    campus_scores = df.groupby('CAMPUS')['SCORE'].mean()
    risky_campuses = campus_scores[campus_scores < 0.6].index.tolist()
    
    # Instructor Risk
    inst_scores = df.groupby('INSTRUCTOR')['SCORE'].mean()
    risky_instructors = inst_scores[inst_scores < 0.5].index.tolist()
    
    return {
        "campuses": risky_campuses,
        "instructors": risky_instructors
    }

def build_ai_summary(df, context="overall"):
    """
    Creates a lightweight, context-aware JSON summary for the AI Assistant.
    Follows strict aggregation rules: Python calculates, AI explains.
    """
    if df.empty:
        return {"context": context, "error": "No data available in current filter"}
        
    # 1. Compute Base Metrics
    total_records = len(df)
    avg_completion = df['SCORE'].mean() * 100
    
    # 2. Status Distribution
    status_dist = df['STATUS'].value_counts().to_dict()
    
    # 3. Identify At-Risk Items (Top 5 for context)
    # Filter for low scores (< 0.5 i.e. 50%)
    risk_df = df[df['SCORE'] < 0.5]
    
    at_risk_items = []
    if not risk_df.empty:
        # Select relevant columns for the snippet
        cols_to_keep = ['INSTRUCTOR', 'CAMPUS', 'SUBJECT', 'SECTION', 'STATUS']
        # Only keep cols that exist
        cols_to_keep = [c for c in cols_to_keep if c in df.columns]
        
        at_risk_items = risk_df[cols_to_keep].head(5).to_dict(orient='records')

    # 4. Construct Final JSON
    summary = {
        "context": context,
        "total_records": total_records,
        "average_completion_pct": round(avg_completion, 1),
        "status_distribution": status_dist,
        "at_risk_preview": at_risk_items,
        "risk_count": len(risk_df),
        "unique_instructors": df['INSTRUCTOR'].nunique(),
        "unique_campuses": df['CAMPUS'].nunique()
    }
    
    # Add optional Hall/Section breakdown if relevant
    if 'SECTION' in df.columns:
        summary["active_sections"] = df['SECTION'].nunique()
    
    return summary
