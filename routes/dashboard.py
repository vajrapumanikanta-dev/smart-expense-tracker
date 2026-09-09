from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, datetime, timedelta
import calendar

from models import db
from models.transaction import Transaction
from models.account import Account
from models.category import Category
from models.budget import Budget
from models.recurring import RecurringExpense
from models.goal import FinancialGoal
from models.ai_insight import AIInsight
from ai.insights import FinancialInsightsEngine
from ai.recommendations import FinancialRecommender

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    current_year = today.year
    current_month = today.month

    # 1. Accounts & Total Balance
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    total_balance = sum(float(a.balance or 0.0) for a in accounts)

    # 2. Current Month Income & Expenses
    start_of_month = date(current_year, current_month, 1)
    
    month_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'income',
        Transaction.transaction_date >= start_of_month,
        Transaction.transaction_date <= today
    ).scalar() or 0.0

    month_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'expense',
        Transaction.transaction_date >= start_of_month,
        Transaction.transaction_date <= today
    ).scalar() or 0.0

    net_savings = float(month_income) - float(month_expense)

    # 3. Monthly Budget Progress
    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).all()
    total_budget = sum(float(b.amount) for b in budgets)
    budget_used_pct = round((float(month_expense) / total_budget * 100), 1) if total_budget > 0 else 0.0

    # 4. Recent Transactions (latest 7)
    recent_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(7).all()

    # 5. Financial Health & AI Insights
    health_score = FinancialInsightsEngine.calculate_financial_health_score(current_user.id)
    overspending_alerts = FinancialRecommender.predict_overspending(current_user.id)
    ai_insights = AIInsight.query.filter_by(user_id=current_user.id).order_by(AIInsight.created_at.desc()).limit(3).all()

    # 6. Goals preview
    goals = FinancialGoal.query.filter_by(user_id=current_user.id, status='In Progress').limit(3).all()

    return render_template(
        'dashboard/index.html',
        total_balance=total_balance,
        month_income=float(month_income),
        month_expense=float(month_expense),
        net_savings=net_savings,
        total_budget=total_budget,
        budget_used_pct=budget_used_pct,
        recent_transactions=recent_transactions,
        health_score=health_score,
        overspending_alerts=overspending_alerts,
        ai_insights=ai_insights,
        goals=goals,
        accounts=accounts,
        current_month_name=calendar.month_name[current_month],
        current_year=current_year
    )


@dashboard_bp.route('/api/chart-data')
@login_required
def chart_data():
    """
    Returns aggregated JSON data for the 5 dashboard Chart.js visualizations:
    1. Expense by Category (Doughnut)
    2. Monthly Expense Trend (Line)
    3. Income vs Expense (Grouped Bar)
    4. Budget vs Actual Comparison (Bar)
    5. Account Balance Distribution (Doughnut / Bar)
    """
    today = date.today()
    current_year = today.year
    current_month = today.month

    # 1. Expense by Category (Current Month)
    start_of_month = date(current_year, current_month, 1)
    cat_query = db.session.query(
        Category.category_name,
        Category.color,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'expense',
        Transaction.transaction_date >= start_of_month
    ).group_by(Category.id).all()

    # Fallback to all time if current month is empty
    if not cat_query:
        cat_query = db.session.query(
            Category.category_name,
            Category.color,
            func.sum(Transaction.amount).label('total')
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == 'expense'
        ).group_by(Category.id).all()

    category_labels = [c[0] for c in cat_query]
    category_colors = [c[1] or '#6366f1' for c in cat_query]
    category_values = [round(float(c[2]), 2) for c in cat_query]

    # 2. Monthly Trend & Income vs Expense (Past 6 Months)
    monthly_labels = []
    income_trend = []
    expense_trend = []

    for i in range(5, -1, -1):
        # Calculate target month and year
        m = (current_month - 1 - i) % 12 + 1
        y = current_year - ((current_month - 1 - i) < 0)
        
        m_start = date(y, m, 1)
        last_d = calendar.monthrange(y, m)[1]
        m_end = date(y, m, last_d)

        monthly_labels.append(f"{calendar.month_abbr[m]} {str(y)[2:]}")

        inc = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == 'income',
            Transaction.transaction_date >= m_start,
            Transaction.transaction_date <= m_end
        ).scalar() or 0.0

        exp = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= m_start,
            Transaction.transaction_date <= m_end
        ).scalar() or 0.0

        income_trend.append(round(float(inc), 2))
        expense_trend.append(round(float(exp), 2))

    # 3. Budget vs Actual (Current Month)
    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).all()

    budget_labels = []
    budget_allocated = []
    budget_actual_spent = []

    for b in budgets:
        cat_name = b.category.category_name if b.category else 'Overall'
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b.category_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= today
        ).scalar() or 0.0

        budget_labels.append(cat_name)
        budget_allocated.append(round(float(b.amount), 2))
        budget_actual_spent.append(round(float(spent), 2))

    # 4. Account Balances
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_labels = [a.account_name for a in accounts]
    account_balances = [round(float(a.balance or 0.0), 2) for a in accounts]

    return jsonify({
        'category_chart': {
            'labels': category_labels,
            'datasets': [{
                'data': category_values,
                'backgroundColor': category_colors
            }]
        },
        'monthly_trend': {
            'labels': monthly_labels,
            'datasets': [
                {
                    'label': 'Expenses',
                    'data': expense_trend,
                    'borderColor': '#ef4444',
                    'backgroundColor': 'rgba(239, 68, 68, 0.15)',
                    'fill': True,
                    'tension': 0.35
                },
                {
                    'label': 'Income',
                    'data': income_trend,
                    'borderColor': '#10b981',
                    'backgroundColor': 'rgba(16, 185, 129, 0.15)',
                    'fill': True,
                    'tension': 0.35
                }
            ]
        },
        'budget_vs_actual': {
            'labels': budget_labels,
            'budget': budget_allocated,
            'actual': budget_actual_spent
        },
        'account_balances': {
            'labels': account_labels,
            'balances': account_balances
        }
    })
