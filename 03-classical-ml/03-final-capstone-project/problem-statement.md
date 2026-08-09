# Project Task: Sales Prediction Pipeline

## 1. Objective

Build a regression pipeline to predict sales, covering data cleaning, feature
engineering, model training with hyperparameter optimization, evaluation,
explainability, and deployment-ready artifact export.

---

## 2. Data Cleaning

- Perform final cleaning pass (data is largely clean; validate for nulls,
  duplicates, and inconsistent types).
- Drop the `total_sale_normalized` column (redundant / leaky feature).

---

## 3. Feature Engineering & Multicollinearity Check

- Encode `branch_name` (categorical, ~20 unique categories) using an
  appropriate encoding strategy (e.g., one-hot or target encoding — justify choice).
- Use a Random Forest (or correlation matrix + VIF) to assess multicollinearity
  among features.
  - **Threshold:** if pairwise correlation > 0.95, drop one feature from the
    pair or merge them into a single representative feature.

---

## 4. Train/Test Split

- Split the data **temporally** (e.g., train on earlier years, test on later
  years) rather than randomly — this respects the time-series nature of the data
  and avoids leakage.

---

## 5. Distribution Analysis & Scaling

- Plot distribution/density plots for numeric features to inspect **skewness**
  and **kurtosis**.
- Based on the distribution shape, apply an appropriate scaler per feature
  (e.g., `StandardScaler` for near-normal features, `RobustScaler` for skewed/
  outlier-heavy features).

---

## 6. Model Training

- Train a baseline set of regressors (e.g., Linear Regression, Random Forest,
  Gradient Boosting, etc.) for comparison.
- Train **XGBoost**, **CatBoost**, and **LightGBM**, using **Optuna** for
  hyperparameter tuning.
  - Do **not** hardcode hyperparameters — let Optuna search and report the
    optimized parameters per model.

---

## 7. Evaluation

Report the following metrics for every model on the test set:

- MAE (Mean Absolute Error)
- MSE (Mean Squared Error)
- RMSE (Root Mean Squared Error)
- R² Score

---

## 8. Deployment Artifacts

- Export fitted preprocessors (encoders, scalers) and trained models so they can be loaded directly into a FastAPI backend for inference.

---

## 9. Bonus: Explainability (XAI)

- Generate **SHAP** and **LIME** plots for the best-performing model.
- Include a feature importance visualization to interpret model behavior.
