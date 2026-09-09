from models import db
from models.account import Account
from models.category import Category
from models.transaction import Transaction
from models.budget import Budget
from models.recurring import RecurringExpense
from models.goal import FinancialGoal
from models.ai_insight import AIInsight
from models.notification import Notification
from datetime import date, datetime, timedelta
import random

DEFAULT_CATEGORIES = [
    # Expenses
    {"name": "Food & Dining", "type": "expense", "icon": "utensils", "color": "#ef4444"},
    {"name": "Groceries", "type": "expense", "icon": "cart-shopping", "color": "#f97316"},
    {"name": "Housing & Rent", "type": "expense", "icon": "house", "color": "#eab308"},
    {"name": "Utilities & Bills", "type": "expense", "icon": "bolt", "color": "#84cc16"},
    {"name": "Transportation & Fuel", "type": "expense", "icon": "car", "color": "#06b6d4"},
    {"name": "Entertainment & Leisure", "type": "expense", "icon": "film", "color": "#8b5cf6"},
    {"name": "Healthcare & Medical", "type": "expense", "icon": "heart-pulse", "color": "#ec4899"},
    {"name": "Shopping", "type": "expense", "icon": "bag-shopping", "color": "#3b82f6"},
    {"name": "Travel & Vacations", "type": "expense", "icon": "plane", "color": "#14b8a6"},
    {"name": "Subscriptions", "type": "expense", "icon": "tv", "color": "#a855f7"},
    {"name": "Education", "type": "expense", "icon": "graduation-cap", "color": "#6366f1"},
    {"name": "Miscellaneous", "type": "expense", "icon": "tags", "color": "#64748b"},
    # Incomes
    {"name": "Salary & Wages", "type": "income", "icon": "money-bill-wave", "color": "#10b981"},
    {"name": "Freelance & Consulting", "type": "income", "icon": "laptop-code", "color": "#059669"},
    {"name": "Investments & Dividends", "type": "income", "icon": "chart-line", "color": "#047857"},
    {"name": "Rental Income", "type": "income", "icon": "building", "color": "#15803d"},
    {"name": "Other Income", "type": "income", "icon": "wallet", "color": "#22c55e"},
]

DEFAULT_ACCOUNTS = [
    {"name": "Main Checking", "type": "Checking", "balance": 0.00},
    {"name": "High-Yield Savings", "type": "Savings", "balance": 0.00},
    {"name": "Cash Wallet", "type": "Cash", "balance": 0.00},
    {"name": "Credit Card", "type": "Credit Card", "balance": 0.00},
]


def seed_user_defaults(user_id):
    """Seed standard categories and initial accounts for a new user."""
    # Seed categories
    for cat in DEFAULT_CATEGORIES:
        category = Category(
            user_id=user_id,
            category_name=cat["name"],
            category_type=cat["type"],
            icon=cat["icon"],
            color=cat["color"]
        )
        db.session.add(category)

    # Seed accounts
    for acc in DEFAULT_ACCOUNTS:
        account = Account(
            user_id=user_id,
            account_name=acc["name"],
            account_type=acc["type"],
            balance=acc["balance"]
        )
        db.session.add(account)

    db.session.commit()


def seed_demo_transactions(user_id):
    """Seed comprehensive realistic transactions, budgets, goals, and recurring items for rich demo data."""
    categories = Category.query.filter_by(user_id=user_id).all()
    accounts = Account.query.filter_by(user_id=user_id).all()
    
    if not categories or not accounts:
        seed_user_defaults(user_id)
        categories = Category.query.filter_by(user_id=user_id).all()
        accounts = Account.query.filter_by(user_id=user_id).all()

    cat_map = {c.category_name: c for c in categories}
    acc_map = {a.account_name: a for a in accounts}

    main_acc = acc_map.get("Main Checking") or accounts[0]
    savings_acc = acc_map.get("High-Yield Savings") or accounts[0]
    cash_acc = acc_map.get("Cash Wallet") or accounts[0]
    cc_acc = acc_map.get("Credit Card") or accounts[0]

    today = date.today()
    current_year = today.year
    current_month = today.month

    # 1. Budgets for current month
    budget_data = [
        ("Food & Dining", 600.0),
        ("Groceries", 500.0),
        ("Housing & Rent", 1400.0),
        ("Utilities & Bills", 250.0),
        ("Transportation & Fuel", 300.0),
        ("Entertainment & Leisure", 200.0),
        ("Shopping", 350.0),
        ("Subscriptions", 80.0),
    ]
    for cat_name, amt in budget_data:
        if cat_name in cat_map:
            b = Budget.query.filter_by(user_id=user_id, category_id=cat_map[cat_name].id, month=current_month, year=current_year).first()
            if not b:
                b = Budget(user_id=user_id, category_id=cat_map[cat_name].id, amount=amt, month=current_month, year=current_year)
                db.session.add(b)

    # 2. Financial Goals
    goals_data = [
        {"name": "Emergency Fund (6 Months)", "target": 18000.0, "current": 12500.0, "category": "Emergency Fund", "days": 180},
        {"name": "Japan Summer Vacation", "target": 4500.0, "current": 2200.0, "category": "Vacation", "days": 120},
        {"name": "New MacBook Pro M4", "target": 2500.0, "current": 1800.0, "category": "Gadgets", "days": 60},
    ]
    for g in goals_data:
        if not FinancialGoal.query.filter_by(user_id=user_id, name=g["name"]).first():
            goal = FinancialGoal(
                user_id=user_id,
                name=g["name"],
                target_amount=g["target"],
                current_amount=g["current"],
                category=g["category"],
                target_date=today + timedelta(days=g["days"]),
                status="In Progress"
            )
            db.session.add(goal)

    # 3. Recurring Expenses
    recurring_data = [
        {"name": "Apartment Rent", "amt": 1400.0, "freq": "Monthly", "cat": "Housing & Rent", "acc": main_acc.id, "due": 1},
        {"name": "Netflix 4K Ultra", "amt": 22.99, "freq": "Monthly", "cat": "Subscriptions", "acc": cc_acc.id, "due": 15},
        {"name": "Spotify Family", "amt": 16.99, "freq": "Monthly", "cat": "Subscriptions", "acc": cc_acc.id, "due": 20},
        {"name": "High-Speed Internet Fiber", "amt": 75.00, "freq": "Monthly", "cat": "Utilities & Bills", "acc": main_acc.id, "due": 10},
        {"name": "Gym Membership", "amt": 55.00, "freq": "Monthly", "cat": "Healthcare & Medical", "acc": cc_acc.id, "due": 5},
    ]
    for r in recurring_data:
        if r["cat"] in cat_map and not RecurringExpense.query.filter_by(user_id=user_id, name=r["name"]).first():
            due_d = date(current_year, current_month, min(r["due"], 28))
            if due_d < today:
                # Next month
                m = current_month + 1 if current_month < 12 else 1
                y = current_year if current_month < 12 else current_year + 1
                due_d = date(y, m, min(r["due"], 28))
            rec = RecurringExpense(
                user_id=user_id,
                account_id=r["acc"],
                category_id=cat_map[r["cat"]].id,
                name=r["name"],
                amount=r["amt"],
                frequency=r["freq"],
                next_due_date=due_d,
                active=True
            )
            db.session.add(rec)

    # 4. Realistic Transactions across past 90 days
    sample_expense_pool = [
        ("Whole Foods Market", 94.50, "Groceries", cc_acc),
        ("Trader Joe's Groceries", 68.20, "Groceries", main_acc),
        ("Dinner at Nobu Sushi", 185.00, "Food & Dining", cc_acc),
        ("Chipotle Mexican Grill", 18.50, "Food & Dining", cc_acc),
        ("Starbucks Morning Coffee", 6.75, "Food & Dining", cash_acc),
        ("Shell Gasoline & Fuel", 52.00, "Transportation & Fuel", cc_acc),
        ("Uber Ride Downtown", 24.80, "Transportation & Fuel", cc_acc),
        ("Electricity & Power Bill", 112.40, "Utilities & Bills", main_acc),
        ("Water & Sewage Utility", 48.00, "Utilities & Bills", main_acc),
        ("Amazon Electronics Purchase", 139.99, "Shopping", cc_acc),
        ("Target Essentials & Toiletries", 45.30, "Shopping", cc_acc),
        ("AMC Cinema Movie Tickets", 36.00, "Entertainment & Leisure", cc_acc),
        ("Steam Game Store", 59.99, "Entertainment & Leisure", cc_acc),
        ("Pharmacy & Prescription", 32.50, "Healthcare & Medical", main_acc),
        ("Coursera ML Specialization", 49.00, "Education", cc_acc),
    ]

    for days_ago in range(90, -1, -3):
        t_date = today - timedelta(days=days_ago)
        
        # Monthly Salary on 1st and 15th
        if t_date.day in (1, 15):
            db.session.add(Transaction(
                user_id=user_id,
                account_id=main_acc.id,
                category_id=cat_map["Salary & Wages"].id if "Salary & Wages" in cat_map else None,
                transaction_type="income",
                amount=3250.00,
                description="Bi-Weekly Payroll Direct Deposit - Tech Corp",
                transaction_date=t_date,
                is_recurring=True,
                is_anomaly=False
            ))
            
        # Freelance bonus occasionally
        if days_ago in (12, 45, 78):
            db.session.add(Transaction(
                user_id=user_id,
                account_id=main_acc.id,
                category_id=cat_map["Freelance & Consulting"].id if "Freelance & Consulting" in cat_map else None,
                transaction_type="income",
                amount=850.00,
                description="Freelance Web Development Client Milestone",
                transaction_date=t_date,
                is_recurring=False,
                is_anomaly=False
            ))

        # Add 1-2 random expenses
        pick_desc, pick_amt, pick_cat, pick_acc = random.choice(sample_expense_pool)
        # Jitter amount slightly
        amt = round(pick_amt * random.uniform(0.85, 1.25), 2)
        if pick_cat in cat_map:
            db.session.add(Transaction(
                user_id=user_id,
                account_id=pick_acc.id,
                category_id=cat_map[pick_cat].id,
                transaction_type="expense",
                amount=amt,
                description=f"{pick_desc}",
                transaction_date=t_date,
                is_recurring=False,
                is_anomaly=False
            ))

    # Add 1 anomaly expense for ML detector demonstration
    anomaly_date = today - timedelta(days=5)
    if "Shopping" in cat_map:
        db.session.add(Transaction(
            user_id=user_id,
            account_id=cc_acc.id,
            category_id=cat_map["Shopping"].id,
            transaction_type="expense",
            amount=1850.00,
            description="Luxury Designer Watch Purchase",
            transaction_date=anomaly_date,
            is_recurring=False,
            is_anomaly=True
        ))

    # 5. Notifications & AI Insights
    db.session.add(Notification(
        user_id=user_id,
        title="Welcome to AI-Powered Expense Tracker",
        message="Your intelligent personal finance dashboard is ready. Explore your budget, account balances, and automated insights.",
        type="general",
        is_read=False
    ))
    db.session.add(Notification(
        user_id=user_id,
        title="Unusual Spending Detected",
        message="Transaction 'Luxury Designer Watch Purchase' ($1,850.00) exceeds your 90-day typical shopping average by 412%.",
        type="anomaly",
        is_read=False
    ))
    db.session.add(AIInsight(
        user_id=user_id,
        insight_type="spending_pattern",
        title="Weekend Dining Trend Analysis",
        message="You spend 42% more on Food & Dining on Friday through Sunday compared to weekdays. Planning ahead could save ~$140/month.",
        severity="info"
    ))
    db.session.add(AIInsight(
        user_id=user_id,
        insight_type="saving_tip",
        title="Goal Acceleration Tip",
        message="Your 'Japan Summer Vacation' goal is 48% funded. Allocating $385/month will ensure completion 2 weeks ahead of target.",
        severity="success"
    ))

    db.session.commit()
