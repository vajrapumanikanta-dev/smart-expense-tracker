import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta

from models.transaction import Transaction
from models.category import Category


class ExpenseForecaster:
    """
    Predicts upcoming expense trends using historical monthly data, linear regression (OLS),
    and rolling averages.
    """

    @staticmethod
    def forecast_monthly_expenses(user_id, horizon_months=3):
        """
        Calculates monthly historical expense totals and forecasts the next N months.
        Returns:
            {
                'historical': [{'month': 'YYYY-MM', 'amount': 1234.56, 'is_projected': False}, ...],
                'forecast': [{'month': 'YYYY-MM', 'amount': 1300.00, 'is_projected': True}, ...],
                'category_forecasts': {...},
                'trend_direction': 'increasing' | 'stable' | 'decreasing',
                'predicted_next_month': 1250.0,
                'avg_monthly_spending': 1180.0
            }
        """
        txs = Transaction.query.filter_by(user_id=user_id, transaction_type='expense').all()
        if not txs:
            return {
                'historical': [],
                'forecast': [],
                'category_forecasts': {},
                'trend_direction': 'stable',
                'predicted_next_month': 0.0,
                'avg_monthly_spending': 0.0
            }

        # Build monthly aggregations
        records = []
        for t in txs:
            records.append({
                'amount': float(t.amount),
                'date': t.transaction_date,
                'month_str': t.transaction_date.strftime('%Y-%m'),
                'category_id': t.category_id,
                'category_name': t.category.category_name if t.category else 'Other'
            })
        df = pd.DataFrame(records)

        # Monthly total
        monthly_df = df.groupby('month_str')['amount'].sum().reset_index().sort_values('month_str')
        
        # Ensure we have at least standard time series format
        historical_points = []
        for _, row in monthly_df.iterrows():
            historical_points.append({
                'month': row['month_str'],
                'amount': round(float(row['amount']), 2),
                'is_projected': False
            })

        avg_monthly = float(monthly_df['amount'].mean()) if len(monthly_df) > 0 else 0.0

        if len(monthly_df) < 2:
            # Not enough time periods for regression, return projection based on average
            last_month_str = monthly_df.iloc[-1]['month_str'] if len(monthly_df) > 0 else date.today().strftime('%Y-%m')
            last_date = datetime.strptime(last_month_str, '%Y-%m')
            
            forecast_points = []
            for i in range(1, horizon_months + 1):
                next_m = (last_date.month - 1 + i) % 12 + 1
                next_y = last_date.year + ((last_date.month - 1 + i) // 12)
                future_str = f"{next_y:04d}-{next_m:02d}"
                forecast_points.append({
                    'month': future_str,
                    'amount': round(avg_monthly, 2),
                    'is_projected': True
                })

            return {
                'historical': historical_points,
                'forecast': forecast_points,
                'category_forecasts': {},
                'trend_direction': 'stable',
                'predicted_next_month': round(avg_monthly, 2),
                'avg_monthly_spending': round(avg_monthly, 2)
            }

        # Fit linear regression model (OLS) over monthly index
        n_points = len(monthly_df)
        x_vals = np.arange(n_points, dtype=float)
        y_vals = monthly_df['amount'].values.astype(float)

        x_mean = np.mean(x_vals)
        y_mean = np.mean(y_vals)
        denom = np.sum((x_vals - x_mean) ** 2)
        slope = float(np.sum((x_vals - x_mean) * (y_vals - y_mean)) / denom) if denom != 0 else 0.0
        intercept = float(y_mean - slope * x_mean)

        if slope > 50:
            trend = 'increasing'
        elif slope < -50:
            trend = 'decreasing'
        else:
            trend = 'stable'

        # Generate future months
        last_month_str = monthly_df.iloc[-1]['month_str']
        last_date = datetime.strptime(last_month_str, '%Y-%m')
        
        forecast_points = []
        for i in range(1, horizon_months + 1):
            future_idx = n_points + i - 1
            pred_val = slope * future_idx + intercept
            # Prevent negative forecasts or unrealistically low drops
            pred_val = max(pred_val, avg_monthly * 0.4, 0.0)
            
            next_m = (last_date.month - 1 + i) % 12 + 1
            next_y = last_date.year + ((last_date.month - 1 + i) // 12)
            future_str = f"{next_y:04d}-{next_m:02d}"

            forecast_points.append({
                'month': future_str,
                'amount': round(float(pred_val), 2),
                'is_projected': True
            })

        # Category forecasts
        cat_forecasts = {}
        for cat_name, c_group in df.groupby('category_name'):
            c_monthly = c_group.groupby('month_str')['amount'].sum().reset_index()
            c_avg = float(c_monthly['amount'].mean())
            cat_forecasts[cat_name] = {
                'avg_monthly': round(c_avg, 2),
                'projected_next': round(max(0.0, c_avg * (1.0 + (slope / (avg_monthly or 1) * 0.5))), 2)
            }

        return {
            'historical': historical_points,
            'forecast': forecast_points,
            'category_forecasts': cat_forecasts,
            'trend_direction': trend,
            'predicted_next_month': forecast_points[0]['amount'] if forecast_points else round(avg_monthly, 2),
            'avg_monthly_spending': round(avg_monthly, 2)
        }
