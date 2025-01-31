import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# Read the CSV
df = pd.read_csv('rw-prizepicks-predictions-2025-01-29.csv')

# Convert percentage strings to floats and handle missing values
numeric_columns = [
    'Weighted Hit Rate', 
    'Hit Rate: Last 5',
    'Hit Rate: Last 10', 
    'Hit Rate: Last 20',
    'Hit Rate: Season',
    'Hit Rate: Previous Season',
    'Hit Rate: Vs Opponent'
]

# Replace '-' with NaN and convert to numeric
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col].replace('-', np.nan))

# Fill missing values with column mean
df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].mean())

# Calculate volatility score
df['Volatility'] = df['Hit Rate: Last 20 Outcomes'].apply(
    lambda x: sum([abs(int(str(x)[i]) - int(str(x)[i-1])) for i in range(1, len(str(x)))]) / 19 * 100
)

# Group by market type performance
df['Market_Success'] = df.groupby('Market Name')['Hit Rate: Season'].transform('mean')

# Calculate opponent impact score
df['Opponent_Impact'] = df.apply(
    lambda row: row['Hit Rate: Vs Opponent'] - row['Hit Rate: Season'] 
    if pd.notnull(row['Hit Rate: Vs Opponent']) else 0, axis=1
)

# Analyze streak quality with recency weighting
df['Streak_Quality'] = df['Hit Rate: Last 20 Outcomes'].apply(
    lambda x: sum([int(i)*(1.1**idx) for idx, i in enumerate(str(x)[::-1])])
)

# Add enhanced trend analysis
df['Recent_Trend'] = df['Hit Rate: Last 20 Outcomes'].apply(
    lambda x: sum([int(i)*weight for i, weight in zip(str(x)[-5:], [1.2,1.4,1.6,1.8,2.0])]) / 8 * 100
)

# Update the weighted recent performance calculation
df['Weighted_Recent'] = (
    df['Hit Rate: Last 5'] * 0.6 +    # Increase weight of last 5 games
    df['Hit Rate: Last 10'] * 0.25 +   # Adjust mid-term weight
    df['Hit Rate: Last 20'] * 0.1 +    # Reduce longer-term influence
    df['Hit Rate: Season'] * 0.05      # Minimal season-long weight
)

# Enhance recent trend analysis
df['Recent_Trend'] = df['Hit Rate: Last 20 Outcomes'].apply(
    lambda x: sum([int(i)*weight for i, weight in zip(str(x)[-5:], [2.5,2.0,1.5,1.2,1.0])]) / 8 * 100
)

# Create composite scoring
df['Composite_Score'] = (
    df['Weighted_Recent'] * 0.3 +
    df['Recent_Trend'] * 0.3 +
    df['Market_Success'] * 0.2 +
    df['Opponent_Impact'] * 0.2
)

# Add streak analysis
df['Current_Streak'] = df['Hit Rate: Last 20 Outcomes'].apply(
    lambda x: len(max(str(x).split('0'))) if '1' in str(x) else 0
)

# Calculate consistency score with weighted standard deviation
df['Consistency'] = df.apply(
    lambda row: np.std([
        row['Hit Rate: Last 5'],
        row['Hit Rate: Last 10'],
        row['Hit Rate: Last 20'],
        row['Weighted_Recent']
    ]), axis=1
)

# Prepare enhanced features for model
X = df[numeric_columns + [
    'Recent_Trend', 'Consistency', 'Weighted_Recent', 'Current_Streak',
    'Volatility', 'Market_Success', 'Opponent_Impact', 'Streak_Quality',
    'Composite_Score'
]]
y = df['Hit Rate: Last 20 Outcomes'].apply(lambda x: [int(i) for i in str(x)])
y = pd.Series([sum(outcomes)/len(outcomes) > 0.5 for outcomes in y])

# Train model with enhanced parameters
model = RandomForestClassifier(
    n_estimators=300,
    random_state=42,
    class_weight='balanced',
    max_depth=10
)
model.fit(X, y)

# Get predictions
predictions = model.predict_proba(X)
df['ML_Score'] = predictions[:,1] * 100 if predictions.shape[1] > 1 else predictions[:,0] * 100

# Calculate median streak quality
median_streak_quality = df['Streak_Quality'].median()
# Relaxed but still effective quality filters
high_quality_picks = df[
    (df['Consistency'] < 15) &  # From 12 to 15
    (df['Recent_Trend'] > 50) &  # From 60 to 50
    (df['Hit Rate: Season'] > 40) &  # From 45 to 40
    (df['Current_Streak'] >= 2) &  # From 4 to 2
    (df['Weighted_Recent'] > 45) &  # From 50 to 45
    (df['Volatility'] < 45) &  # From 35 to 45
    (df['Composite_Score'] > 45) &  # From 50 to 45
    (df['Market_Success'] > 40) &  # From 45 to 40
    (df['Opponent_Impact'].abs() > 5) &  # From 10 to 5
    ((df['ML_Score'] > 90) | (df['ML_Score'] < 10))  # From 95/5 to 90/10
]
# Market-specific filtering
points_picks = high_quality_picks[high_quality_picks['Market Name'].str.contains('Points', na=False)]
rebounds_picks = high_quality_picks[high_quality_picks['Market Name'].str.contains('Rebounds', na=False)]
assists_picks = high_quality_picks[high_quality_picks['Market Name'].str.contains('Assists', na=False)]

# Combine filtered picks
final_picks = pd.concat([points_picks, rebounds_picks, assists_picks])

# Sort and display results with additional metrics
results = final_picks[[
    'Player', 'Market Name', 'Line', 'ML_Score',
    'Recent_Trend', 'Consistency', 'Current_Streak', 'Weighted_Recent',
    'Volatility', 'Market_Success', 'Opponent_Impact', 'Composite_Score',
    'Streak_Quality'
]]
# Format the results for better readability
pd.set_option('display.float_format', lambda x: '%.2f' % x)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Create a cleaner display format
def format_results(df):
    formatted_df = df.copy()
    formatted_df['ML_Score'] = formatted_df['ML_Score'].round(2)
    formatted_df['Recent_Trend'] = formatted_df['Recent_Trend'].round(1)
    formatted_df['Consistency'] = formatted_df['Consistency'].round(2)
    formatted_df['Weighted_Recent'] = formatted_df['Weighted_Recent'].round(1)
    formatted_df['Volatility'] = formatted_df['Volatility'].round(1)
    formatted_df['Market_Success'] = formatted_df['Market_Success'].round(1)
    formatted_df['Opponent_Impact'] = formatted_df['Opponent_Impact'].round(1)
    formatted_df['Composite_Score'] = formatted_df['Composite_Score'].round(1)
    formatted_df['Streak_Quality'] = formatted_df['Streak_Quality'].round(2)
    return formatted_df

# Display formatted results
formatted_results = format_results(results)
# Add recent performance verification
df['Recent_Average'] = df['Hit Rate: Last 5'] * 0.8 + df['Hit Rate: Last 10'] * 0.2

# Update filtering criteria
overs = formatted_results[
    (formatted_results['ML_Score'] > 90) &
    (formatted_results['Recent_Average'] > 55) &  # Stricter recent performance requirement
    (formatted_results['Weighted_Recent'] > 50) &
    (formatted_results['Volatility'] < 40) &      # Lower volatility threshold
    (formatted_results['Market_Success'] > 45)
]

# Add actual performance check
def verify_recent_performance(row):
    last_5_outcomes = str(row['Hit Rate: Last 20 Outcomes'])[-5:]
    return sum(int(x) for x in last_5_outcomes) >= 3  # Must hit in at least 3 of last 5

overs = overs[overs.apply(verify_recent_performance, axis=1)]

# For UNDERS (using available metrics)
unders = formatted_results[
    (formatted_results['ML_Score'] < 35) &
    (formatted_results['Recent_Trend'] < 40) &
    (formatted_results['Weighted_Recent'] < 45) &
    (formatted_results['Current_Streak'] <= 2) &
    (formatted_results['Volatility'] < 50) &
    (formatted_results['Composite_Score'] < 45)
]

print("\n🔥 TOP RECOMMENDED OVERS 🔥")
print("=====================================")
high_prob = overs.sort_values('ML_Score', ascending=False).head(10)
for _, row in high_prob.iterrows():
    print(f"\nPlayer: {row['Player']}")
    print(f"Market: {row['Market Name']} OVER {row['Line']}")
    print(f"ML Score: {row['ML_Score']}%")
    print(f"Streak: {row['Current_Streak']} games")
    print(f"Recent Trend: {row['Recent_Trend']}%")
    print(f"Composite Score: {row['Composite_Score']}")
    print("-------------------------------------")

print("\n❄️ TOP RECOMMENDED UNDERS ❄️")
print("=====================================")
low_prob = unders.sort_values('ML_Score', ascending=False).head(10)
for _, row in low_prob.iterrows():
    print(f"\nPlayer: {row['Player']}")
    print(f"Market: {row['Market Name']} UNDER {row['Line']}")
    print(f"ML Score: {row['ML_Score']}%")
    print(f"Streak: {row['Current_Streak']} games")
    print(f"Recent Trend: {row['Recent_Trend']}%")
    print(f"Composite Score: {row['Composite_Score']}")
    print("-------------------------------------")
