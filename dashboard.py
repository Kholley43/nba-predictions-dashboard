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
        df = pd.read_csv(uploaded_file)
        st.session_state.prediction_data = df
        
        # Display data overview
        st.header("Data Overview")
        st.dataframe(df.head())
    
    df = load_data()
    
    if len(df) > 0:
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            accuracy = (df['Result'].mean() * 100) if 'Result' in df else 0
            st.metric("Overall Accuracy", f"{accuracy:.1f}%")
        with col2:
            total_bets = len(df)
            st.metric("Total Predictions", total_bets)
        with col3:
            roi = ((df['Result'].sum() * 100) / len(df)) - 100 if 'Result' in df else 0
            st.metric("ROI", f"{roi:.1f}%")
        with col4:
            if 'Hit Rate: Season' in df.columns:
                avg_hit_rate = df['Hit Rate: Season'].mean()
                st.metric("Season Hit Rate", f"{avg_hit_rate:.1f}%")

        # Market Analysis
        st.header("Market Analysis")
        if 'Market Name' in df.columns:
            market_counts = df['Market Name'].value_counts()
            fig1 = px.bar(market_counts, title="Predictions by Market Type")
            st.plotly_chart(fig1)
        
        # Performance by Market
        if 'Market' in df:
            market_perf = df.groupby('Market')['Result'].agg(['count', 'mean'])
            fig2 = px.bar(market_perf, y='mean', title="Win Rate by Market Type")
            st.plotly_chart(fig2)
        
        # Confidence Analysis
        st.header("Confidence Analysis")
        col1, col2 = st.columns(2)
        with col1:
            if 'Confidence' in df and 'Result' in df:
                fig3 = px.scatter(df, x='Confidence', y='Result',
                             trendline="lowess", title="Confidence vs Results")
                st.plotly_chart(fig3)
        with col2:
            if 'Weighted Hit Rate' in df.columns:
                fig4 = px.histogram(df, x='Weighted Hit Rate',
                                title="Distribution of Hit Rates")
                st.plotly_chart(fig4)
        
        # Recent Predictions
        st.header("Today's Predictions")
        today = datetime.now().strftime('%Y-%m-%d')
        if 'Date' in df:
            today_preds = df[df['Date'] == today]
            display_columns = ['Player', 'Market Name', 'Line', 'Hit Rate: Season', 'Weighted Hit Rate']
            st.table(today_preds[display_columns])
    else:
        st.info("Upload a predictions CSV file to view analytics")

if __name__ == "__main__":
    create_dashboard()
