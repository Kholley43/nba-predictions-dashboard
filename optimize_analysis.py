import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import streamlit as st

@st.cache_data
def load_and_preprocess_data(df):
    """Cache the initial data loading and preprocessing"""
    return df.copy()

def calculate_market_metrics(df, market_name):
    """Calculate market-specific metrics"""
    market_data = df[df['Market Name'] == market_name]
    return {
        'hit_rate': market_data['Weighted Hit Rate'].mean(),
        'volume': len(market_data),
        'trends': market_data['Hit Rate: Last 5'].mean()
    }

def parallel_player_analysis(df, players):
    """Run player analysis in parallel"""
    with ThreadPoolExecutor() as executor:
        results = executor.map(lambda p: analyze_single_player(df, p), players)
    return pd.DataFrame(list(results))

def analyze_single_player(df, player):
    """Analyze metrics for a single player"""
    player_data = df[df['Player'] == player]
    return {
        'player': player,
        'weighted_rate': player_data['Weighted Hit Rate'].mean(),
        'recent_form': player_data['Hit Rate: Last 5'].mean(),
        'markets': player_data['Market Name'].unique().tolist()
    }

def optimized_analysis(df):
    # Cache the preprocessed data
    cached_df = load_and_preprocess_data(df)
    
    # Process market calculations
    market_metrics = {
        market: calculate_market_metrics(cached_df, market) 
        for market in cached_df['Market Name'].unique()
    }
    
    # Process player analysis
    players = cached_df['Player'].unique()
    player_metrics = parallel_player_analysis(cached_df, players)
    
    return player_metrics, market_metrics
