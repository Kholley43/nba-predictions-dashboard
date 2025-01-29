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
        st.write("Available columns:", list(df.columns))
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
            col1, col2 = st.columns(2)
            with col1:
                market_counts = df['Market Name'].value_counts()
                fig1 = px.bar(market_counts, title="Predictions by Market Type")
                st.plotly_chart(fig1)
            with col2:
                market_hit_rates = df.groupby('Market Name')['Weighted Hit Rate'].mean()
                fig2 = px.bar(market_hit_rates, title="Hit Rates by Market Type")
                st.plotly_chart(fig2)

        # Player Performance
        st.header("Player Performance")
        if 'Player' in df.columns:
            top_players = df.groupby('Player')['Weighted Hit Rate'].mean().sort_values(ascending=False).head(10)
            fig3 = px.bar(top_players, title="Top 10 Players by Hit Rate")
            st.plotly_chart(fig3)

        # Hit Rate Distribution
        st.header("Hit Rate Distribution")
        col1, col2 = st.columns(2)
        with col1:
            fig4 = px.histogram(df, x='Weighted Hit Rate', title="Distribution of Hit Rates")
            st.plotly_chart(fig4)
        with col2:
            fig5 = px.box(df, x='Market Name', y='Weighted Hit Rate', title="Hit Rate Ranges by Market")
            st.plotly_chart(fig5)

        # Recent Predictions
        st.header("Today's Predictions")
        today = datetime.now().strftime('%Y-%m-%d')
        if 'Date' in df:
            today_preds = df[df['Date'] == today]
            display_columns = [
                'Player', 'Market Name', 'Line', 
                'Hit Rate: Last 5', 'Hit Rate: Last 10',
                'Hit Rate: Season', 'Weighted Hit Rate'
            ]
            st.table(today_preds[display_columns])

        # Trend Analysis
        st.header("Historical Trends")
        if 'Hit Rate: Last 20 Outcomes' in df.columns:
            selected_player = st.selectbox("Select Player", df['Player'].unique())
            player_data = df[df['Player'] == selected_player]
            outcomes = player_data['Hit Rate: Last 20 Outcomes'].iloc[0]  # Get the first occurrence
            trend_data = pd.DataFrame({
                'Game': range(1, 21),
                'Hit Rate': [int(x) for x in outcomes]
            })
            fig6 = px.line(trend_data, x='Game', y='Hit Rate', title=f"{selected_player}'s Last 20 Games")
            st.plotly_chart(fig6)
    else:
        st.info("Upload a predictions CSV file to view analytics")

if __name__ == "__main__":
    create_dashboard()
