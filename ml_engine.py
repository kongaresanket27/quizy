import numpy as np
from sklearn.linear_model import LinearRegression

def train_model(trend):
    if len(trend) < 2:
        return None

    X = np.array(range(len(trend))).reshape(-1, 1)
    y = np.array(trend)

    model = LinearRegression()
    model.fit(X, y)

    next_prediction = model.predict([[len(trend)]])
    return round(float(next_prediction[0]), 2)