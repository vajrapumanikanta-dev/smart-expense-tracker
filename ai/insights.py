import calendar
from datetime import date, datetime, timedelta
from models.transaction import Transaction
from models.budget import Budget
from models.category import Category
from models.account import Account
from models.recurring import RecurringExpense
from models.goal import FinancialGoal


class FinancialInsightsEngine:
    """
    Computes comprehensive financial health score (0-100), monthly summary intelligence,
    and granular spending pattern analysis.
    """

    @staticmethod
    def calculate_financial_health_score(user_id):
        """
        Calculates an algorithmic 0-100 Financial Health Score with 4 distinct pillars:
        1. Savings Rate Score (0 - 35 points) - Target: 20%+ of income saved
        2. Budget Adherence Score (0 - 30 points) - Spending within budgeted boundaries
        3. Recurring Burden Ratio (0 - 20 points) - Recurring fixed commitments < 35% of income
        4. Financial Goal Progress (0 - 15 points) - Active goals and milestone pacing
        """
        today = date.today()
        current_year = today.year
        current_month = today.month
        start_of_month = date(current_year, current_month, 1)

        # 1. Income & Expenses for current month
        txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= today
        ).all()

        month_income = sum(float(t.amount) for t in txs if t.transaction_type == 'income')
        month_expense = sum(float(t.amount) for t in txs if t.transaction_type == 'expense')

        # Fallback to past 60 days if current month data is sparse
        if month_income == 0 and month_expense == 0:
            sixty_days_ago = today - timedelta(days=60)
            past_txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= sixty_days_ago
            ).all()
            month_income = sum(float(t.amount) for t in past_txs if t.transaction_type == 'income') / 2.0
            month_expense = sum(float(t.amount) for t in past_txs if t.transaction_type == 'expense') / 2.0

        # Pillar 1: Savings Rate (35 pts max)
        savings_amount = max(0.0, month_income - month_expense)
        savings_rate = (savings_amount / month_income) * 100 if month_income > 0 else (15.0 if month_expense == 0 else 0.0)
        
        if savings_rate >= 30:
            savings_score = 35
        elif savings_rate >= 20:
            savings_score = 28 + (savings_rate - 20) * 0.7
        elif savings_rate >= 10:
            savings_score = 18 + (savings_rate - 10) * 1.0
        elif savings_rate > 0:
            savings_score = savings_rate * 1.8
        else:
            savings_score = 0

        # Pillar 2: Budget Adherence (30 pts max)
        budgets = Budget.query.filter_by(user_id=user_id, month=current_month, year=current_year).all()
        if budgets:
            total_budget = sum(float(b.amount) for b in budgets)
            spent_pct = (month_expense / total_budget) * 100 if total_budget > 0 else 100
            
            # Expected progress ratio
            days_in_month = calendar.monthrange(current_year, current_month)[1]
            expected_pct = (today.day / days_in_month) * 100

            if spent_pct <= expected_pct:
                budget_score = 30
            elif spent_pct <= expected_pct * 1.2:
                budget_score = 22
            elif spent_pct <= 100:
                budget_score = 15
            else:
                budget_score = max(0, 10 - int((spent_pct - 100) / 5))
        else:
            budget_score = 20  # Neutral baseline if no budget configured

        # Pillar 3: Recurring Burden (20 pts max)
        recurring = RecurringExpense.query.filter_by(user_id=user_id, active=True).all()
        monthly_recurring_sum = 0.0
        for r in recurring:
            amt = float(r.amount)
            if r.frequency == 'Monthly':
                monthly_recurring_sum += amt
            elif r.frequency == 'Weekly':
                monthly_recurring_sum += amt * 4.33
            elif r.frequency == 'Yearly':
                monthly_recurring_sum += amt / 12.0

        if month_income > 0:
            recurring_burden_ratio = (monthly_recurring_sum / month_income) * 100
            if recurring_burden_ratio <= 30:
                recurring_score = 20
            elif recurring_burden_ratio <= 45:
                recurring_score = 14
            elif recurring_burden_ratio <= 60:
                recurring_score = 8
            else:
                recurring_score = 3
        else:
            recurring_score = 15

        # Pillar 4: Financial Goal Progress (15 pts max)
        goals = FinancialGoal.query.filter_by(user_id=user_id, status='In Progress').all()
        if goals:
            avg_progress = sum(g.progress_percentage for g in goals) / len(goals)
            goal_score = min(15, (avg_progress / 100) * 15 + 5)
        else:
            goal_score = 10

        # Total Composite Score
        total_score = int(round(savings_score + budget_score + recurring_score + goal_score))
        total_score = max(0, min(100, total_score))

        # Grade Label
        if total_score >= 85:
            grade = "Excellent"
            grade_color = "#10b981"
        elif total_score >= 70:
            grade = "Good"
            grade_color = "#3b82f6"
        elif total_score >= 50:
            grade = "Fair"
            grade_color = "#f59e0b"
        else:
            grade = "Needs Attention"
            grade_color = "#ef4444"

        return {
            'score': total_score,
            'grade': grade,
            'grade_color': grade_color,
            'savings_rate': round(savings_rate, 1),
            'savings_score': round(savings_score, 1),
            'budget_score': round(budget_score, 1),
            'recurring_score': round(recurring_score, 1),
            'goal_score': round(goal_score, 1),
            'monthly_income': round(month_income, 2),
            'monthly_expense': round(month_expense, 2),
            'monthly_savings': round(savings_amount, 2),
            'monthly_recurring': round(monthly_recurring_sum, 2)
        }

    @staticmethod
    def generate_monthly_report(user_id, year=None, month=None):
        """
        Generates a comprehensive monthly executive financial report.
        """
        today = date.today()
        year = year or today.year
        month = month or today.month

        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ).all()

        income_txs = [t for t in txs if t.transaction_type == 'income']
        expense_txs = [t for t in txs if t.transaction_type == 'expense']

        total_income = sum(float(t.amount) for t in income_txs)
        total_expense = sum(float(t.amount) for t in expense_txs)
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0

        # Category Breakdown
        cat_map = {}
        for t in expense_txs:
            cat_name = t.category.category_name if t.category else 'Uncategorized'
            cat_map[cat_name] = cat_map.get(cat_name, 0.0) + float(t.amount)

        sorted_cats = sorted(cat_map.items(), key=lambda x: x[1], reverse=True)
        top_categories = [{'name': name, 'amount': round(amt, 2), 'pct': round(amt / total_expense * 100, 1) if total_expense > 0 else 0} for name, amt in sorted_cats[:5]]

        # Compare with previous month
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_start = date(prev_year, prev_month, 1)
        prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
        prev_end = date(prev_year, prev_month, prev_last_day)

        prev_txs = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date <= prev_end
        ).all()
        prev_total_expense = sum(float(t.amount) for t in prev_txs)
        expense_change_pct = ((total_expense - prev_total_expense) / prev_total_expense * 100) if prev_total_expense > 0 else 0.0

        needs_cats = {'Housing & Rent', 'Groceries', 'Utilities & Bills', 'Healthcare & Medical', 'Transportation & Fuel', 'Education'}
        needs_amt = sum(float(t.amount) for t in expense_txs if t.category and t.category.category_name in needs_cats)
        wants_amt = sum(float(t.amount) for t in expense_txs if not (t.category and t.category.category_name in needs_cats))
        savings_amt = max(0.0, net_savings)

        income_base = total_income if total_income > 0 else (total_expense if total_expense > 0 else 1.0)
        needs_pct = round((needs_amt / income_base) * 100, 1)
        wants_pct = round((wants_amt / income_base) * 100, 1)
        savings_pct = round((savings_amt / income_base) * 100, 1) if total_income > 0 else 0.0

        rule_50_30_20 = {
            'needs': {'amount': round(needs_amt, 2), 'pct': needs_pct},
            'wants': {'amount': round(wants_amt, 2), 'pct': wants_pct},
            'savings': {'amount': round(savings_amt, 2), 'pct': savings_pct}
        }

        # Generated Narrative Insights
        insights = []
        if total_income > 0:
            if savings_rate >= 20:
                insights.append(f"Outstanding savings rate of {savings_rate}% this month, exceeding the 20% healthy benchmark.")
            elif savings_rate > 0:
                insights.append(f"You maintained a positive net savings rate of {savings_rate}%, accumulating ${savings_amt:,.2f}.")
            else:
                insights.append(f"Net outflow exceeded inflows by ${abs(net_savings):,.2f}. Review discretionary spending to restore surplus.")

        if prev_total_expense > 0:
            if expense_change_pct < 0:
                insights.append(f"Total expenditures decreased by {abs(expense_change_pct)}% compared to the previous statement period.")
            elif expense_change_pct > 0:
                insights.append(f"Expenditures increased by {expense_change_pct}% over last month (${prev_total_expense:,.2f} vs ${total_expense:,.2f}).")

        if top_categories:
            insights.append(f"Highest spending occurred in '{top_categories[0]['name']}' with ${top_categories[0]['amount']:,.2f} ({top_categories[0]['pct']}% of total expenses).")

        if needs_pct > 55 and total_income > 0:
            insights.append(f"Essential needs consumed {needs_pct}% of total income (recommended threshold: 50%).")

        month_name = calendar.month_name[month]

        return {
            'month_name': month_name,
            'month': month,
            'year': year,
            'total_income': round(total_income, 2),
            'total_expense': round(total_expense, 2),
            'net_savings': round(net_savings, 2),
            'savings_rate': round(savings_rate, 1),
            'previous_month_expense': round(prev_total_expense, 2),
            'expense_change_pct': round(expense_change_pct, 1),
            'top_categories': top_categories,
            'rule_50_30_20': rule_50_30_20,
            'insights': insights,
            'transaction_count': len(txs)
        }

