import streamlit as st
import pandas as pd
from groq import Groq
import plotly.express as px
from fpdf import FPDF
import os
from datetime import datetime

st.set_page_config(
    page_title="AI Business Report Generator",
    page_icon="📊",
    layout="wide"
)

st.title("🤖 AI Business Report Generator")

# SIDEBAR - UPLOAD & API KEY
with st.sidebar:
    st.header("📤 Upload Data")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    st.divider()
    
    st.header("🔑 API Configuration")
    api_key = st.text_input("Enter your Groq API key", type="password")

# MAIN AREA
if uploaded_file is not None and api_key:
    df = pd.read_csv(uploaded_file)
    st.success("✅ File uploaded successfully!")
    
    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["Data Overview", "Analysis", "Recommendations", "Download Report"])
    
    with tab1:
        st.subheader("Dataset Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="Rows", value=len(df))
        with col2:
            st.metric(label="Columns", value=len(df.columns))
        with col3:
            st.metric(label="Missing Values", value=df.isnull().sum().sum())
        
        st.subheader("Data Preview")
        st.dataframe(df, use_container_width=True)
        
        st.subheader("Column Information")
        col_info = pd.DataFrame({
            'Column': df.columns,
            'Type': df.dtypes.values,
            'Missing': df.isnull().sum().values
        })
        st.dataframe(col_info, use_container_width=True)
    
    with tab2:
        st.subheader("Statistical Summary")
        st.dataframe(df.describe(), use_container_width=True)
        
        st.subheader("📊 Visualizations")
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        # BAR CHART - TOP 10 ONLY
        if categorical_cols and numeric_cols:
            st.subheader("Bar Chart (Top 10)")
            df_top = df.nlargest(10, numeric_cols[0])
            fig_bar = px.bar(df_top, x=categorical_cols[0], y=numeric_cols[0], title=f"Top 10: {categorical_cols[0]}")
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # LINE CHART - GROUPED BY MONTH
        if 'Date' in df.columns and numeric_cols:
            st.subheader("Line Chart (By Month)")
            df_copy = df.copy()
            df_copy['Date'] = pd.to_datetime(df_copy['Date'])
            df_copy['YearMonth'] = df_copy['Date'].dt.strftime('%Y-%m')
            df_monthly = df_copy.groupby('YearMonth')[numeric_cols[0]].sum().reset_index()
            fig_line = px.line(df_monthly, x='YearMonth', y=numeric_cols[0], title=f"Monthly Trend")
            st.plotly_chart(fig_line, use_container_width=True)
        
        # PIE CHART - TOP 5 ONLY
        if categorical_cols:
            st.subheader("Pie Chart (Top 5)")
            df_top5 = df.nlargest(5, numeric_cols[0]) if numeric_cols else df.head(5)
            fig_pie = px.pie(df_top5, names=categorical_cols[0], title=f"Top 5: {categorical_cols[0]}")
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab3:
        st.subheader("📋 AI-Generated Recommendations")
        
        if st.button("Generate AI Insights"):
            with st.spinner("🤖 Analyzing data..."):
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                
                analysis = {
                    "Total Rows": len(df),
                    "Total Columns": len(df.columns),
                    "Missing Values": df.isnull().sum().sum()
                }
                
                if numeric_cols:
                    for col in numeric_cols:
                        analysis[f"{col} - Mean"] = round(df[col].mean(), 2)
                        analysis[f"{col} - Max"] = round(df[col].max(), 2)
                        analysis[f"{col} - Min"] = round(df[col].min(), 2)
                
                metrics_text = "\n".join([f"- {k}: {v}" for k, v in analysis.items()])
                
                data_description = f"""
                Dataset Metrics:
                {metrics_text}
                
                Sample data (first 3 rows):
                {df.head(3).to_string()}
                """
                
                client = Groq(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Analyze this business dataset and provide: 1. Business domain 2. Key insights 3. Top 3 recommendations. {data_description}"
                        }
                    ]
                )
                
                ai_response = response.choices[0].message.content
                st.session_state.ai_response = ai_response
                st.session_state.analysis = analysis
                st.write(ai_response)
    
    with tab4:
        st.subheader("📥 Download Your Report")
        
        if st.button("Generate PDF Report"):
            with st.spinner("📄 Creating PDF..."):
                pdf = FPDF()
                pdf.add_page()
                
                pdf.set_font("Arial", "B", 20)
                pdf.cell(0, 10, "Business Report", ln=True, align="C")
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
                pdf.ln(5)
                
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "Dataset Overview", ln=True)
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, f"Rows: {len(df)}", ln=True)
                pdf.cell(0, 10, f"Columns: {len(df.columns)}", ln=True)
                pdf.cell(0, 10, f"Missing Values: {df.isnull().sum().sum()}", ln=True)
                pdf.ln(5)
                
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "Column Information", ln=True)
                
                pdf.set_font("Arial", "", 9)
                for col in df.columns:
                    pdf.cell(0, 8, f"{col}: {df[col].dtype}", ln=True)
                pdf.ln(5)
                
                if 'analysis' in st.session_state:
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, "Analysis Metrics", ln=True)
                    
                    pdf.set_font("Arial", "", 9)
                    for key, value in st.session_state.analysis.items():
                        pdf.cell(0, 8, f"{key}: {value}", ln=True)
                    pdf.ln(5)
                
                if 'ai_response' in st.session_state:
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, "AI Analysis", ln=True)
                    
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 5, st.session_state.ai_response)
                
                pdf_path = "report.pdf"
                pdf.output(pdf_path)
                
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_file,
                        file_name=f"business_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
                
                st.success("✅ PDF created successfully!")

elif uploaded_file is not None and not api_key:
    st.warning("⚠️ Please enter your Groq API key in the sidebar")

else:
    st.info("👈 Upload a CSV file and enter API key in the sidebar to get started")