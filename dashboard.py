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

def initialize_database():
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY,
            date TEXT,
            player TEXT,
            market TEXT,
            line REAL,
            prediction TEXT,
            result TEXT DEFAULT 'Pending',
            hit_rate REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_prediction(prediction):
    conn = sqlite3.connect('predictions.db')
    data = pd.DataFrame({
        'date': [prediction['Date']],
        'player': [prediction['Player']],
        'market': [prediction['Market Name']],
        'line': [prediction['Line']],
        'prediction': ['Over'],
        'result': ['Pending'],
        'hit_rate': [prediction['Weighted Hit Rate']]
    })
    data.to_sql('predictions', conn, if_exists='append', index=False)
    conn.close()

def load_results():
    conn = sqlite3.connect('predictions.db')
    results = pd.read_sql('SELECT * FROM predictions', conn)
    conn.close()
    return results

def update_result(prediction_id, result):
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE predictions SET result = ? WHERE id = ?",
        (result, prediction_id)
    )
    conn.commit()
    conn.close()

def filter_todays_best_bets(df):
    today = datetime.now().strftime('%Y-%m-%d')
    return df[
        (df['Date'] == today) &
        (df['Weighted Hit Rate'] > 60) &
        (df['Hit Rate: Last 5'] > 50)
    ].sort_values('Weighted Hit Rate', ascending=False)

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

def create_dashboard():
    st.title('🏀 NBA Props Prediction Dashboard')
    initialize_database()
    
    # Create radio buttons instead of tabs for guaranteed visibility
    page = st.radio("Navigation", ["Today's Best Bets", "Results Tracking", "Analysis"], horizontal=True)
    
    # File uploader moved outside navigation
    uploaded_file = st.file_uploader("Upload your predictions CSV", type=['csv'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state.prediction_data = df
    
    if page == "Today's Best Bets":
        if 'prediction_data' in st.session_state:
            df = st.session_state.prediction_data
            best_bets = filter_todays_best_bets(df)
            st.header("🎯 Today's Best Bets")
            if len(best_bets) > 0:
                for idx, bet in best_bets.iterrows():
                    with st.expander(f"{bet['Player']} - {bet['Market Name']}"):
                        col1, col2, col3 = st.columns([2,1,1])
                        with col1:
                            st.write(f"Line: {bet['Line']}")
                            st.write(f"Weighted Hit Rate: {bet['Weighted Hit Rate']:.1f}%")
                        with col2:
                            st.write(f"Last 5: {bet['Hit Rate: Last 5']}%")
                            st.write(f"Season: {bet['Hit Rate: Season']}%")
                        with col3:
                            if st.button("Track Bet", key=f"track_{idx}"):
                                save_prediction(bet)
                                st.success("Bet tracked!")
    elif page == "Results Tracking":
        st.header("Results Tracking")
        results = load_results()
        if len(results) > 0:
            st.write("Track your prediction outcomes:")
            for idx, pred in results.iterrows():
                col1, col2, col3 = st.columns([2,1,1])
                with col1:
                    st.write(f"{pred['Player']} - {pred['Market Name']}")
                with col2:
                    st.write(f"Line: {pred['Line']}")
                with col3:
                    result = st.selectbox(
                        "Result",
                        ["Pending", "Hit", "Miss"],
                        key=f"result_{idx}"
                    )
                    if result != "Pending":
                        update_result(idx, result)
            
            hits = len(results[results['result'] == 'Hit'])
            total = len(results[results['result'] != 'Pending'])
            if total > 0:
                win_rate = (hits / total) * 100
                st.metric("Win Rate", f"{win_rate:.1f}%")
    else:
        if 'prediction_data' in st.session_state:
            df = st.session_state.prediction_data
            col1, col2, col3, col4 = st.columns(4)
            metrics_display(df, col1, col2, col3, col4)
            market_analysis(df)
            player_performance(df)
            hit_rate_distribution(df)
            trend_analysis(df)
        else:
            st.info("Upload a predictions CSV file to view analytics")

if __name__ == "__main__":
    create_dashboard()
