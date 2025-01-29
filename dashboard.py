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
        st.write("Available columns:", list(df.columns))  # Debug line to show columns
        st.session_state.prediction_data = df
        
    df = load_data()
    
    if len(df) > 0:
        # Key Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_bets = len(df)
            st.metric("Total Predictions", total_bets)
        with col2:
            if 'Hit Rate: Season' in df.columns:
                avg_season = df['Hit Rate: Season'].mean()
                st.metric("Season Hit Rate", f"{avg_season:.1f}%")
        with col3:
            if 'Hit Rate: Last 5' in df.columns:
                avg_recent = df['Hit Rate: Last 5'].mean()
                st.metric("Recent Hit Rate", f"{avg_recent:.1f}%")
        with col4:
            if 'Weighted Hit Rate' in df.columns:
                avg_weighted = df['Weighted Hit Rate'].mean()
                st.metric("Weighted Hit Rate", f"{avg_weighted:.1f}%")

        # Market Analysis
        st.header("Market Analysis")
        if 'Market Name' in df.columns:
            market_counts = df['Market Name'].value_counts()
            fig1 = px.bar(market_counts, title="Predictions by Market Type")
            st.plotly_chart(fig1)
        
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
