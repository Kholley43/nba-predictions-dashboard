import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_performance(predictions_df):
    """
    Analyzes prediction performance metrics
    """
    total_predictions = len(predictions_df)
    correct_predictions = len(predictions_df[predictions_df['result'] == 'Hit'])
    accuracy = (correct_predictions / total_predictions) * 100 if total_predictions > 0 else 0
    
    return {
        'total_predictions': total_predictions,
        'correct_predictions': correct_predictions,
        'accuracy': accuracy
    }

def analyze_prediction_history():
    history = pd.read_csv('prediction_history.csv')
   
    # Market type analysis
    print("\n📊 MARKET PERFORMANCE BREAKDOWN")
    print("=============================")
    market_stats = history.groupby('Market')['Result'].agg(['count', 'mean'])
    market_stats.columns = ['Total Predictions', 'Win Rate']
    market_stats['Win Rate'] = market_stats['Win Rate'] * 100
    print(market_stats.sort_values('Win Rate', ascending=False))
   
    # Confidence correlation
    print("\n🎯 CONFIDENCE SCORE EFFECTIVENESS")
    print("==============================")
    confidence_bins = pd.qcut(history['Confidence'], q=4)
    confidence_analysis = history.groupby(confidence_bins)['Result'].mean() * 100
    print(confidence_analysis)
   
    # Visualize trends
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=history, x='Date', y='Result', rolling=7)
    plt.title('Prediction Accuracy Trend')
    plt.savefig('accuracy_trend.png')

if __name__ == "__main__":
    analyze_performance()
