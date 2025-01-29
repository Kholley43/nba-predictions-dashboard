import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
import requests
from time import sleep
import threading

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

def get_espn_stats(player_name, market_type):
    """
    Fetches real-time NBA stats using ESPN API
    """
    base_url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba"
    
    try:
        # Get today's games and stats
        response = requests.get(f"{base_url}/scoreboard")
        games_data = response.json()
        
        for game in games_data['events']:
            for team in game['competitions'][0]['competitors']:
                for athlete in team.get('statistics', []):
                    if player_name.lower() in athlete['name'].lower():
                        stats = {
                            'Points': athlete.get('points', 0),
                            'Rebounds': athlete.get('rebounds', 0),
                            'Assists': athlete.get('assists', 0),
                            'PTS+REB': athlete.get('points', 0) + athlete.get('rebounds', 0),
                            'PTS+AST': athlete.get('points', 0) + athlete.get('assists', 0),
                            'REB+AST': athlete.get('rebounds', 0) + athlete.get('assists', 0),
                            'PTS+REB+AST': athlete.get('points', 0) + athlete.get('rebounds', 0) + athlete.get('assists', 0)
                        }
                        return stats.get(market_type, 0)
        return 0
    except Exception as e:
        st.sidebar.error(f"Stats Update Error: {e}")
        return 0

def process_player_stats(stats_data, market_type):
    """
    Processes raw ESPN stats data into usable metrics
    """
    stats_mapping = {
        'Points': 'points',
        'Rebounds': 'rebounds',
        'Assists': 'assists',
        'PTS+REB': lambda x: x['points'] + x['rebounds'],
        'PTS+AST': lambda x: x['points'] + x['assists'],
        'REB+AST': lambda x: x['rebounds'] + x['assists'],
        'PTS+REB+AST': lambda x: x['points'] + x['rebounds'] + x['assists'],
        'Steals': 'steals',
        'Blocks': 'blocks',
        'BLK+STL': lambda x: x['blocks'] + x['steals']
    }
    
    return stats_mapping[market_type](stats_data) if market_type in stats_mapping else None

def get_live_game_stats():
    """
    Fetches all live NBA game stats
    """
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    response = requests.get(url)
    return response.json()

def update_dashboard_stats():
    """
    Updates dashboard with live stats every 60 seconds
    """
    while True:
        live_stats = get_live_game_stats()
        st.session_state.live_stats = live_stats
        sleep(60)

def auto_validate_predictions():
    """
    Automatically validates predictions against real stats
    """
    while True:
        conn = sqlite3.connect('predictions.db')
        pending_predictions = pd.read_sql('SELECT * FROM predictions WHERE result="Pending"', conn)
        
        for idx, pred in pending_predictions.iterrows():
            actual_value = get_espn_stats(pred['player'], pred['market'])
            if actual_value is not None:
                result = 'Hit' if (pred['prediction'] == 'Over' and actual_value > pred['line']) or \
                                 (pred['prediction'] == 'Under' and actual_value < pred['line']) else 'Miss'
                update_result(pred['id'], result)
        
        conn.close()
        sleep(300)  # Check every 5 minutes
def process_live_updates(player_name, market_type, line, prediction):
    """
    Processes live stat updates and returns current progress
    """
    current_value = get_espn_stats(player_name, market_type)
    if current_value is not None:
        progress = (current_value / float(line)) * 100
        st.session_state.last_updates[f"{player_name}_{market_type}"] = {
            'player': player_name,
            'market': market_type,
            'current_value': current_value,
            'line': line,
            'progress': progress,
            'prediction': prediction
        }
        return current_value
    return None

def display_live_tracking():
    """
    Displays live tracking progress bars and metrics
    """
    st.subheader("🎯 Live Prop Tracking")
    for bet_key, stats in st.session_state.last_updates.items():
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            st.write(f"{stats['player']} - {stats['market']}")
            st.progress(min(stats['progress']/100, 1.0))
        with col2:
            st.metric("Current", stats['current_value'])
        with col3:
            st.metric("Target", stats['line'])

def display_bet_card(bet):
    """
    Displays an individual bet card with live tracking
    """
    with st.expander(f"{bet['player']} - {bet['market']}", expanded=True):
        col1, col2, col3 = st.columns([2,1,1])
        
        with col1:
            current_value = get_espn_stats(bet['player'], bet['market'])
            if current_value is not None:
                progress = (current_value / float(bet['line'])) * 100
                st.progress(min(progress/100, 1.0))
                st.metric(
                    "Current Progress",
                    f"{current_value}",
                    delta=f"{current_value - float(bet['line']):.1f} from target",
                    delta_color="normal"
                )
        
        with col2:
            st.metric("Target", bet['line'])
            if current_value >= float(bet['line']):
                st.success("✅ Target Reached!")
            else:
                remaining = float(bet['line']) - current_value
                st.info(f"Needs {remaining:.1f} more")
        
        with col3:
            st.metric("Hit Rate", f"{bet['hit_rate']:.1f}%")
            if bet['result'] == 'Pending':
                if current_value >= float(bet['line']):
                    update_result(bet['id'], 'Hit')
                    st.success("Bet Hit!")
                else:
                    st.write("🎯 Tracking...")

def update_live_tracking():
    """
    Updates all live bets every 60 seconds
    """
    while True:
        results = load_results()
        pending_bets = results[results['result'] == 'Pending']
        
        for _, bet in pending_bets.iterrows():
            process_live_updates(bet['player'], bet['market'], bet['line'], bet['prediction'])
        
        sleep(60)

def handle_tracking_errors():
    """
    Manages tracking errors and notifications
    """
    if 'tracking_errors' not in st.session_state:
        st.session_state.tracking_errors = []

def notify_tracking_status(message, level="info"):
    """
    Displays tracking notifications
    """
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    elif level == "error":
        st.error(message)
    else:
        st.info(message)

def monitor_tracking_health():
    """
    Monitors tracking system health
    """
    while True:
        try:
            current_time = datetime.now()
            last_update = st.session_state.tracking_status['last_update']
            
            if (current_time - last_update).seconds > 300:  # 5 minutes
                notify_tracking_status("Tracking system delayed. Attempting to reconnect...", "warning")
                initialize_tracking()
            
            for bet_id, data in st.session_state.tracking_status['active_bets'].items():
                if (current_time - data['last_update']).seconds > 180:  # 3 minutes
                    notify_tracking_status(f"Bet {bet_id} tracking delayed", "warning")
            
            sleep(60)
        except Exception as e:
            handle_tracking_errors()
            notify_tracking_status(f"Tracking error: {str(e)}", "error")

def track_bet_progress(bet_id, current_value, target):
    """
    Tracks the progress of a bet and returns a status dictionary
    """
    return {
        'bet_id': bet_id,
        'progress': (current_value / float(target)) * 100 if current_value else 0,
        'current': current_value,
        'target': float(target),
        'last_update': datetime.now(),
        'status': 'Hit' if current_value >= float(target) else 'In Progress'
    }

def initialize_tracking():
    """
    Initializes tracking system state variables
    """
    if 'tracking_status' not in st.session_state:
        st.session_state.tracking_status = {
            'last_update': datetime.now(),
            'active_bets': {},
            'updates_count': 0,
            'system_health': 'operational'
        }
    
    if 'live_updates' not in st.session_state:
        st.session_state.live_updates = {}
        
    if 'tracking_errors' not in st.session_state:
        st.session_state.tracking_errors = []


def auto_refresh_stats():
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    current_time = datetime.now()
    if (current_time - st.session_state.last_refresh).seconds >= 30:
        st.rerun()
        st.session_state.last_refresh = current_time

def create_dashboard():
    st.title('🏀 NBA Props Prediction Dashboard')
    initialize_database()
    initialize_tracking()
    handle_tracking_errors()
    
    # Add this near the top of the function
    auto_refresh_stats()
    
    # Start all monitoring threads
    validation_thread = threading.Thread(target=auto_validate_predictions, daemon=True)
    tracking_thread = threading.Thread(target=update_live_tracking, daemon=True)
    health_thread = threading.Thread(target=monitor_tracking_health, daemon=True)
    
    validation_thread.start()
    tracking_thread.start()
    health_thread.start()
    
    # Enhanced tracking display
    with st.sidebar:
        st.header("System Status")
        system_status = st.empty()
        with system_status.container():
            if st.session_state.tracking_errors:
                st.error(f"Recent Errors: {len(st.session_state.tracking_errors)}")
            else:
                st.success("All Systems Operational")
                
        st.metric("Active Trackers", len(st.session_state.tracking_status['active_bets']))
        st.metric("Last Update", st.session_state.tracking_status['last_update'].strftime("%H:%M:%S"))    
    page = st.radio("Navigation", ["Today's Best Bets", "Results Tracking", "Analysis"], horizontal=True)
   
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
            refresh_placeholder = st.empty()
            with refresh_placeholder.container():
                for idx, bet in results.iterrows():
                    current_value = get_espn_stats(bet['player'], bet['market'])
                    display_bet_card(bet)
                    
            # Add refresh button for manual updates
            if st.button("Refresh Stats"):
                st.rerun()
        
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


