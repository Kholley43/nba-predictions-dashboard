import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime

# Load datasets
df = pd.read_csv('rw-prizepicks-predictions-2025-01-29.csv')
injuries_df = pd.read_csv('nba-injury-report.csv')

# Clean team names
df['Team'] = df['Team'].str.replace('@', '')
df['Opponent'] = df['Opponent'].str.replace('@', '')

def get_initial_candidates(df, injuries_df):
    healthy_players = df[~df['Player'].isin(injuries_df[injuries_df['Status'].isin(['Out', 'Game Time Decision'])]['Player'])]
    return healthy_players[
        (healthy_players['Hit Rate: Last 5'] >= 60) &
        (healthy_players['Hit Rate: Season'] >= 55) &
        (healthy_players['Hit Rate: Last 10'] >= 50) &
        (healthy_players['Hit Rate: Last 20'] >= 45) &
        (healthy_players['Weighted Hit Rate'] >= 45)
    ].copy()

def calculate_confidence(play):
    metrics = {
        'Recent Form': float(play['Hit Rate: Last 5']) * 0.25,
        'Season Rate': float(play['Hit Rate: Season']) * 0.20,
        'Last 10': float(play['Hit Rate: Last 10']) * 0.15,
        'Last 20': float(play['Hit Rate: Last 20']) * 0.15,
        'Weighted Rate': float(play['Weighted Hit Rate']) * 0.15,
        'Vs Opponent': float(play['Hit Rate: Vs Opponent'] if pd.notna(play['Hit Rate: Vs Opponent']) else play['Hit Rate: Season']) * 0.10
    }
    
    confidence = sum(metrics.values())
    return round(confidence, 2)

def get_elite_plays(df, injuries_df):
    print("Finding promising candidates...")
    candidates = get_initial_candidates(df, injuries_df)
    
    print("Validating top plays...")
    validated_plays = []
    
    for _, play in tqdm(candidates.iterrows(), total=len(candidates)):
        if get_espn_stats(play['Player']):
            confidence = calculate_confidence(play)
            play['Confidence'] = confidence
            validated_plays.append(play)
            store_prediction(play, confidence)
            if len(validated_plays) >= 10:
                break
    
    return pd.DataFrame(validated_plays).sort_values('Confidence', ascending=False).head(10)

def store_prediction(play, confidence):
    prediction_data = {
        'Date': datetime.now().strftime('%Y-%m-%d'),
        'Player': play['Player'],
        'Market': play['Market Name'],
        'Line': play['Line'],
        'Hit Rate: Last 5': play['Hit Rate: Last 5'],
        'Hit Rate: Last 10': play['Hit Rate: Last 10'],
        'Hit Rate: Last 20': play['Hit Rate: Last 20'],
        'Hit Rate: Season': play['Hit Rate: Season'],
        'Hit Rate: Vs Opponent': play['Hit Rate: Vs Opponent'],
        'Weighted Hit Rate': play['Weighted Hit Rate'],
        'Last 20 Outcomes': play['Hit Rate: Last 20 Outcomes'],
        'Prediction': 'Over' if confidence > 65 else 'Under',
        'Confidence': confidence,
        'Actual': None,
        'Result': None
    }
    
    pd.DataFrame([prediction_data]).to_csv('prediction_history.csv', mode='a', header=False, index=False)

# Display results with all metrics
print("\n🎯 TOP PREDICTIONS WITH FULL STATISTICAL ANALYSIS")
print("===============================================")
elite_plays = get_elite_plays(df, injuries_df)
for _, play in elite_plays.iterrows():
    print(f"\nPlayer: {play['Player']}")
    print(f"Market: {play['Market Name']} {play['Line']}")
    print(f"Recent Success: {play['Hit Rate: Last 5']}%")
    print(f"Last 10 Games: {play['Hit Rate: Last 10']}%")
    print(f"Last 20 Games: {play['Hit Rate: Last 20']}%")
    print(f"Season Rate: {play['Hit Rate: Season']}%")
    print(f"Vs Opponent: {play['Hit Rate: Vs Opponent']}%")
    print(f"Weighted Rate: {play['Weighted Hit Rate']}%")
    print(f"Last 20 Pattern: {play['Hit Rate: Last 20 Outcomes']}")
    print(f"Confidence: {play['Confidence']}%")
    print("-" * 50)

def get_espn_stats(player_name):
    """
    Fetches player statistics from ESPN
    """
    stats = {
        'points': 0,
        'rebounds': 0,
        'assists': 0,
        'steals': 0,
        'blocks': 0,
        'turnovers': 0,
        'minutes': 0
    }
    
    try:
        # ESPN API endpoint would go here
        # For now returning placeholder stats
        return stats
    except Exception as e:
        print(f"Error fetching ESPN stats: {e}")
        return stats
