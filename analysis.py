import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "car_listings"

print("Connecting to Supabase...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"Fetching all data from '{TABLE_NAME}'...")
response = supabase.table(TABLE_NAME).select("*").execute()

df = pd.DataFrame(response.data)

print("\n✅ Data loaded successfully into Pandas!")
print(f"Dataset shape (rows, columns): {df.shape}")
#print("\n--- First 5 rows of our dataset ---")
#print(df.head())

print("\n--- Dataset Info ---")
print(df.info())

print("\n--- Dataset Statistics ---")
print(df.describe())

# --- DATA CLEANING ---
df = df.dropna(subset=['power_hp'])
columns_to_drop = ['transmission', 'id', 'created_at', 'listing_link', 'car_id']
df = df.drop(columns=columns_to_drop)
df = df[df['fuel_type'] != 'Unknown']
print("\n--- Cleaned Dataset Info ---")
print(f"Final shape after data cleaning, ready for ML: {df.shape}")
#print(df.head())

# --- DATA VISUALIZATION (EDA) ---

#print("\nGenerating Price vs Mileage scatter plot...")

sns.set_theme(style="whitegrid")

plt.figure(figsize=(10, 6))
scatter = sns.scatterplot(
    data=df, 
    x='mileage', 
    y='price', 
    hue='fuel_type', # Colors the dots based on fuel type
    alpha=0.7,       # Makes the dots slightly transparent
    edgecolor=None
)

plt.title("BMW 3 Series: Price vs. Mileage", fontsize=16, fontweight='bold')
plt.xlabel("Mileage (km)", fontsize=12)
plt.ylabel("Price (EUR)", fontsize=12)
#plt.show()


df_ml = pd.get_dummies(df, columns=['make', 'fuel_type', 'model'], drop_first=True)

print("--- Final Dataset for ML ---")
print(f"Shape: {df_ml.shape}")
print(df_ml.head())

# --- MACHINE LEARNING: RANDOM FOREST ---
print("\nTraining the AI Model...")

y = df_ml['price']
X = df_ml.drop(columns=['price'])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("--- AI Model Results ---")
print(f"Mean Absolute Error (MAE): € {mae:.2f}")
print(f"Accuracy (R-Squared): {r2 * 100:.2f}%")

print("\n--- Real vs Predicted (First 3 Test Cars) ---")
for i in range(3):
    real_price = y_test.iloc[i]
    predicted_price = predictions[i]
    print(f"Car {i+1} | Real: €{real_price} | AI Predicted: €{predicted_price:.0f} | Difference: €{abs(real_price - predicted_price):.0f}")

# --- EXPORTING THE AI MODEL (for future use) ---
print("\nSaving the AI model and features for future use...")
joblib.dump(model, 'bmw3_price_model.pkl')
joblib.dump(list(X.columns), 'model_columns.pkl')
print("✅ Model successfully saved! You can now use it in the simulator.")