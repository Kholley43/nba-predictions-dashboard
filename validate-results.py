import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_game_stats(player_name, market):
    formatted_name = player_name.lower().replace(' ', '-')
    url = f"https://www.espn.com/nba/player/gamelog/_/name/{formatted_name}/season/2024"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Get most recent game stats
        stats_table = soup.find('table', class_='Table')
        latest_game = stats_table.find_all('tr')[1]  # First row after header
        
        stat_mapping = {
            'Points': 'PTS',
            'Rebounds': 'REB',
            'Assists': 'AST',
            'PTS+REB': ['PTS', 'REB'],
            'PTS+AST': ['PTS', 'AST'],
            'REB+AST': ['REB', 'AST'],
            'PTS+REB+AST': ['PTS', 'REB', 'AST']
        }
        
        return extract_stats(latest_game, stat_mapping[market])
    except:
        return None

def extract_stats(game_row, stat_categories):
    if isinstance(stat_categories, list):
        total = 0
        for cat in stat_categories:
            total += float(game_row.find('td', {'data-stat': cat.lower()}).text)
        return total
    else:
        return float(game_row.find('td', {'data-stat': stat_categories.lower()}).text)

def update_results():
    predictions = pd.read_csv('prediction_history.csv')
    today_date = datetime.now().strftime('%Y-%m-%d')
    pending_predictions = predictions[
        (predictions['Date'] == today_date) & 
        (predictions['Actual'].isnull())
    ]
    
    print("\n📊 UPDATING PREDICTION RESULTS")
    print("============================")
    
    for _, pred in pending_predictions.iterrows():
        actual_stat = get_game_stats(pred['Player'], pred['Market'])
        if actual_stat:
            predictions.loc[predictions.index == _, 'Actual'] = actual_stat
            result = (actual_stat > float(pred['Line'])) if pred['Prediction'] == 'Over' else (actual_stat < float(pred['Line']))
            predictions.loc[predictions.index == _, 'Result'] = result
            
            print(f"\nPlayer: {pred['Player']}")
            print(f"Market: {pred['Market']} {pred['Line']}")
            print(f"Prediction: {pred['Prediction']}")
            print(f"Actual: {actual_stat}")
            print(f"Result: {'✅ Correct' if result else '❌ Incorrect'}")
    
    predictions.to_csv('prediction_history.csv', index=False)
    
    # Calculate and display accuracy metrics
    results = predictions[predictions['Result'].notna()]
    total_predictions = len(results)
    correct_predictions = results['Result'].sum()
    accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
    
    print("\n📈 OVERALL PERFORMANCE")
    print("====================")
    print(f"Total Predictions: {total_predictions}")
    print(f"Correct Predictions: {correct_predictions}")
    print(f"Accuracy: {accuracy:.1f}%")

if __name__ == "__main__":
    update_results()
