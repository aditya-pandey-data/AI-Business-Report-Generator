import streamlit as st
import pandas as pd
import numpy as np
from groq import Groq
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import sqlite3
import os

st.set_page_config(
    page_title="AI Business Report Generator",
    page_icon="📊",
    layout="wide"
)

st.title("🤖 AI Business Report Generator with Advanced SQL")

# SIDEBAR - UPLOAD & API KEY
with st.sidebar:
    st.header("📤 Data Source")
    
    data_source = st.radio("Choose data source:", ["Upload CSV", "Connect to Database"])
    
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        db_connection = None
    else:
        st.subheader("Database Connection")
        db_type = st.selectbox("Database Type:", ["SQLite (Local)", "PostgreSQL", "MySQL"])
        
        if db_type == "SQLite (Local)":
            db_file = st.text_input("SQLite file path (e.g., data.db):")
            if db_file and os.path.exists(db_file):
                try:
                    db_connection = sqlite3.connect(db_file)
                    st.success("✅ Connected to SQLite")
                except:
                    st.error("❌ Could not connect to database")
                    db_connection = None
            else:
                db_connection = None
        else:
            st.warning("Enter connection details for PostgreSQL/MySQL (optional)")
            db_connection = None
        
        uploaded_file = None
    
    st.divider()
    
    st.header("🔑 API Configuration")
    api_key = st.text_input("Enter your Groq API key", type="password")

# ==================== MAIN LOGIC ====================

has_data = False
df = None
db_connection = None

if data_source == "Upload CSV" and uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    has_data = True
elif data_source == "Connect to Database":
    if db_connection is not None:
        has_data = True

if has_data and api_key:
    
    # Create database for CSV (if needed)
    if df is not None and db_connection is None:
        db_connection = sqlite3.connect(":memory:")
        df.to_sql("data", db_connection, if_exists="replace", index=False)
        st.success("✅ CSV loaded into SQLite")
    
    if df is None and db_connection is not None:
        df = pd.read_sql("SELECT * FROM data LIMIT 1000", db_connection)
    
    st.success("✅ Data loaded successfully!")
    
    # AUTO-DETECT DATA STRUCTURE
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    # Check for date columns
    has_date = False
    date_col = None
    for col in categorical_cols:
        try:
            pd.to_datetime(df[col])
            has_date = True
            date_col = col
            break
        except:
            pass
    
    if 'Date' in df.columns:
        has_date = True
        date_col = 'Date'
    
    has_numeric = len(numeric_cols) > 0
    has_categorical = len(categorical_cols) > 0
    
    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Data Quality", 
        "SQL Analysis", 
        "Statistical Analysis",
        "Visualizations", 
        "AI Insights", 
        "Download Report"
    ])
    
    # ==================== TAB 1: DATA QUALITY ====================
    with tab1:
        st.subheader("📋 Data Quality Assessment")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Total Columns", len(df.columns))
        with col3:
            st.metric("Missing Values", df.isnull().sum().sum())
        with col4:
            st.metric("Duplicate Rows", df.duplicated().sum())
        
        st.divider()
        
        st.subheader("Column Information")
        col_info = pd.DataFrame({
            'Column': df.columns,
            'Data Type': df.dtypes.values,
            'Missing Count': df.isnull().sum().values,
            'Missing %': (df.isnull().sum().values / len(df) * 100).round(2),
            'Unique Values': [df[col].nunique() for col in df.columns]
        })
        st.dataframe(col_info, use_container_width=True)
        
        st.divider()
        
        st.subheader("🔍 Quality Checks")
        quality_issues = []
        
        high_missing = col_info[col_info['Missing %'] > 50]
        if len(high_missing) > 0:
            quality_issues.append(
                f"⚠️ **{len(high_missing)} columns have >50% missing values**: {', '.join(high_missing['Column'].tolist())}"
            )
        
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            quality_issues.append(f"⚠️ **{duplicates} duplicate rows found**")
        
        for col in numeric_cols:
            if (df[col] < 0).sum() > 0 and col.lower() not in ['change', 'variance', 'delta']:
                quality_issues.append(f"⚠️ **Column '{col}' has negative values**")
        
        # IMPROVED OUTLIER DETECTION using IQR method
        outlier_rows = set()
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outlier_indices = df[(df[col] < lower_bound) | (df[col] > upper_bound)].index
            outlier_rows.update(outlier_indices)
        
        if len(outlier_rows) > 0:
            outlier_percentage = (len(outlier_rows) / len(df) * 100)
            quality_issues.append(
                f"📊 **{len(outlier_rows)} rows ({outlier_percentage:.1f}%) have outliers** detected using IQR method"
            )
        
        if len(quality_issues) == 0:
            st.success("✅ Data quality looks good!")
        else:
            for issue in quality_issues:
                st.info(issue)
        
        st.divider()
        st.subheader("Data Preview")
        st.dataframe(df.head(10), use_container_width=True)
    
    # ==================== TAB 2: SQL ANALYSIS (SMART) ====================
    with tab2:
        st.subheader("🔍 Advanced SQL Analysis")
        
        st.write("**SQL Queries automatically generated based on your data structure:**")
        
        st.divider()
        
        # SHOW AVAILABLE QUERIES
        st.subheader("📊 Available Queries")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if has_numeric and has_categorical:
                st.success("✅ Query 1: Ranking")
            else:
                st.error("❌ Query 1 requires numeric + categorical")
        
        with col2:
            if has_numeric:
                st.success("✅ Query 2: Segmentation")
            else:
                st.error("❌ Query 2 requires numeric")
        
        with col3:
            if has_date and has_numeric:
                st.success("✅ Query 3: Trends")
            else:
                if not has_date:
                    st.warning("⚠️ Query 3 needs Date")
                if not has_numeric:
                    st.warning("⚠️ Query 3 needs numeric")
        
        st.divider()
        
        # QUERY 1: ROW_NUMBER (instead of RANK)
        if has_numeric and has_categorical:
            st.subheader("Query 1: Ranking Analysis (ROW_NUMBER)")
            
            sql_query1 = f"""
            SELECT 
                "{categorical_cols[0]}",
                SUM(CAST("{numeric_cols[0]}" AS FLOAT)) as total_value,
                AVG(CAST("{numeric_cols[0]}" AS FLOAT)) as avg_value,
                COUNT(*) as count,
                ROW_NUMBER() OVER (ORDER BY SUM(CAST("{numeric_cols[0]}" AS FLOAT)) DESC) as rank,
                ROUND(100.0 * SUM(CAST("{numeric_cols[0]}" AS FLOAT)) / 
                    (SELECT SUM(CAST("{numeric_cols[0]}" AS FLOAT)) FROM data), 2) as percentage_of_total
            FROM data
            GROUP BY "{categorical_cols[0]}"
            ORDER BY total_value DESC
            LIMIT 10
            """
            
            st.write("**SQL Query:**")
            st.code(sql_query1, language="sql")
            
            try:
                result1 = pd.read_sql(sql_query1, db_connection)
                st.write("**Results:**")
                st.dataframe(result1, use_container_width=True)
                st.session_state.sql_result1 = result1
                
                st.success("✅ Top categories ranked without gaps (using ROW_NUMBER)")
            except Exception as e:
                st.error(f"❌ Query error: {str(e)}")
        
        else:
            st.info("⚠️ **Query 1 Not Available**")
            st.write(f"Needs: Numeric ({has_numeric}) + Categorical ({has_categorical})")
        
        st.divider()
        
        # QUERY 2: SEGMENTATION
        if has_numeric:
            st.subheader("Query 2: Customer Segmentation (CTE)")
            
            sql_query2 = f"""
            WITH stats AS (
                SELECT 
                    AVG(CAST("{numeric_cols[0]}" AS FLOAT)) as avg_value,
                    MIN(CAST("{numeric_cols[0]}" AS FLOAT)) as min_value,
                    MAX(CAST("{numeric_cols[0]}" AS FLOAT)) as max_value
                FROM data
            ),
            segmentation AS (
                SELECT 
                    *,
                    CASE 
                        WHEN CAST("{numeric_cols[0]}" AS FLOAT) >= (SELECT avg_value FROM stats) 
                        THEN 'High Performer'
                        ELSE 'Lower Performer'
                    END as segment
                FROM data
            )
            SELECT 
                segment,
                COUNT(*) as count,
                ROUND(AVG(CAST("{numeric_cols[0]}" AS FLOAT)), 2) as avg_value,
                ROUND(MIN(CAST("{numeric_cols[0]}" AS FLOAT)), 2) as min_value,
                ROUND(MAX(CAST("{numeric_cols[0]}" AS FLOAT)), 2) as max_value,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM data), 2) as percentage
            FROM segmentation
            GROUP BY segment
            ORDER BY avg_value DESC
            """
            
            st.write("**SQL Query:**")
            st.code(sql_query2, language="sql")
            
            try:
                result2 = pd.read_sql(sql_query2, db_connection)
                st.write("**Results:**")
                st.dataframe(result2, use_container_width=True)
                st.session_state.sql_result2 = result2
                
                st.success("✅ Data segmented into High vs Low performers")
            except Exception as e:
                st.error(f"❌ Query error: {str(e)}")
        
        else:
            st.info("⚠️ **Query 2 Not Available** - Requires numeric columns")
        
        st.divider()
        
        # QUERY 3: TREND ANALYSIS
        if has_date and has_numeric:
            st.subheader("Query 3: Trend Analysis (LAG)")
            
            sql_query3 = f"""
            SELECT 
                "{date_col}",
                CAST("{numeric_cols[0]}" AS FLOAT) as current_value,
                LAG(CAST("{numeric_cols[0]}" AS FLOAT)) OVER (ORDER BY "{date_col}") as previous_value,
                ROUND(CAST("{numeric_cols[0]}" AS FLOAT) - 
                      LAG(CAST("{numeric_cols[0]}" AS FLOAT)) OVER (ORDER BY "{date_col}"), 2) as change,
                ROUND((CAST("{numeric_cols[0]}" AS FLOAT) - 
                      LAG(CAST("{numeric_cols[0]}" AS FLOAT)) OVER (ORDER BY "{date_col}")) 
                      / LAG(CAST("{numeric_cols[0]}" AS FLOAT)) OVER (ORDER BY "{date_col}") * 100, 2) as pct_change
            FROM data
            ORDER BY "{date_col}"
            LIMIT 20
            """
            
            st.write("**SQL Query:**")
            st.code(sql_query3, language="sql")
            
            try:
                result3 = pd.read_sql(sql_query3, db_connection)
                st.write("**Results:**")
                st.dataframe(result3, use_container_width=True)
                st.session_state.sql_result3 = result3
                
                st.success("✅ Trend analysis with period-over-period changes")
            except Exception as e:
                st.error(f"❌ Query error: {str(e)}")
        
        else:
            st.info("⚠️ **Query 3 Not Available**")
            st.write(f"Needs: Date ({has_date}) + Numeric ({has_numeric})")
    
    # ==================== TAB 3: STATISTICAL ANALYSIS ====================
    with tab3:
        st.subheader("📊 Statistical Summary")
        
        if numeric_cols:
            st.subheader("Numeric Column Statistics")
            stats_df = df[numeric_cols].describe().T
            stats_df['CV'] = (df[numeric_cols].std() / df[numeric_cols].mean() * 100).round(2)
            st.dataframe(stats_df, use_container_width=True)
            
            st.divider()
            
            st.subheader("Correlation Analysis")
            
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                
                strong_corr = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_value = corr_matrix.iloc[i, j]
                        if abs(corr_value) > 0.7:
                            strong_corr.append({
                                'Column 1': corr_matrix.columns[i],
                                'Column 2': corr_matrix.columns[j],
                                'Correlation': round(corr_value, 3)
                            })
                
                if strong_corr:
                    st.info(f"🔗 Found {len(strong_corr)} strong correlation(s):")
                    for corr in strong_corr:
                        st.write(f"- **{corr['Column 1']}** ↔ **{corr['Column 2']}**: {corr['Correlation']}")
                
                fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", title="Correlation Matrix")
                st.plotly_chart(fig, use_container_width=True)
        
        if categorical_cols:
            st.divider()
            st.subheader("Categorical Column Analysis")
            
            for col in categorical_cols[:3]:
                st.write(f"**{col}** - Top 10 Values:")
                col_counts = df[col].value_counts().head(10)
                fig = px.bar(x=col_counts.index, y=col_counts.values, labels={'x': col, 'y': 'Count'})
                st.plotly_chart(fig, use_container_width=True)
    
    # ==================== TAB 4: VISUALIZATIONS ====================
    with tab4:
        st.subheader("📈 Data Visualizations")
        
        if categorical_cols and numeric_cols:
            st.subheader("Bar Chart (Top 10)")
            df_top = df.nlargest(10, numeric_cols[0])
            fig_bar = px.bar(
                df_top, 
                x=categorical_cols[0], 
                y=numeric_cols[0],
                title=f"Top 10: {categorical_cols[0]}"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        if has_date and numeric_cols:
            st.subheader("Line Chart (Trend)")
            try:
                df_copy = df.copy()
                df_copy[date_col] = pd.to_datetime(df_copy[date_col])
                df_copy['YearMonth'] = df_copy[date_col].dt.strftime('%Y-%m')
                df_monthly = df_copy.groupby('YearMonth')[numeric_cols[0]].sum().reset_index()
                
                fig_line = px.line(
                    df_monthly, 
                    x='YearMonth', 
                    y=numeric_cols[0],
                    title="Monthly Trend",
                    markers=True
                )
                st.plotly_chart(fig_line, use_container_width=True)
            except:
                st.warning("Could not parse date column for trend")
        
        if categorical_cols and numeric_cols:
            st.subheader("Pie Chart (Top 5)")
            df_top5 = df.nlargest(5, numeric_cols[0])
            fig_pie = px.pie(
                df_top5, 
                names=categorical_cols[0],
                values=numeric_cols[0],
                title="Top 5 Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # ==================== TAB 5: AI INSIGHTS ====================
    with tab5:
        st.subheader("🤖 AI-Generated Business Insights")
        
        if st.button("Generate AI Insights"):
            with st.spinner("🤖 Analyzing data with SQL + AI..."):
                
                analysis = {
                    "Total Rows": len(df),
                    "Total Columns": len(df.columns),
                    "Missing Values": df.isnull().sum().sum(),
                    "Duplicate Rows": df.duplicated().sum()
                }
                
                if numeric_cols:
                    for col in numeric_cols[:5]:
                        analysis[f"{col} - Total"] = round(df[col].sum(), 2)
                        analysis[f"{col} - Average"] = round(df[col].mean(), 2)
                        analysis[f"{col} - Median"] = round(df[col].median(), 2)
                        analysis[f"{col} - Std Dev"] = round(df[col].std(), 2)
                
                metrics_text = "\n".join([f"- {k}: {v}" for k, v in analysis.items()])
                
                data_description = f"""
                Dataset Metrics:
                {metrics_text}
                
                Sample data (first 5 rows):
                {df.head(5).to_string()}
                
                Column names and types: {list(df.dtypes.items())}
                """
                
                client = Groq(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": f"""Analyze this business dataset and provide:
1. Business Domain: What type of business/data is this?
2. Key Findings: 3-4 most important observations
3. Business Risks: 2-3 potential problems or concerns
4. Recommendations: 3-4 specific, actionable next steps

Dataset:
{data_description}"""
                        }
                    ]
                )
                
                ai_response = response.choices[0].message.content
                st.session_state.ai_response = ai_response
                st.session_state.analysis = analysis
                
                st.write(ai_response)
    
    # ==================== TAB 6: DOWNLOAD REPORT ====================
    with tab6:
        st.subheader("📥 Download Your Report")
        
        if st.button("Generate PDF Report"):
            with st.spinner("📄 Creating PDF..."):
                pdf = FPDF()
                pdf.add_page()
                
                pdf.set_font("Arial", "B", 20)
                pdf.cell(0, 15, "Business Analytics Report", ln=True, align="C")
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
                pdf.ln(5)
                
                # DATASET OVERVIEW
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "1. Dataset Overview", ln=True)
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, f"Total Rows: {len(df)}", ln=True)
                pdf.cell(0, 8, f"Total Columns: {len(df.columns)}", ln=True)
                pdf.cell(0, 8, f"Missing Values: {df.isnull().sum().sum()}", ln=True)
                pdf.ln(5)
                
                # COLUMN INFORMATION
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "2. Column Information", ln=True)
                
                pdf.set_font("Arial", "", 9)
                for col in df.columns[:15]:
                    pdf.cell(0, 7, f"- {col}: {df[col].dtype}", ln=True)
                pdf.ln(3)
                
                # SQL ANALYSIS
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "3. SQL Analysis Results", ln=True)
                
                pdf.set_font("Arial", "", 9)
                
                if 'sql_result1' in st.session_state:
                    pdf.cell(0, 8, "Query 1 - Top Categories (by Rank):", ln=True)
                    result = st.session_state.sql_result1.head(5)
                    for idx, row in result.iterrows():
                        pdf.cell(0, 6, f"- Rank {int(row.iloc[4])}: {row.iloc[0]} ({row.iloc[5]}%)", ln=True)
                
                if 'sql_result2' in st.session_state:
                    pdf.cell(0, 8, "Query 2 - Segmentation:", ln=True)
                    result = st.session_state.sql_result2
                    for idx, row in result.iterrows():
                        pdf.cell(0, 6, f"- {row.iloc[0]}: Avg={row.iloc[2]}, Count={row.iloc[1]}", ln=True)
                
                pdf.ln(3)
                
                # STATISTICAL METRICS
                if 'analysis' in st.session_state:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, "4. Statistical Metrics", ln=True)
                    
                    pdf.set_font("Arial", "", 9)
                    for key, value in list(st.session_state.analysis.items())[:20]:
                        pdf.cell(0, 6, f"- {key}: {value}", ln=True)
                    pdf.ln(3)
                
                # AI INSIGHTS
                if 'ai_response' in st.session_state:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, "5. AI Analysis & Recommendations", ln=True)
                    
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 5, st.session_state.ai_response)
                
                pdf_path = "report.pdf"
                pdf.output(pdf_path)
                
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_file,
                        file_name=f"business_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
                
                st.success("✅ PDF created successfully!")

elif not api_key:
    st.warning("⚠️ Please enter your Groq API key in the sidebar")

else:
    st.info("👈 Upload a CSV or connect to database + enter API key in sidebar")