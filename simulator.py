import joblib
import pandas as pd

ml_model = joblib.load('bmw3_price_model.pkl')
model_columns = joblib.load('model_columns.pkl')

print("Car details:")
car_model = input("Model: ")
model_year = int(input("Year of fabrication: "))
mileage = int(input("Mileage (km):"))
hp = float(input("HP: "))
fuel_type = input("Fuel Type: ")

car_data = {
    "make": "Bmw",
    "model": car_model,
    "mileage": mileage,
    "model_year": model_year,
    "power_hp": hp,
    "fuel_type": fuel_type,
    }

df_user = pd.DataFrame([car_data])
df_encoded = pd.get_dummies(df_user, columns=['make', 'model', 'fuel_type'])
df_final = df_encoded.reindex(columns=model_columns, fill_value=False)
predicted_price = ml_model.predict(df_final)[0]
print(f"Estimated price: €{predicted_price:,.2f}")