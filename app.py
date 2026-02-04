import streamlit as st
import pandas as pd
import plotly.express as px
from modules.data_processor import auto_detect_schema, normalize_data
from modules.analytics import compute_kpis, compute_instructor_performance, compute_risk_factors

st.set_page_config(page_title="Universal Academic Dashboard", layout="wide", page_icon="🎓")

# --- CSS Styling ---
st.markdown("""
    <style>
    /* Global Background */
    .main {
        background-color: #0e1117;
    }
    
    /* Metrics Cards */
    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background-color: #1f2937; /* Dark Gray */
        border: 1px solid #374151;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: 0.2s;
        color: white;
    }
    
    div[data-testid="stMetric"]:hover {
        border-color: #60a5fa; /* Blue hover */
        transform: translateY(-2px);
    }
    
    /* Metric Label (Top text) */
    div[data-testid="stMetric"] label {
        color: #9ca3af !important; /* Muted gray */
        font-size: 0.9rem !important;
    }
    
    /* Metric Value (Big number) */
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f3f4f6 !important; /* Brighter white */
        font-weight: 700 !important;
    }
    
    /* Headers */
    h1, h2, h3 { 
        color: #f8fafc !important; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Divider */
    hr {
        margin: 2em 0;
        border-color: #334155;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #374151;
    }
    </style>
""", unsafe_allow_html=True)

# --- Title ---
st.title("🎓 Universal Academic Performance Dashboard")
st.markdown("Upload any syllabus/tracking sheet to generate insights automatically.")

# --- Groq API Key ---
api_key = st.sidebar.text_input("🔑 Groq API Key", type="password", help="Required for AI Schema Detection")

# --- File Upload ---
uploaded_file = st.sidebar.file_uploader("📂 Upload Data File", type=["xlsx", "csv"])

if uploaded_file is not None:
    # 1. Load Data
    try:
        if uploaded_file.name.endswith('.csv'):
            df_raw = pd.read_csv(uploaded_file)
        else:
            df_raw = pd.read_excel(uploaded_file)
            
        st.success(f"Loaded {len(df_raw)} rows successfully.")
        
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()

    # 2. Process Data (AI vs Heuristic)
    with st.spinner("Analyzing schema..."):
        from modules.ai_mapper import detect_schema_with_ai
        
        schema = None
        if api_key:
            try:
                schema = detect_schema_with_ai(df_raw, api_key)
                if schema:
                     st.toast("✅ AI Schema Detection Successful!")
            except Exception as e:
                st.warning(f"AI Failed: {e}. Falling back to rules.")
        
        if not schema:
            st.info("Using Heuristic Detection (No API Key provided or AI failed)")
            schema = auto_detect_schema(df_raw)
        
        # Display detected schema for verification
        with st.expander("🛠️ Detected Schema (Mapping)"):
            st.json(schema)
            
        df = normalize_data(df_raw, schema)
        
    # 3. Sidebar Filters
    st.sidebar.header("🔍 Filters Setup")
    
    # Campus Filter
    all_campuses = sorted(df['CAMPUS'].unique().astype(str))
    selected_campuses = st.sidebar.multiselect("Select Campus", all_campuses, default=all_campuses)
    
    # Instructor Filter
    if selected_campuses:
        # Filter RAW data for options list to be relevant
        df_for_options = df[df['CAMPUS'].astype(str).isin(selected_campuses)]
    else:
        df_for_options = df

    all_instructors = sorted(df_for_options['INSTRUCTOR'].unique().astype(str))
    selected_instructors = st.sidebar.multiselect("Select Instructor", all_instructors, default=all_instructors)
    
    # --- APPLY FILTERS (Core Logic) ---
    df_filtered = df.copy()
    
    # Filter 1: Campus
    if selected_campuses:
        df_filtered = df_filtered[df_filtered['CAMPUS'].astype(str).isin(selected_campuses)]
        
    # Filter 2: Instructor
    if selected_instructors:
        df_filtered = df_filtered[df_filtered['INSTRUCTOR'].astype(str).isin(selected_instructors)]
        
    # Debug row count
    # st.sidebar.info(f"Filtered Rows: {len(df_filtered)}")

    # 4. Render Logic (Dynamic View)
    st.divider()
    
    # determine view mode
    is_single_instructor = (len(selected_instructors) == 1)
    
    if is_single_instructor:
        instructor_name = selected_instructors[0]
        st.header(f"👨‍🏫 Instructor Overview: {instructor_name}")
    else:
        st.header("📊 Executive Overview")
    
    # COMPUTE KPIS ON FILTERED DATA
    kpis = compute_kpis(df_filtered)
    
    # Row 1: High Level Counts
    cols = st.columns(5)
    cols[0].metric("Instructors", kpis.get('num_instructors', 0))
    cols[1].metric("Campuses", kpis.get('num_campuses', 0))
    cols[2].metric("Subjects", kpis.get('num_subjects', 0)) # New
    cols[3].metric("Active Sections", df_filtered['SECTION'].nunique()) # New
    cols[4].metric("At Risk", kpis.get('at_risk_instructors', 0), delta_color="inverse")

    # Row 2: Performance Metrics (Styled)
    st.markdown("###")
    m1, m2, m3 = st.columns(3)
    
    global_rate = kpis.get('global_completion', 0)
    m1.metric("⭐ Global Completion Rate", f"{global_rate}%", delta=f"{global_rate-100}% of target" if global_rate < 100 else "Completed")
    
    # Calculate Theory vs Practice if possible (heuristic)
    # Simple check if SUBJECT/TOPIC contains 'Lab' or 'Practice'
    lab_count = df_filtered[df_filtered['SUBJECT'].str.contains('Lab|Practice|Practical', case=False, na=False)].shape[0]
    total_count = len(df_filtered)
    lab_ratio = (lab_count / total_count * 100) if total_count > 0 else 0
    
    m2.metric("🔬 Practical/Lab Focus", f"{round(lab_ratio, 1)}%", help="% of syllabus items identified as Labs")
    m3.metric("📅 Total Tracks/Rows", total_count)
    
    # Charts Row 1
    c1, c2 = st.columns(2)
    
    with c1:
        if is_single_instructor:
            st.subheader("Weekly Progress")
            # If week detection works, show robust line chart
            # else show simple status distribution
            if 'WEEK' in df_filtered.columns and df_filtered['WEEK'].nunique() > 1:
                # Attempt to sort weeks logic
                week_prog = df_filtered.groupby('WEEK')['SCORE'].mean().reset_index()
                fig_prog = px.line(week_prog, x='WEEK', y='SCORE', markers=True, title="Completion Score over Weeks")
                st.plotly_chart(fig_prog, use_container_width=True)
            else:
                 fig_hist = px.pie(df_filtered, names="STATUS", title="Status Breakdown")
                 st.plotly_chart(fig_hist, use_container_width=True)

        else:
            st.subheader("Performance by Campus")
            # Calc Aggregation
            campus_perf = df_filtered.groupby('CAMPUS')['SCORE'].mean().reset_index()
            campus_perf['Completion %'] = (campus_perf['SCORE'] * 100).round(1)
            
            fig_campus = px.bar(campus_perf, x='CAMPUS', y='Completion %', 
                               color='Completion %', color_continuous_scale='RdBu')
            st.plotly_chart(fig_campus, use_container_width=True)

    with c2:
        st.subheader("Performance Distribution")
        fig_hist = px.histogram(df_filtered, x="SCORE", nbins=5, title="Task Completion Distribution (0=Pending, 1=Done)")
        st.plotly_chart(fig_hist, use_container_width=True)

    # --- NEW: Heatmap & Hall View ---
    st.divider()
    c3, c4 = st.columns([2, 1])
    
    with c3:
        st.subheader("🔥 Subject Performance Heatmap")
        # Aggregation: Campus x Subject -> Avg Score
        heatmap_data = df_filtered.groupby(['CAMPUS', 'SUBJECT'])['SCORE'].mean().reset_index()
        heatmap_data['Completion %'] = (heatmap_data['SCORE'] * 100).round(0)
        
        fig_heat = px.density_heatmap(
            heatmap_data, 
            x='CAMPUS', 
            y='SUBJECT', 
            z='Completion %', 
            text_auto=True,
            color_continuous_scale='Viridis',
            title="Avg Completion % by Campus & Subject"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with c4:
        st.subheader("🏫 Hall / Section Breakdown")
        # Aggregation: Section -> Avg Score
        if 'SECTION' in df_filtered.columns:
            section_data = df_filtered.groupby('SECTION').agg(
                Size=('INSTRUCTOR', 'count'),
                Avg_Completion=('SCORE', 'mean')
            ).reset_index()
            section_data['Avg_Completion'] = (section_data['Avg_Completion'] * 100).round(1)
            
            st.dataframe(
                section_data, 
                use_container_width=True,
                column_config={
                    "Avg_Completion": st.column_config.ProgressColumn(
                        "Progress", 
                        format="%.1f%%", 
                        min_value=0, 
                        max_value=100
                    )
                },
                hide_index=True
            )
        else:
            st.info("No 'Section' or 'Hall' column detected.")

    # 5. Instructor Drill-Down (Always visible but filtered)
    st.divider()
    if not is_single_instructor:
        st.header("Detailed Instructor Tracker")
    else:
        st.header("Detailed Syllabus Items")
        
    if is_single_instructor:
        # Show raw items for the single instructor
        st.dataframe(df_filtered[['SUBJECT', 'SECTION', 'WEEK', 'STATUS', 'SCORE']], use_container_width=True)
    else:
        # Show Aggregate Table
        instructor_table = compute_instructor_performance(df_filtered)
        
        st.dataframe(
            instructor_table,
            use_container_width=True,
            column_config={
                "Completion_Pct": st.column_config.ProgressColumn(
                    "Completion %",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                 "Status": st.column_config.TextColumn("Status Mode")
            }
        )

    # 6. Risk Panel
    risks = compute_risk_factors(df_filtered)
    if risks['instructors']:
        st.error(f"⚠️ **Attention Required**: {len(risks['instructors'])} Instructors are critically behind schedule.")
        st.write(risks['instructors'])
    else:
        st.success("✅ No critical delays detected.")

    # 7. AI Assistant Interface
    if api_key:
        st.sidebar.divider()
        st.sidebar.header("🤖 AI Analyst")
        
        # --- Context Detection Logic ---
        # Heuristic: 
        # Logic: If 1 Instructor Selected -> 'instructor'
        # Logic: If >1 Instructor but 1 Campus -> 'campus' (Assuming instructors belong to that campus)
        # Logic: Else -> 'overall'
        
        context = "overall"
        if is_single_instructor:
            context = "instructor"
        elif selected_campuses and len(selected_campuses) == 1 and len(selected_instructors) > 1:
            context = "campus"
        
        # Display Context Badge
        st.sidebar.caption(f"Current Mode: **{context.upper()} Analyst**")
        
        from modules.analytics import build_ai_summary
        from modules.ai_mapper import generate_analysis

        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "I am analyzing the current view. Ask me about risks, performance, or specific metrics."}]

        # Chat Input
        if prompt := st.sidebar.chat_input("Ask about performance..."):
            st.session_state["messages"].append({"role": "user", "content": prompt})
            
            # Prepare context
            summary_context = build_ai_summary(df_filtered, context=context)
            
            # Debug: Show what we send to AI (Hidden by default, useful for verification)
            # st.sidebar.json(summary_context, expanded=False)
            
            with st.sidebar.chat_message("user"):
                st.write(prompt)
                
            with st.sidebar.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    response = generate_analysis(summary_context, prompt, api_key)
                    st.write(response)
                    st.session_state["messages"].append({"role": "assistant", "content": response})

                

else:
    # Landing State
    st.info("👋 Welcome! Please upload an Excel or CSV file from the sidebar to begin analysis.")
    st.markdown("""
        ### Supported Columns (Auto-Detected):
        - **Campus**: Location, Branch, Center
        - **Instructor**: Faculty, Name, Trainer
        - **Subject**: Course, Module, Topic
        - **Status**: Progress, State, Remarks (Done/Pending)
    """)
