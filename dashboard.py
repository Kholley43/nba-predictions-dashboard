import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
import requests

def load_data():
    if 'prediction_data' not in st.session_state:
        st.session_state.prediction_data = pd.DataFrame()
    return st.session_state.prediction_data

def filter_best_predictions(df):
    return df[
        (df['Weighted Hit Rate'] > 55) &
        (df['Hit Rate: Last 5'] > 40) &
        (df['Hit Rate: Season'] > 45)
    ].sort_values('Weighted Hit Rate', ascending=False)

def save_prediction(prediction):
    conn = sqlite3.connect('predictions.db')
    prediction.to_sql('predictions', conn, if_exists='append', index=False)
    conn.close()

def load_results():
    conn = sqlite3.connect('predictions.db')
    results = pd.read_sql('SELECT * FROM predictions', conn)
    conn.close()
    return results

def create_dashboard():
    st.title('🏀 NBA Props Prediction Dashboard')
    
    tabs = st.tabs(["Predictions", "Results Tracking", "Analysis"])
    
    with tabs[0]:
        uploaded_file = st.file_uploader("Upload your predictions CSV", type=['csv'])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.session_state.prediction_data = df
            
            # Filter best predictions
            best_predictions = filter_best_predictions(df)
            st.header("🎯 Top Predictions")
            st.dataframe(best_predictions[['Player', 'Market Name', 'Line', 'Weighted Hit Rate', 'Hit Rate: Last 5']])
            
            # Save predictions
            if st.button("Save Predictions"):
                save_prediction(best_predictions)
                st.success("Predictions saved!")
    
    with tabs[1]:
        st.header("Results Tracking")
        results = load_results()
        if len(results) > 0:
            # Add result input
            for idx, pred in results.iterrows():
                col1, col2, col3 = st.columns([2,1,1])
                with col1:
                    st.write(f"{pred['Player']} - {pred['Market Name']}")
                with col2:
                    st.write(f"Line: {pred['Line']}")
                with col3:
                    result = st.selectbox("Result", ["Pending", "Hit", "Miss"], key=f"result_{idx}")
                    if result != "Pending":
                        update_result(idx, result)
    
    with tabs[2]:
        df = load_data()
        if len(df) > 0:
            # Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            metrics_display(df, col1, col2, col3, col4)
            
            # Market Analysis
            market_analysis(df)
            
            # Player Performance
            player_performance(df)
            
            # Hit Rate Distribution
            hit_rate_distribution(df)
            
            # Recent Predictions
            recent_predictions(df)
            
            # Trend Analysis
            trend_analysis(df)
        else:
            st.info("Upload a predictions CSV file to view analytics")

def metrics_display(df, col1, col2, col3, col4):
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

def market_analysis(df):
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

def player_performance(df):
    st.header("Player Performance")
    if 'Player' in df.columns:
        top_players = df.groupby('Player')['Weighted Hit Rate'].mean().sort_values(ascending=False).head(10)
        fig3 = px.bar(top_players, title="Top 10 Players by Hit Rate")
        st.plotly_chart(fig3)

def hit_rate_distribution(df):
    st.header("Hit Rate Distribution")
    col1, col2 = st.columns(2)
    with col1:
        fig4 = px.histogram(df, x='Weighted Hit Rate', title="Distribution of Hit Rates")
        st.plotly_chart(fig4)
    with col2:
        fig5 = px.box(df, x='Market Name', y='Weighted Hit Rate', title="Hit Rate Ranges by Market")
        st.plotly_chart(fig5)

def recent_predictions(df):
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

def trend_analysis(df):
    st.header("Historical Trends")
    if 'Hit Rate: Last 20 Outcomes' in df.columns:
        selected_player = st.selectbox("Select Player", df['Player'].unique())
        player_data = df[df['Player'] == selected_player]
        
        outcomes_str = str(player_data['Hit Rate: Last 20 Outcomes'].iloc[0])
        outcomes_list = [int(x) for x in outcomes_str if x in '01']
        
        trend_data = pd.DataFrame({
            'Game': range(1, len(outcomes_list) + 1),
            'Hit Rate': outcomes_list
        })
        
        fig6 = px.line(trend_data, x='Game', y='Hit Rate',
                       title=f"{selected_player}'s Last {len(outcomes_list)} Games")
        fig6.update_traces(mode='lines+markers')
        st.plotly_chart(fig6)

if __name__ == "__main__":
    create_dashboard()

def update_result(prediction_id, result):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE predictions SET result = ? WHERE id = ?", 
        (result, prediction_id)
    )
    conn.commit()
    conn.close()
