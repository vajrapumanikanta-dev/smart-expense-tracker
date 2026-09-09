import calendar
from datetime import date, datetime, timedelta
from models.transaction import Transaction
from models.budget import Budget
from models.category import Category
from models.recurring import RecurringExpense


class FinancialRecommender:
    """
    AI & Algorithmic advisory engine for budget recommendations, overspending prediction,
    subscription discovery, and duplicate charge detection.
    """

    @staticmethod
    def predict_overspending(user_id):
        """
        Calculates month-to-date spending velocity versus active budgets and days remaining.
        Flags categories at risk of exceeding their limit before the month ends.
        """
        today = date.today()
        current_year = today.year
        current_month = today.month
        
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        days_passed = max(today.day, 1)
        progress_ratio = days_passed / float(days_in_month)

        budgets = Budget.query.filter_by(user_id=user_id, month=current_month, year=current_year).all()
        if not budgets:
            return []

        start_date = date(current_year, current_month, 1)
        txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= today
        ).all()

        spent_by_cat = {}
        for t in txs:
            spent_by_cat[t.category_id] = spent_by_cat.get(t.category_id, 0.0) + float(t.amount)

        alerts = []
        for b in budgets:
            budget_amt = float(b.amount)
            if budget_amt <= 0:
                continue

            cat_name = b.category.category_name if b.category else 'Overall Monthly Budget'
            spent = spent_by_cat.get(b.category_id, 0.0)
            spent_pct = (spent / budget_amt) * 100.0

            # Projected end-of-month spend based on velocity
            projected_spend = (spent / progress_ratio) if progress_ratio > 0 else spent
            projected_pct = (projected_spend / budget_amt) * 100.0

            if spent > budget_amt:
                alerts.append({
                    'category_name': cat_name,
                    'category_id': b.category_id,
                    'status': 'exceeded',
                    'budget': budget_amt,
                    'spent': spent,
                    'projected': round(projected_spend, 2),
                    'spent_pct': round(spent_pct, 1),
                    'severity': 'danger',
                    'message': f"You have already exceeded your {cat_name} budget (${budget_amt:,.2f}) by ${spent - budget_amt:,.2f}."
                })
            elif projected_spend > budget_amt and spent_pct > (progress_ratio * 100 * 1.15):
                alerts.append({
                    'category_name': cat_name,
                    'category_id': b.category_id,
                    'status': 'at_risk',
                    'budget': budget_amt,
                    'spent': spent,
                    'projected': round(projected_spend, 2),
                    'spent_pct': round(spent_pct, 1),
                    'severity': 'warning',
                    'message': f"At your current spending pace, you will reach ~${projected_spend:,.2f} ({round(projected_pct)}% of limit) in {cat_name} by month-end."
                })

        return alerts

    @staticmethod
    def generate_budget_recommendations(user_id):
        """
        Analyzes historical monthly averages and recommends balanced category budgets
        aligned with the 50/30/20 rule (Needs, Wants, Savings).
        """
        today = date.today()
        three_months_ago = today - timedelta(days=90)

        txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= three_months_ago
        ).all()

        if not txs:
            return []

        cat_totals = {}
        for t in txs:
            cat_name = t.category.category_name if t.category else 'Other'
            cat_totals[cat_name] = cat_totals.get(cat_name, 0.0) + float(t.amount)

        # Average per month across past 3 months
        needs_cats = {'Housing & Rent', 'Groceries', 'Utilities & Bills', 'Healthcare & Medical', 'Transportation & Fuel'}
        recommendations = []
        for cat_name, total in cat_totals.items():
            monthly_avg = total / 3.0
            # Target recommendation: 5-10% optimization cushion
            recommended_budget = round(monthly_avg * 0.95, -1)  # Round to nearest 10
            if recommended_budget < 10:
                recommended_budget = round(monthly_avg, 2)

            rule_type = 'Needs' if cat_name in needs_cats else ('Savings' if 'saving' in cat_name.lower() or 'invest' in cat_name.lower() else 'Wants')
            reason_str = f"Based on your average spending of ${monthly_avg:,.2f}/mo over the last 90 days with a 5% optimization target."

            recommendations.append({
                'category_name': cat_name,
                'monthly_avg': round(monthly_avg, 2),
                'historical_avg': round(monthly_avg, 2),
                'recommended_budget': recommended_budget,
                'category_type_rule': rule_type,
                'potential_savings': max(0.0, round(monthly_avg - recommended_budget, 2)),
                'reason': reason_str,
                'rationale': reason_str
            })

        recommendations.sort(key=lambda x: x['monthly_avg'], reverse=True)
        return recommendations

    @staticmethod
    def detect_subscriptions(user_id):
        """
        Scans transaction history to identify recurring payments/subscriptions
        that are not yet tracked in the recurring expenses table.
        """
        txs = Transaction.query.filter_by(user_id=user_id, transaction_type='expense').order_by(Transaction.transaction_date.desc()).all()
        if len(txs) < 4:
            return []

        existing_recurring = {r.name.lower() for r in RecurringExpense.query.filter_by(user_id=user_id).all()}
        
        # Group by description and amount
        groups = {}
        for t in txs:
            desc = (t.description or '').strip()
            if not desc:
                continue
            key = (desc.lower(), round(float(t.amount), 2))
            if key not in groups:
                groups[key] = []
            groups[key].append(t)

        detected = []
        for (desc_lower, amt), item_list in groups.items():
            if len(item_list) >= 2:
                # Check if already added
                if any(r_name in desc_lower or desc_lower in r_name for r_name in existing_recurring):
                    continue

                dates = sorted([t.transaction_date for t in item_list])
                intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                avg_interval = sum(intervals) / len(intervals)

                freq = "Monthly" if 25 <= avg_interval <= 35 else ("Weekly" if 5 <= avg_interval <= 9 else "Yearly" if 350 <= avg_interval <= 380 else None)
                if freq or len(item_list) >= 3:
                    sample_tx = item_list[0]
                    detected.append({
                        'name': sample_tx.description,
                        'amount': amt,
                        'estimated_frequency': freq or 'Monthly',
                        'occurrences': len(item_list),
                        'category_name': sample_tx.category.category_name if sample_tx.category else 'Subscriptions',
                        'category_id': sample_tx.category_id,
                        'account_id': sample_tx.account_id,
                        'last_date': sample_tx.transaction_date.strftime('%Y-%m-%d')
                    })

        return detected

    @staticmethod
    def detect_duplicates(user_id):
        """
        Detects potential accidental duplicate charges within 48 hours for the same amount and description.
        """
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        
        txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= thirty_days_ago
        ).order_by(Transaction.transaction_date.desc()).all()

        duplicates = []
        seen = set()

        for i in range(len(txs)):
            for j in range(i + 1, len(txs)):
                t1 = txs[i]
                t2 = txs[j]
                if t1.id in seen or t2.id in seen:
                    continue

                if (t1.amount == t2.amount and 
                    t1.transaction_type == t2.transaction_type and 
                    t1.account_id == t2.account_id):
                    
                    day_diff = abs((t1.transaction_date - t2.transaction_date).days)
                    desc1 = (t1.description or '').strip().lower()
                    desc2 = (t2.description or '').strip().lower()

                    if day_diff <= 2 and (desc1 == desc2 or desc1 in desc2 or desc2 in desc1):
                        seen.add(t1.id)
                        seen.add(t2.id)
                        duplicates.append({
                            'amount': float(t1.amount),
                            'description': t1.description,
                            'transaction_1': t1.to_dict(),
                            'transaction_2': t2.to_dict(),
                            'days_apart': day_diff
                        })

        return duplicates
