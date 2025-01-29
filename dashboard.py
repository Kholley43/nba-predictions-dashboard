import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def load_data():
    if 'prediction_data' not in st.session_state:
        st.session_state.prediction_data = pd.DataFrame()
    return st.session_state.prediction_data

def create_dashboard():
    st.title('🏀 NBA Props Prediction Dashboard')
    
    # File uploader
    uploaded_file = st.file_uploader("Upload your predictions CSV", type=['csv'])
    if uploaded_file is not None:
        st.session_state.prediction_data = pd.read_csv(uploaded_file)
        
    df = load_data()
    
    if len(df) > 0:
        # Key Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            accuracy = (df['Result'].mean() * 100) if 'Result' in df else 0
            st.metric("Overall Accuracy", f"{accuracy:.1f}%")
        with col2:
            total_bets = len(df)
            st.metric("Total Predictions", total_bets)
        with col3:
            roi = ((df['Result'].sum() * 100) / len(df)) - 100 if 'Result' in df else 0
            st.metric("ROI", f"{roi:.1f}%")
        
        # Performance by Market
        st.header("Market Performance")
        if 'Market' in df:
            market_perf = df.groupby('Market')['Result'].agg(['count', 'mean'])
            fig = px.bar(market_perf, y='mean', title="Win Rate by Market Type")
            st.plotly_chart(fig)
        
        # Confidence Analysis
        st.header("Confidence Score Analysis")
        if 'Confidence' in df and 'Result' in df:
            fig2 = px.scatter(df, x='Confidence', y='Result', 
                         trendline="lowess", title="Confidence vs Actual Results")
            st.plotly_chart(fig2)
        
        # Recent Predictions
        st.header("Today's Predictions")
        today = datetime.now().strftime('%Y-%m-%d')
        if 'Date' in df:
            today_preds = df[df['Date'] == today]
            st.table(today_preds[['Player', 'Market', 'Line', 'Prediction', 'Confidence']])
    else:
        st.info("Upload a predictions CSV file to view analytics")

if __name__ == "__main__":
    create_dashboard()
