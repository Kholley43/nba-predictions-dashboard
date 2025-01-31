import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
import requests
from time import sleep
import threading
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import numpy as np
from optimize_analysis import optimized_analysis
from pytz import timezone

st.set_page_config(
    layout="wide",
    page_title="PrizePicks Analysis Dashboard",
    initial_sidebar_state="expanded"
)

def load_data():
    if 'prediction_data' not in st.session_state:
        st.session_state.prediction_data = pd.DataFrame()
    return st.session_state.prediction_data

def filter_todays_best_bets(df):
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Convert hit rate columns to numeric values
    df['Weighted Hit Rate'] = pd.to_numeric(df['Weighted Hit Rate'])
    df['Hit Rate: Last 5'] = pd.to_numeric(df['Hit Rate: Last 5'])
    df['Hit Rate: Season'] = pd.to_numeric(df['Hit Rate: Season'])

    return df[
        (df['Date'] == today) &
        (df['Weighted Hit Rate'] > 60) &
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
            hit_rate REAL,
            final_value REAL
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


def sync_completed_game_stats(game_data, boxscore):
    """
    Automatically syncs stats when game enters final minute
    """
    period = game_data.get('status', {}).get('period', 0)
    clock = game_data.get('status', {}).get('displayClock', '')
    
    if period == 4 and ':' in clock:
        minutes, seconds = clock.split(':')
        if int(minutes) == 0 and 0 <= int(seconds) <= 30:
            conn = sqlite3.connect('predictions.db')
            cursor = conn.cursor()
            
            # Get all tracked bets for this game
            game_date = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT id, player, market, line 
                FROM predictions 
                WHERE date = ? AND result = 'Pending'
            """, (game_date,))
            
            active_bets = cursor.fetchall()
            
            # Process final stats for each tracked player
            for bet_id, player, market, line in active_bets:
                final_stat = get_espn_stats(player, market)
                if final_stat:
                    result = 'Hit' if final_stat >= float(line) else 'Miss'
                    cursor.execute("""
                        UPDATE predictions 
                        SET result = ? 
                        WHERE id = ?
                    """, (result, bet_id))
            
            conn.commit()
            conn.close()



def trend_analysis(df):
    st.header("Historical Trends")
    if 'Hit Rate: Last 20 Outcomes' in df.columns:
        # Create a callback for player selection
        def on_player_select():
            st.session_state.current_trend_player = st.session_state.player_selector
        
        # Initialize the current player if needed
        if 'current_trend_player' not in st.session_state:
            st.session_state.current_trend_player = df['Player'].iloc[0]
        
        # Player selection with callback
        player_list = list(df['Player'].unique())
        current_index = player_list.index(st.session_state.current_trend_player)
        
        selected_player = st.selectbox(
            "Select Player",
            options=player_list,
            index=current_index,
            key="player_selector",
            on_change=on_player_select
        )
        
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


def get_espn_stats(player_name, market_type, line, bet_date=None):
    """
    Fetches and processes ESPN stats with targeted debugging
    """
    def safe_get_stat(stats_array, index, default=0):
        try:
            return int(stats_array[index]) if stats_array[index] else default
        except (IndexError, ValueError, TypeError):
            return default

    today = datetime.now().strftime('%Y-%m-%d')
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    
    try:
        games_data = requests.get(url, timeout=10).json().get('events', [])
        active_games = []
        completed_games = []
        
        for game in games_data:
            utc_time = datetime.strptime(game['date'], '%Y-%m-%dT%H:%M%z')
            et_time = utc_time.astimezone(timezone('US/Eastern'))
            game_time = et_time.strftime('%I:%M %p ET')
            
            game_info = {
                'id': game['id'],
                'name': game['name'],
                'time': game_time,
                'status': game['status']['type']['state'],
                'period': game.get('status', {}).get('period', 0),
                'clock': game.get('status', {}).get('displayClock', '')
            }
            
            if game_info['status'] == 'in':
                active_games.append(game_info)
            elif game_info['status'] == 'post':
                completed_games.append(game_info)

        # Check completed games first
        for game in completed_games + active_games:
            box_score_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game['id']}"
            
            try:
                response = requests.get(box_score_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    boxscore = data.get('boxscore', {})
                    
                    for team in boxscore.get('players', []):
                        team_name = team.get('team', {}).get('name')
                        
                        for stats in team.get('statistics', []):
                            for athlete in stats.get('athletes', []):
                                if player_name.lower() in athlete['athlete']['displayName'].lower():
                                    player_stats = athlete['stats']
                                    
                                    processed_stats = {
                                        'Minutes': safe_get_stat(player_stats, 0),
                                        'Points': safe_get_stat(player_stats, 13),
                                        'Rebounds': safe_get_stat(player_stats, 6),
                                        'Assists': safe_get_stat(player_stats, 7),
                                        'Blocks': safe_get_stat(player_stats, 8),
                                        'Steals': safe_get_stat(player_stats, 9),
                                        'ThreesMade': safe_get_stat(player_stats, 11)
                                    }
                                    
                                    final_stats = process_market_stats(processed_stats, market_type)
                                    
                    # Update database if game is complete
                    if game['status'] == 'post':
                        conn = sqlite3.connect('predictions.db')
                        cursor = conn.cursor()
                        
                        # First get the line value for this prediction
                        cursor.execute("""
                            SELECT line 
                            FROM predictions 
                            WHERE player = ? AND market = ? AND date = ? AND result = 'Pending'
                        """, (player_name, market_type, today))
                        
                        line_result = cursor.fetchone()
                        if line_result:
                            line = line_result[0]
                            # Now update with the result
                            cursor.execute("""
                                UPDATE predictions 
                                SET result = ?, actual = ?
                                WHERE player = ? AND market = ? AND date = ? AND result = 'Pending'
                            """, ('Hit' if final_stats > line else 'Miss', final_stats, player_name, market_type, today))
                            conn.commit()
                        conn.close()
                        return final_stats
                                    
            except (requests.exceptions.RequestException, ValueError, KeyError):
                continue

    except requests.exceptions.RequestException:
        return 0

    return 0












def check_live_stats(player_name, market_type):
    url = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    response = requests.get(url).json()
    
    for game in response.get('events', []):
        if game['status']['type']['state'] == 'in':
            game_id = game['id']
            stats = fetch_live_game_stats(game_id, player_name, market_type)
            if stats:
                return stats
    return None

def fetch_live_game_stats(game_id, player_name, market_type):
    """
    Fetches live game statistics for a specific player
    """
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    response = requests.get(url).json()
    
    for team in response.get('boxscore', {}).get('players', []):
        for player in team.get('statistics', []):
            if player_name.lower() in player.get('name', '').lower():
                stats = {
                    'Points': player.get('points', 0),
                    'Rebounds': player.get('rebounds', 0),
                    'Assists': player.get('assists', 0),
                    'Steals': player.get('steals', 0),
                    'Blocks': player.get('blocks', 0)
                }
                
                return process_market_stats(stats, market_type)
    
    return None

def extract_stats_from_row(row, market_type):
    """
    Extracts and processes stats from a player's box score row
    """
    stats = {}
    stat_cells = row.find_all('td')
    
    if len(stat_cells) >= 14:  # Standard box score has 14+ columns
        stats['Points'] = int(stat_cells[13].text)
        stats['Rebounds'] = int(stat_cells[6].text)
        stats['Assists'] = int(stat_cells[7].text)
        
        # Calculate combined stats
        stats['PTS+REB'] = stats['Points'] + stats['Rebounds']
        stats['PTS+AST'] = stats['Points'] + stats['Assists']
        stats['REB+AST'] = stats['Rebounds'] + stats['Assists']
        stats['PTS+REB+AST'] = stats['Points'] + stats['Rebounds'] + stats['Assists']
        
        return stats.get(market_type, None)
    
    return None

def get_game_timing():
    return {
        'current_time': datetime.now(),
        'game_times': {
            'pre': [],
            'in': [],
            'post': []
        }
    }


def check_completed_stats(player_name, market_type, game_date):
    today = datetime.now().strftime('%Y-%m-%d')
    
    if 'tracking_cache' not in st.session_state:
        st.session_state.tracking_cache = {}
    
    cache_key = f"{player_name}_{game_date}"
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={game_date}"
    data = requests.get(url).json()
    games = data.get('events', [])
    
    # Debug prints
    st.write("🔍 DEBUG INFO:")
    st.write(f"Date being checked: {game_date}")
    st.write(f"Games found: {len(games)}")
    st.write(f"Player being tracked: {player_name}")
    
    player_data = {
        'name': player_name,
        'market': market_type,
        'games': [],
        'current_value': 0,
        'stats': {
            'Points': 0,
            'Rebounds': 0,
            'Assists': 0,
            'Steals': 0,
            'Blocks': 0,
            'Minutes': '0',
            'FG': '0-0',
            '3PT': '0-0'
        }
    }
    
    for game in games:
        game_id = game['id']
        game_status = game.get('status', {}).get('type', {}).get('state', '')
        period = game.get('status', {}).get('period', 1)
        clock = game.get('status', {}).get('displayClock', '')
        
        # Debug game status
        st.write(f"Game {game_id}:")
        st.write(f"- Status: {game_status}")
        st.write(f"- Period: {period}")
        st.write(f"- Clock: {clock}")
        
        if game_status in ['in', 'post']:
            box_score_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
            st.write(f"📊 Fetching box score from: {box_score_url}")
            box_score = requests.get(box_score_url).json()
            
            for team in box_score.get('boxscore', {}).get('teams', []):
                for player in team.get('statistics', []):
                    if player_name.lower() in player.get('athlete', {}).get('displayName', '').lower():
                        st.write(f"✅ Found {player_name}'s stats")
                        stats_array = player.get('stats', [])
                        if stats_array:
                            player_data['stats'] = {
                                'Points': int(stats_array[0]) if len(stats_array) > 0 else 0,
                                'Rebounds': int(stats_array[5]) if len(stats_array) > 5 else 0,
                                'Assists': int(stats_array[6]) if len(stats_array) > 6 else 0,
                                'Steals': int(stats_array[7]) if len(stats_array) > 7 else 0,
                                'Blocks': int(stats_array[8]) if len(stats_array) > 8 else 0,
                                'Minutes': stats_array[1] if len(stats_array) > 1 else '0',
                                'FG': f"{stats_array[2]}-{stats_array[3]}" if len(stats_array) > 3 else '0-0',
                                '3PT': f"{stats_array[4]}-{stats_array[5]}" if len(stats_array) > 5 else '0-0'
                            }
                            
                            # Market type calculations
                            if market_type == 'Points':
                                player_data['current_value'] = player_data['stats']['Points']
                            elif market_type == 'Rebounds':
                                player_data['current_value'] = player_data['stats']['Rebounds']
                            elif market_type == 'Assists':
                                player_data['current_value'] = player_data['stats']['Assists']
                            elif market_type == 'PTS+REB':
                                player_data['current_value'] = player_data['stats']['Points'] + player_data['stats']['Rebounds']
                            elif market_type == 'PTS+AST':
                                player_data['current_value'] = player_data['stats']['Points'] + player_data['stats']['Assists']
                            elif market_type == 'REB+AST':
                                player_data['current_value'] = player_data['stats']['Rebounds'] + player_data['stats']['Assists']
                            elif market_type == 'PTS+REB+AST':
                                player_data['current_value'] = player_data['stats']['Points'] + player_data['stats']['Rebounds'] + player_data['stats']['Assists']
        
        game_info = {
            'id': game_id,
            'status': game_status,
            'teams': [team.get('team', {}).get('name') for team in game.get('competitions', [])[0].get('competitors', [])],
            'time': clock,
            'period': period,
            'quarter': f"Q{period}" if period <= 4 else "OT" if period > 4 else "",
            'display_period': f"{'Q' if period <= 4 else 'OT'}{period if period <= 4 else period-4} - {clock}"
        }
        player_data['games'].append(game_info)
    
    st.session_state.tracking_cache[cache_key] = player_data
    
    if game_date == today:
        st.sidebar.write(f"📊 Stats Updated: {player_data['stats']}")
    
    return player_data










def get_game_status(game_id):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    response = requests.get(url).json()
    return {
        'status': response.get('status', {}).get('type', {}).get('state', ''),
        'period': response.get('status', {}).get('period', 0),
        'clock': response.get('status', {}).get('displayClock', '')
    }



def process_stats(stats_row, market_type):
    stat_indices = {
        'MIN': 0, 'FG': 1, '3PT': 2, 'FT': 3,
        'OREB': 4, 'DREB': 5, 'REB': 6, 'AST': 7,
        'STL': 8, 'BLK': 9, 'TO': 10, 'PF': 11,
        '+/-': 12, 'PTS': 13
    }

    fg = stats_row[stat_indices['FG']].text.split('-')
    pt3 = stats_row[stat_indices['3PT']].text.split('-')
    ft = stats_row[stat_indices['FT']].text.split('-')
    
    base_stats = {
        'Points': int(stats_row[stat_indices['PTS']].text),
        'Rebounds': int(stats_row[stat_indices['REB']].text),
        'Assists': int(stats_row[stat_indices['AST']].text),
        'Steals': int(stats_row[stat_indices['STL']].text),
        'Blocks': int(stats_row[stat_indices['BLK']].text),
        'Minutes': int(stats_row[stat_indices['MIN']].text),
        'OffReb': int(stats_row[stat_indices['OREB']].text),
        'DefReb': int(stats_row[stat_indices['DREB']].text),
        'Turnovers': int(stats_row[stat_indices['TO']].text)
    }
    
    shooting_stats = {
        'FGM': int(fg[0]), 'FGA': int(fg[1]),
        '3PM': int(pt3[0]), '3PA': int(pt3[1]),
        'FTM': int(ft[0]), 'FTA': int(ft[1])
    }
    
    combined_stats = {
        **base_stats,
        **shooting_stats,
        'PTS+REB': base_stats['Points'] + base_stats['Rebounds'],
        'PTS+AST': base_stats['Points'] + base_stats['Assists'],
        'REB+AST': base_stats['Rebounds'] + base_stats['Assists'],
        'PTS+REB+AST': base_stats['Points'] + base_stats['Rebounds'] + base_stats['Assists'],
        'STL+BLK': base_stats['Steals'] + base_stats['Blocks'],
        'BLK+STL': base_stats['Blocks'] + base_stats['Steals'],
        '3PT Made': shooting_stats['3PM']
    }
    
    st.sidebar.write("Stats found:", combined_stats)
    return combined_stats.get(market_type, 0)


def process_market_stats(stats, market_type):
    """Helper function to calculate combined stats"""
    market_stats = {
        'Points': stats['Points'],
        'Rebounds': stats['Rebounds'],
        'Assists': stats['Assists'],
        'PTS+REB': stats['Points'] + stats['Rebounds'],
        'PTS+AST': stats['Points'] + stats['Assists'],
        'REB+AST': stats['Rebounds'] + stats['Assists'],
        'PTS+REB+AST': stats['Points'] + stats['Rebounds'] + stats['Assists']
    }
    return market_stats.get(market_type, 0)
    
def process_market_stats(stats, market_type):
    """
    Processes raw stats into market-specific values
    """
    market_calculations = {
        'Points': stats['Points'],
        'Rebounds': stats['Rebounds'],
        'Assists': stats['Assists'],
        'PTS+REB': stats['Points'] + stats['Rebounds'],
        'PTS+AST': stats['Points'] + stats['Assists'],
        'REB+AST': stats['Rebounds'] + stats['Assists'],
        'PTS+REB+AST': stats['Points'] + stats['Rebounds'] + stats['Assists']
    }
    return market_calculations.get(market_type, 0)

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

def validate_stats_data(stats_array):
    """Validates the stats array structure"""
    if not stats_array:
        return False
    
    required_indices = [0, 5, 6, 7, 8]  # Points, Rebounds, Assists, Steals, Blocks
    return all(i < len(stats_array) for i in required_indices)


def auto_validate_predictions():
    results = load_results()
    updated = False
    
    for idx, pred in results.iterrows():
        if pred['result'] == 'Pending':
            actual_stat = get_espn_stats(pred['player'], pred['market'])
            if actual_stat > 0:
                result = 'Hit' if actual_stat >= float(pred['line']) else 'Miss'
                update_result(idx, result)
                updated = True
    
    if updated:
        st.rerun()
def process_live_updates(player_name, market_type, line, prediction):
    """
    Processes live stat updates and returns current progress
    """
    stats = get_espn_stats(player_name, market_type)
    
    if isinstance(stats, dict):
        current_value = stats.get(market_type, 0)
    else:
        current_value = stats if stats is not None else 0

    if current_value is not None:
        progress = (float(current_value) / float(line)) * 100
        
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


def display_tracking_section():
    st.header("Live Tracking")
    results = load_results()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Split into today's and historical bets
    todays_bets = results[results['date'] == today]
    historical_bets = results[results['date'] != today]
    
    if len(todays_bets) > 0:
        st.subheader("Today's Active Bets")
        for idx, bet in todays_bets.iterrows():
            display_live_bet_card(bet)
            
    if len(historical_bets) > 0:
        st.subheader("Historical Bets")
        for idx, bet in historical_bets.iterrows():
            display_bet_card(bet)

def display_live_bet_card(bet):
    st.write("🔍 DEBUG: Live Bet Card Data")
    st.write("Incoming bet data:", bet)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    if bet['date'] == today:
        st.write("\n📊 Fetching live stats...")
        stats_data = get_espn_stats(bet['player'], bet['market'])
        st.write("Raw stats response:", stats_data)
        
        with st.container():
            header_col, stats_col = st.columns([2, 3])
            
            with header_col:
                st.subheader(f"{bet['player']} - {bet['market']}")
                st.caption(f"Line: {bet['line']}")
                
            with stats_col:
                current_value = stats_data['current_value'] if isinstance(stats_data, dict) else stats_data
                st.write("DEBUG: Current value:", current_value)
                
                if current_value is not None:
                    progress = min((float(current_value) / float(bet['line'])), 1.0)
                    st.write("DEBUG: Progress value:", progress)
                    st.progress(progress)
                    
            metrics_col1, metrics_col2, metrics_col3, action_col = st.columns([2,1,1,1])
            
            with metrics_col1:
                if current_value is not None:
                    delta = current_value - float(bet['line'])
                    st.write("DEBUG: Delta value:", delta)
                    st.metric(
                        "Live Progress",
                        f"{current_value}",
                        delta=f"{delta:.1f} from target",
                        delta_color="normal" if delta < 0 else "inverse"
                    )
            
            with metrics_col2:
                st.metric("Target", bet['line'])
                if current_value and current_value >= float(bet['line']):
                    st.success("✅ HIT")
                else:
                    remaining = float(bet['line']) - current_value if current_value else float(bet['line'])
                    st.write("DEBUG: Remaining needed:", remaining)
                    st.info(f"🎯 Needs {remaining:.1f} more")
            
            with metrics_col3:
                st.metric("Hit Rate", f"{bet['hit_rate']:.1f}%")
                refresh = st.button("🔄 Refresh", key=f"refresh_{bet['id']}")
                if refresh:
                    st.write("DEBUG: Processing refresh...")
                    process_live_updates(
                        bet['player'],
                        bet['market'],
                        bet['line'],
                        bet.get('prediction', 'over')
                    )
            
            with action_col:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📊", key=f"stats_{bet['id']}", help="View detailed stats"):
                        st.session_state[f"show_stats_{bet['id']}"] = True
                with col2:
                    if st.button("🗑️", key=f"delete_{bet['id']}", help="Remove bet"):
                        st.write("DEBUG: Deleting bet:", bet['id'])
                        delete_bet(bet['id'])
                        st.success("Bet removed")
                        st.rerun()
            
            if st.session_state.get(f"show_stats_{bet['id']}", False):
                with st.expander("Detailed Stats", expanded=True):
                    if isinstance(stats_data, dict):
                        st.write("DEBUG: Detailed stats data:", stats_data)
                        for key, value in stats_data.items():
                            if key != 'current_value':
                                st.write(f"{key}: {value}")






def delete_bet(bet_id):
    """
    Deletes a bet from the tracking database
    """
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()
    
    # First verify the bet exists
    cursor.execute('SELECT id FROM predictions WHERE id = ?', (bet_id,))
    if cursor.fetchone():
        # Delete the bet
        cursor.execute('DELETE FROM predictions WHERE id = ?', (bet_id,))
        conn.commit()
        st.session_state.prediction_data = pd.read_sql('SELECT * FROM predictions', conn)
    
    conn.close()
    return True



def display_bet_card(bet):
    with st.expander(f"{bet['player']} - {bet['market']}", expanded=True):
        col1, col2, col3 = st.columns([2,1,1])
        
        # Get live game data
        stats_data = check_completed_stats(bet['player'], bet['market'], bet['date'])
        
        with col1:
            current_value = stats_data['current_value'] if stats_data else None
            if current_value is not None:
                progress = (float(current_value) / float(bet['line'])) * 100
                st.progress(min(progress/100, 1.0))
                st.metric(
                    "Current Progress",
                    f"{current_value}",
                    delta=f"{current_value - float(bet['line']):.1f} from target",
                    delta_color="normal"
                )
            else:
                st.info("📊 Waiting for stats...")
        
        with col2:
            st.metric("Target", bet['line'])
            if current_value is not None:
                if current_value >= float(bet['line']):
                    st.success("✅ Target Reached!")
                else:
                    remaining = float(bet['line']) - current_value
                    st.info(f"📈 Needs {remaining:.1f} more")
            else:
                st.info("🕒 Game not started")
        
        with col3:
            st.metric("Hit Rate", f"{bet['hit_rate']:.1f}%")
            if bet['result'] == 'Pending':
                if current_value is not None and current_value >= float(bet['line']):
                    update_result(bet['id'], 'Hit')
                    st.success("🎯 Bet Hit!")
                else:
                    st.write("📊 Tracking...")
            
            if st.button("🗑️ Delete", key=f"delete_{bet['id']}", type="secondary"):
                delete_bet(bet['id'])
                st.success("✅ Bet removed from tracking")
                st.rerun()

    return current_value






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

def add_advanced_analysis(df):
    # Streak Detection & Hot Players
    st.header("🔥 Hot/Cold Analysis")
    col1, col2 = st.columns(2)
    with col1:
        hot_players = df[df['Hit Rate: Last 5'] > 70].groupby('Player').agg({
            'Hit Rate: Last 5': 'mean',
            'Weighted Hit Rate': 'mean',
            'Market Name': lambda x: list(x.unique())
        }).sort_values('Hit Rate: Last 5', ascending=False)
        st.subheader("🎯 Players on Hot Streaks")
        st.dataframe(hot_players.head(10))
    
    # Opponent Matchup Analysis
    with col2:
        matchup_success = df.groupby(['Player', 'Opponent'])['Hit Rate: Last 20'].mean()
        best_matchups = matchup_success.sort_values(ascending=False)
        st.subheader("💪 Best Player vs Team Matchups")
        st.dataframe(best_matchups.head(10))
    
    # Market Correlation Analysis
    st.header("📊 Market Correlation Insights")
    market_correlations = pd.pivot_table(
        df, 
        values='Weighted Hit Rate',
        index='Player',
        columns='Market Name',
        aggfunc='mean'
    ).corr()
    fig = px.imshow(market_correlations, 
                    title="Market Type Correlations",
                    color_continuous_scale="RdBu")
    st.plotly_chart(fig)
    
    # Time-Based Success Patterns
    st.header("⏰ Time-Based Success Patterns")
    time_success = df.groupby('Time')['Weighted Hit Rate'].mean().sort_values(ascending=False)
    fig = px.bar(time_success, 
                 title="Win Rate by Game Time",
                 labels={'value': 'Success Rate', 'Time': 'Game Time'})
    st.plotly_chart(fig)

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
        results = load_results()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Update live bets more frequently
        live_bets = results[results['date'] == today]
        for _, bet in live_bets.iterrows():
            current_value = get_espn_stats(bet['player'], bet['market'])
            if current_value:
                st.session_state[f'live_stat_{bet["id"]}'] = current_value
        
        st.session_state.last_refresh = current_time
        st.rerun()

def analyze_line_movement(df):
    st.header("📈 Line Movement Analysis")
    col1, col2 = st.columns(2)
    
    with col1:
        # Compare current lines to season averages
        line_comparison = df.groupby('Player').agg({
            'Line': ['mean', 'std', 'last'],
            'Weighted Hit Rate': 'mean'
        })
        line_comparison['Line_Diff'] = line_comparison['Line']['last'] - line_comparison['Line']['mean']
        value_spots = line_comparison[abs(line_comparison['Line_Diff']) > line_comparison['Line']['std']]
        st.subheader("Significant Line Movements")
        st.dataframe(value_spots)

def analyze_injury_impact(df, injury_data):
    st.header("🏥 Injury Impact Opportunities")
    # Cross reference injuries with player matchups
    for idx, injury in injury_data.iterrows():
        team = injury['Team']
        matching_games = df[df['Opponent'] == team]
        if len(matching_games) > 0:
            st.write(f"**{injury['Player']} ({team}) {injury['Status']}**")
            st.dataframe(matching_games[['Player', 'Market Name', 'Line', 'Weighted Hit Rate']])

def find_optimal_stacks(df):
    st.header("🎯 Optimal Prop Stacks")
    
    # Find correlated props
    correlations = df.pivot_table(
        values='Hit Rate: Last 20 Outcomes',
        index='Player',
        columns='Market Name',
        aggfunc='mean'
    ).corr()
    
    # Identify strong positive correlations
    strong_correlations = correlations.unstack()
    strong_correlations = strong_correlations[strong_correlations > 0.7]
    
    st.subheader("Recommended 2-Leg Parlays")
    for idx, corr in strong_correlations.items():
        if idx[0] != idx[1]:  # Avoid self-correlations
            st.write(f"**{idx[0]} + {idx[1]}** (Correlation: {corr:.2f})")
            combined_plays = df[
                (df['Market Name'].isin([idx[0], idx[1]])) &
                (df['Weighted Hit Rate'] > 60)
            ]
            st.dataframe(combined_plays[['Player', 'Market Name', 'Line', 'Weighted Hit Rate']])



def enhanced_market_analysis(df):
    st.header("💰 Advanced Market Insights")
    
    # Market success by time slots
    time_analysis = df.groupby(['Time', 'Market Name'])['Weighted Hit Rate'].mean()
    fig_time = px.heat_map(time_analysis.unstack(), 
                          title="Best Markets by Game Time")
    st.plotly_chart(fig_time)
    
    # Opponent impact analysis
    opp_analysis = df.groupby(['Opponent', 'Market Name'])['Hit Rate: Last 5'].mean()
    top_matchups = opp_analysis.unstack().sort_values(ascending=False)
    st.write("🎯 Top Player vs Team Matchups")
    st.dataframe(top_matchups.head(10))
    
    # Streak detection
    st.subheader("🔥 Hot Trends")
    recent_form = df[df['Hit Rate: Last 5'] > 70]
    st.write("Players on Fire (>70% in last 5):")
    st.dataframe(recent_form[['Player', 'Market Name', 'Hit Rate: Last 5']])
    
    # Line value analysis
    st.subheader("📊 Line Value Spots")
    value_plays = df[
        (df['Weighted Hit Rate'] > 65) & 
        (df['Hit Rate: Last 5'] > df['Hit Rate: Season'])
    ]
    st.write("High Probability Plays:")
    st.dataframe(value_plays[['Player', 'Market Name', 'Line', 'Weighted Hit Rate']])

def generate_ai_insights(df):
    st.header("🤖 Elite AI Strategic Analysis")
    
    # Premium Parlay Builder
    st.subheader("🎲 Elite Parlay Combinations")
    correlations = df.pivot_table(
        values='Hit Rate: Last 20',
        index='Player',
        columns='Market Name',
        aggfunc='mean'
    ).corr()
    
    strong_pairs = correlations[correlations > 0.85].stack()
    st.write("💫 Today's Premium Stacks:")
    for pair, corr in strong_pairs.nlargest(3).items():
        if pair[0] != pair[1]:
            matching_plays = df[
                (df['Market Name'].isin([pair[0], pair[1]])) &
                (df['Weighted Hit Rate'] > 65) &  # Increased threshold
                (df['Hit Rate: Last 5'] > 60)     # Added recent form filter
            ]
            if not matching_plays.empty:
                st.write(f"🔒 High-Value Stack ({corr:.2f} correlation):")
                st.dataframe(matching_plays[['Player', 'Market Name', 'Line', 'Weighted Hit Rate', 'Hit Rate: Last 5']])
    
    # Advanced Market Analysis
    st.subheader("💰 Premium Value Spots")
    elite_plays = df[
        (df['Weighted Hit Rate'] > df['Hit Rate: Season'] + 12) &  # Increased edge requirement
        (df['Hit Rate: Last 5'] > 70) &                            # Stronger recent form
        (df['Hit Rate: Last 10'] > 60) &                          # Added medium-term consistency
        (df['Hit Rate: Last 20'] > 55)                            # Added long-term baseline
    ].sort_values('Weighted Hit Rate', ascending=False)
    
    if not elite_plays.empty:
        st.write("🎯 Highest Probability Plays:")
        st.dataframe(elite_plays[['Player', 'Market Name', 'Line', 'Weighted Hit Rate', 'Hit Rate: Last 5', 'Hit Rate: Last 10']])
    
    # Elite Player Insights
    st.subheader("🏀 Elite Player Trends")
    hot_players = df[
        (df['Hit Rate: Last 5'] > df['Hit Rate: Season'] + 15) &
        (df['Weighted Hit Rate'] > 68) &                        # Increased threshold
        (df['Hit Rate: Last 10'] > df['Hit Rate: Season'] + 5) &  # Added medium-term momentum
        (df['Hit Rate: Last 20'] > 55)                            # Added long-term consistency
    ].sort_values(['Hit Rate: Last 5', 'Weighted Hit Rate'], ascending=[False, False])
    
    if not hot_players.empty:
        st.write("🔥 Players in Peak Form:")
        for _, player in hot_players.head(3).iterrows():  # Reduced to top 3 for focus
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Recent Form", f"{player['Hit Rate: Last 5']}%", 
                         f"+{player['Hit Rate: Last 5'] - player['Hit Rate: Season']:.1f}%")
            with col2:
                st.metric("10-Game Trend", f"{player['Hit Rate: Last 10']}%")
            with col3:
                st.metric("Line Value", player['Line'], 
                         f"{player['Weighted Hit Rate']:.1f}% probability")
    
    # Supreme Value Opportunities
    st.subheader("💎 Supreme Value Plays")
    supreme_value = df[
        (df['Weighted Hit Rate'] > 72) &                    
        (df['Hit Rate: Last 5'] > df['Hit Rate: Season'] + 8) &
        (df['Hit Rate: Last 10'] > 60)                   
    ].sort_values('Weighted Hit Rate', ascending=False)

    for _, play in supreme_value.head(3).iterrows():
        confidence_score = calculate_enhanced_confidence_score(play)
        if confidence_score > 75:
            st.write(f"⭐ {play['Player']} {play['Market Name']}")
            st.write(f"- Line: {play['Line']}")
            st.write(f"- Elite Confidence Score: {confidence_score}/100")
            st.write(f"- Key Factors: Strong recent form, consistent long-term success, favorable line value")

    st.subheader("🏀 Cross-Team Parlay Builder")
    generate_cross_team_parlays(df)
    st.subheader("🔒 Game scoring leader")
    analyze_game_scoring_leaders(df)
    st.subheader("🔒 Safe alt lines")
    find_safe_alt_lines(df)

def calculate_enhanced_confidence_score(play):
    """Calculate a more sophisticated confidence score"""
    score = 0
    score += min(play['Weighted Hit Rate'], 100) * 0.4
    score += min(play['Hit Rate: Last 5'], 100) * 0.3
    score += min(play['Hit Rate: Last 10'], 100) * 0.2
    score += min(play['Hit Rate: Last 20'], 100) * 0.1
    return round(score)

def generate_cross_team_parlays(df):
    st.subheader("🏀 Elite Cross-Team Parlays")
    
    used_players = set()  # Track players already recommended
    
    high_prob_plays = df[
        (df['Weighted Hit Rate'] > 65) &
        (df['Hit Rate: Last 5'] > 60) &
        (df['Hit Rate: Last 10'] > 55)
    ]
    
    team_plays = high_prob_plays.groupby('Team')
    parlay_combinations = []
    teams = list(team_plays.groups.keys())
    
    for team1 in teams:
        for team2 in teams:
            if team1 != team2:
                team1_plays = team_plays.get_group(team1)
                team2_plays = team_plays.get_group(team2)
                
                # Filter out already used players
                team1_plays = team1_plays[~team1_plays['Player'].isin(used_players)]
                team2_plays = team2_plays[~team2_plays['Player'].isin(used_players)]
                
                if len(team1_plays) > 0 and len(team2_plays) > 0:
                    best_play1 = team1_plays.nlargest(1, 'Weighted Hit Rate')
                    best_play2 = team2_plays.nlargest(1, 'Weighted Hit Rate')
                    
                    # Add players to used set
                    used_players.add(best_play1['Player'].iloc[0])
                    used_players.add(best_play2['Player'].iloc[0])
                    
                    combined_prob = (best_play1['Weighted Hit Rate'].iloc[0] + 
                                   best_play2['Weighted Hit Rate'].iloc[0]) / 2
                    
                    parlay_combinations.append({
                        'team1_player': best_play1['Player'].iloc[0],
                        'team1_market': best_play1['Market Name'].iloc[0],
                        'team1_line': best_play1['Line'].iloc[0],
                        'team2_player': best_play2['Player'].iloc[0],
                        'team2_market': best_play2['Market Name'].iloc[0],
                        'team2_line': best_play2['Line'].iloc[0],
                        'combined_prob': combined_prob
                    })
    
    top_parlays = sorted(parlay_combinations, key=lambda x: x['combined_prob'], reverse=True)
    for parlay in top_parlays[:3]:  # Show top 3 unique player combinations
        st.write(f"💫 Premium Cross-Team Parlay ({parlay['combined_prob']:.1f}% combined probability)")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"🏀 {parlay['team1_player']}")
            st.write(f"Market: {parlay['team1_market']}")
            st.write(f"Line: {parlay['team1_line']}")
        with col2:
            st.write(f"🏀 {parlay['team2_player']}")
            st.write(f"Market: {parlay['team2_market']}")
            st.write(f"Line: {parlay['team2_line']}")

def analyze_game_scoring_leaders(df):
    st.subheader("🏆 Game Scoring Leaders")
    
    games = df.groupby(['Team', 'Opponent'])
    for (team, opponent), game_data in games:
        st.write(f"📊 {team} vs {opponent}")
        
        # Filter for points markets
        points_data = game_data[
            (game_data['Market Name'].str.contains('Points')) &
            (game_data['Weighted Hit Rate'] > 60)
        ].sort_values('Line', ascending=False)
        
        if not points_data.empty:
            top_scorer = points_data.iloc[0]
            st.metric(
                "Projected Top Scorer",
                f"{top_scorer['Player']}",
                f"{top_scorer['Line']} points ({top_scorer['Weighted Hit Rate']:.1f}% confidence)"
            )

def find_safe_alt_lines(df):
    st.subheader("🎯 Alternative Line Explorer")
    
    alt_lines = df.copy()
    alt_lines['Safe Line'] = alt_lines.apply(lambda x: 
        calculate_safe_line(
            x['Line'], 
            x['Hit Rate: Last 20'],
            x['Hit Rate: Last 5'],
            x['Weighted Hit Rate']
        ), axis=1
    )
    
    # Minimal filtering - showing almost all options
    safe_plays = alt_lines[
        (alt_lines['Weighted Hit Rate'] > 35)  # Very low threshold to see more options
    ].sort_values(['Weighted Hit Rate'], ascending=[False])
    
    st.write("🎲 Full Range of Alternative Lines")
    
    for _, play in safe_plays.head(15).iterrows():  # Showing more options
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"🏀 {play['Player']}")
            st.write(f"Market: {play['Market Name']}")
        with col2:
            st.write(f"Original: {play['Line']}")
            st.write(f"Current Probability: {play['Weighted Hit Rate']:.1f}%")
        with col3:
            ultra_safe = round(play['Line'] * 0.85, 1)  # More aggressive reduction
            moderate = round(play['Line'] * 0.90, 1)
            st.write(f"Ultra Safe: {ultra_safe}")
            st.write(f"Moderate: {moderate}")
        st.write("---")


def calculate_safe_line(original_line, long_term_rate, recent_rate, weighted_rate):
    # Adjustments based on multiple factors
    base_adjustment = 0.92
    if weighted_rate > 65:
        base_adjustment = 0.88
    elif recent_rate > long_term_rate:
        base_adjustment = 0.90
    
    return round(original_line * base_adjustment, 1)



def create_dashboard():
    st.title('🏀 NBA Props Prediction Dashboard')
    initialize_database()
    initialize_tracking()
    handle_tracking_errors()
    
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ''
    
    if 'last_updates' not in st.session_state:
        st.session_state.last_updates = {}
    
    auto_refresh_stats()
    
    # Start all monitoring threads
    validation_thread = threading.Thread(target=auto_validate_predictions, daemon=True)
    tracking_thread = threading.Thread(target=update_live_tracking, daemon=True)
    health_thread = threading.Thread(target=monitor_tracking_health, daemon=True)
    
    validation_thread.start()
    tracking_thread.start()
    health_thread.start()
    
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
    
    tabs = st.tabs(["Today's Best Bets", "Live Tracking", "Historical Bets", "Analysis"])
    
    search_col1, search_col2 = st.columns([3,1])
    with search_col1:
        new_search = st.text_input("🔍 Search Players", key="player_search", value=st.session_state.search_query)
    with search_col2:
        if st.button("Clear", key="clear_search"):
            st.session_state.search_query = ''
            st.rerun()
    
    if new_search != st.session_state.search_query:
        st.session_state.search_query = new_search
    
    uploaded_file = st.file_uploader("Upload your predictions CSV", type=['csv'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state.prediction_data = df
    
    with tabs[0]:  # Today's Best Bets
        if 'prediction_data' in st.session_state:
            df = st.session_state.prediction_data
            if st.session_state.search_query:
                df = df[df['Player'].str.contains(st.session_state.search_query, case=False)]
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
    
    with tabs[1]:  # Live Tracking
        results = load_results()
        if len(results) > 0:
            if st.session_state.search_query:
                results = results[results['player'].str.contains(st.session_state.search_query, case=False)]
            
            today = datetime.now().strftime('%Y-%m-%d')
            todays_bets = results[results['date'] == today].sort_values('player')  # Sort by player name
            
            refresh_placeholder = st.empty()
            with refresh_placeholder.container():
                if len(todays_bets) > 0:
                    st.subheader("Today's Active Bets")
                    for idx, bet in todays_bets.iterrows():
                        stats_data = get_espn_stats(bet['player'], bet['market'])
                        current_value = stats_data['current_value'] if isinstance(stats_data, dict) else stats_data
                        
                        # Check if bet should be marked complete
                        if current_value is not None:
                            target = float(bet['line'])
                            if current_value >= target:
                                update_result(bet['id'], 'Hit')
                        
                        display_live_bet_card(bet)
                else:
                    st.info("No active bets for today")
                    
            if st.button("Refresh Stats"):
                st.rerun()






    with tabs[2]:  # Historical Bets
        results = load_results()
        if len(results) > 0:
            if st.session_state.search_query:
                results = results[results['player'].str.contains(st.session_state.search_query, case=False)]
            
            today = datetime.now().strftime('%Y-%m-%d')
            historical_bets = results[
                (results['date'] != today)
            ].sort_values(['date', 'player'], ascending=[False, True])  # Sort by date (newest first) and player name
            
            if len(historical_bets) > 0:
                hits = len(historical_bets[historical_bets['result'] == 'Hit'])
                total = len(historical_bets[historical_bets['result'] != 'Pending'])
                if total > 0:
                    win_rate = (hits / total) * 100
                    st.metric("Historical Win Rate", f"{win_rate:.1f}%")
                
                for idx, bet in historical_bets.iterrows():
                    display_bet_card(bet)
            else:
                st.info("No historical bets found")

    

    with tabs[3]:  # Analysis
        if 'prediction_data' in st.session_state:
            df = st.session_state.prediction_data
            if st.session_state.search_query:
                df = df[df['Player'].str.contains(st.session_state.search_query, case=False)]
            
            # Get optimized metrics first
            player_metrics, market_metrics = optimized_analysis(df)
            
            # Load injury data
            injury_data = pd.read_csv('nba-injury-report.csv')
            
            st.header("📊 Performance Overview")
            col1, col2, col3, col4 = st.columns(4)
            # Use the pre-calculated metrics
            metrics_display(player_metrics, col1, col2, col3, col4)

            
            # Market Analysis Section
            st.header("🎯 Market Intelligence")
            market_col1, market_col2 = st.columns(2)
            with market_col1:
                market_analysis(df)
            with market_col2:
                top_markets = df.groupby('Market Name')['Weighted Hit Rate'].mean().sort_values(ascending=False)
                st.subheader("Most Profitable Markets")
                fig = px.bar(top_markets, title="Market Success Rates")
                st.plotly_chart(fig)
            
            # Line Movement Analysis
            st.header("📈 Line Movement Tracker")
            line_col1, line_col2 = st.columns(2)
            with line_col1:
                # Compare lines to season averages
                line_comparison = df.groupby(['Player', 'Market Name']).agg({
                    'Line': ['mean', 'std', 'last'],
                    'Weighted Hit Rate': 'mean'
                }).round(2)
                line_comparison['Value'] = line_comparison['Line']['last'] - line_comparison['Line']['mean']
                significant_moves = line_comparison[abs(line_comparison['Value']) > line_comparison['Line']['std']]
                st.subheader("📊 Significant Line Movements")
                st.dataframe(significant_moves)
            
            with line_col2:
                # Injury Impact Analysis
                st.subheader("🏥 Key Injuries Affecting Lines")
                today = datetime.now().strftime('%Y-%m-%d')
                todays_injuries = injury_data[injury_data['Status'].isin(['Out', 'Game Time Decision'])]
                for _, injury in todays_injuries.iterrows():
                    affected_players = df[df['Opponent'] == injury['Team']]
                    if len(affected_players) > 0:
                        st.write(f"**{injury['Player']} ({injury['Team']}) - {injury['Status']}**")
                        st.dataframe(affected_players[['Player', 'Market Name', 'Line', 'Weighted Hit Rate']])
            
            # Player Analysis Section
            st.header("👥 Player Insights")
            player_col1, player_col2 = st.columns(2)
            with player_col1:
                player_performance(df)
            with player_col2:
                recent_form = df.groupby('Player')['Hit Rate: Last 5'].mean().sort_values(ascending=False)
                fig = px.bar(recent_form.head(10), title="Top Players by Recent Form")
                st.plotly_chart(fig)
            
            # Distribution Analysis
            st.header("📈 Success Patterns")
            dist_col1, dist_col2 = st.columns(2)
            with dist_col1:
                hit_rate_distribution(df)
            with dist_col2:
                df['Line Range'] = pd.qcut(df['Line'], q=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
                line_success = df.groupby('Line Range')['Weighted Hit Rate'].mean()
                fig = px.bar(line_success, title="Success by Line Range")
                st.plotly_chart(fig)
            
            # Optimal Stacks Analysis
            st.header("🎯 Optimal Prop Stacks")
            stack_col1, stack_col2 = st.columns(2)
            with stack_col1:
                correlations = df.pivot_table(
                    values='Hit Rate: Last 20',
                    index='Player',
                    columns='Market Name',
                    aggfunc='mean'
                ).corr()
                strong_pairs = correlations.unstack()
                strong_pairs = strong_pairs[(strong_pairs > 0.7) & (strong_pairs < 1.0)]
                st.subheader("💪 Recommended Parlays")
                for idx, corr in strong_pairs.items():
                    if idx[0] != idx[1]:
                        st.write(f"**{idx[0]} + {idx[1]}** (Correlation: {corr:.2f})")
            
            # Hot/Cold Analysis Section
            st.header("🔥 Hot/Cold Analysis")
            hot_col1, hot_col2 = st.columns(2)
            with hot_col1:
                hot_players = df[df['Hit Rate: Last 5'] > 70].groupby('Player').agg({
                    'Hit Rate: Last 5': 'mean',
                    'Weighted Hit Rate': 'mean',
                    'Market Name': lambda x: list(x.unique())
                }).sort_values('Hit Rate: Last 5', ascending=False)
                st.subheader("🎯 Players on Hot Streaks")
                st.dataframe(hot_players.head(10))
            
            with hot_col2:
                matchup_success = df.groupby(['Player', 'Opponent'])['Hit Rate: Last 20'].mean()
                best_matchups = matchup_success.sort_values(ascending=False)
                st.subheader("💪 Best Player vs Team Matchups")
                st.dataframe(best_matchups.head(10))
            
            # Market Correlation Analysis
            st.header("📊 Market Correlation Insights")
            market_correlations = pd.pivot_table(
                df,
                values='Weighted Hit Rate',
                index='Player',
                columns='Market Name',
                aggfunc='mean'
            ).corr()
            fig = px.imshow(market_correlations,
                            title="Market Type Correlations",
                            color_continuous_scale="RdBu")
            st.plotly_chart(fig)
            
            # Time Analysis
            st.header("⏰ Time-Based Success Patterns")
            time_success = df.groupby('Time')['Weighted Hit Rate'].mean().sort_values(ascending=False)
            fig = px.bar(time_success,
                        title="Win Rate by Game Time",
                        labels={'value': 'Success Rate', 'Time': 'Game Time'})
            st.plotly_chart(fig)
            
            # Value Finder
            st.header("💎 Value Opportunities")
            value_plays = df[
                (df['Weighted Hit Rate'] > 65) &
                (df['Hit Rate: Last 5'] > df['Hit Rate: Season'])
            ].sort_values('Weighted Hit Rate', ascending=False)
            st.dataframe(value_plays[['Player', 'Market Name', 'Line', 'Weighted Hit Rate', 'Hit Rate: Last 5']])

            # AI Strategic Insights
            generate_ai_insights(df)

        else:
            st.info("Upload a predictions CSV file to view analytics")




if __name__ == "__main__":
    create_dashboard()
