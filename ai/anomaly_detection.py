import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from models.transaction import Transaction
from models.category import Category


class AnomalyDetector:
    """
    Detects unusual transactions using statistical Z-score/IQR and multi-dimensional outlier scoring
    based on historical spending patterns.
    """

    @staticmethod
    def detect_anomalies_for_user(user_id, contamination=0.05):
        """
        Scans all expense transactions for a user and identifies statistical and ML anomalies.
        Returns a list of flagged transactions with reasons and scores.
        """
        transactions = Transaction.query.filter_by(user_id=user_id, transaction_type='expense').order_by(Transaction.transaction_date.desc()).all()
        if not transactions or len(transactions) < 3:
            return []

        # Convert to records
        data = []
        for t in transactions:
            cat_name = t.category.category_name if t.category else 'Uncategorized'
            data.append({
                'id': t.id,
                'amount': float(t.amount),
                'category_id': t.category_id or 0,
                'category_name': cat_name,
                'date': t.transaction_date,
                'description': t.description or '',
                'day_of_week': t.transaction_date.weekday(),
                'day_of_month': t.transaction_date.day
            })
        df = pd.DataFrame(data)

        # 1. Statistical Per-Category Analysis (Z-score / IQR / MAD)
        anomalies = []
        cat_stats = {}
        for cat_id, group in df.groupby('category_id'):
            amounts = group['amount'].values
            mean_amt = float(np.mean(amounts))
            std_amt = float(np.std(amounts)) if len(amounts) > 1 else 0.0
            median_amt = float(np.median(amounts))
            
            if len(amounts) >= 4:
                q75, q25 = np.percentile(amounts, [75, 25])
                iqr = float(q75 - q25)
            else:
                iqr = float(std_amt)
                q75 = mean_amt

            upper_bound = float(q75 + 1.5 * iqr if iqr > 0 else mean_amt * 2.2)
            cat_stats[cat_id] = {
                'mean': mean_amt,
                'std': std_amt,
                'median': median_amt,
                'upper_bound': upper_bound,
                'count': len(group)
            }

        # 2. Multi-feature outlier scoring (amount vs overall percentile)
        overall_p90 = float(df['amount'].quantile(0.90))
        df['ml_anomaly'] = df['amount'] > (overall_p90 * 1.5)

        for idx, row in df.iterrows():
            cat_id = row['category_id']
            stats = cat_stats.get(cat_id)
            is_anomaly = False
            reasons = []

            # Check IQR / Upper Bound
            if stats and stats['count'] >= 2:
                if row['amount'] > stats['upper_bound'] and row['amount'] > (stats['mean'] * 1.8):
                    is_anomaly = True
                    multiplier = round(row['amount'] / (stats['mean'] or 1), 1)
                    reasons.append(f"Amount (${row['amount']:,.2f}) is {multiplier}x the average (${stats['mean']:,.2f}) in '{row['category_name']}'")

            # Check ML / Multi-feature outlier
            if row['ml_anomaly'] and (row['amount'] > df['amount'].quantile(0.80)):
                is_anomaly = True
                reasons.append("Unusual multi-feature spending pattern detected by outlier engine")

            if is_anomaly:
                anomalies.append({
                    'transaction_id': int(row['id']),
                    'amount': float(row['amount']),
                    'description': row['description'],
                    'category_name': row['category_name'],
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'reasons': reasons,
                    'severity': 'high' if row['amount'] > (stats['mean'] * 2.8 if stats else 1000) else 'medium'
                })

        return anomalies

    @staticmethod
    def evaluate_single_transaction(user_id, amount, category_id, description=""):
        """
        Quickly test if an individual incoming transaction is anomalous before saving.
        """
        past_txs = Transaction.query.filter_by(
            user_id=user_id,
            category_id=category_id,
            transaction_type='expense'
        ).all()

        if len(past_txs) < 2:
            return False, "Not enough historical category data for anomaly evaluation."

        amounts = [float(t.amount) for t in past_txs]
        mean_amt = float(np.mean(amounts))
        std_amt = float(np.std(amounts)) if len(amounts) > 1 else 0.0

        if amount > (mean_amt + 2.5 * std_amt) or (amount > mean_amt * 2.5 and amount > 50):
            multiplier = round(amount / (mean_amt or 1), 1)
            return True, f"This transaction is {multiplier}x higher than your average of ${mean_amt:,.2f} for this category."

        return False, "Transaction is within normal spending bounds."
