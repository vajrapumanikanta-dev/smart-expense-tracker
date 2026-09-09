import os
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, datetime, timedelta
from app import create_app
from models import db, User, Account, Category, Transaction, Budget, RecurringExpense, FinancialGoal, Notification, AIInsight
from models.seed import seed_user_defaults, seed_demo_transactions
from ai.assistant import FinancialAssistant
from ai.categorizer import ExpenseCategorizer
from ai.anomaly_detection import AnomalyDetector
from ai.forecasting import ExpenseForecaster
from ai.recommendations import FinancialRecommender
from ai.insights import FinancialInsightsEngine

print("Initializing test application...")
app = create_app('testing')
app.config.update({
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'WTF_CSRF_ENABLED': False
})

with app.app_context():
    db.create_all()
    print("Database tables created.")

    # 1. User creation and defaults
    user = User(name='Test User', email='test@example.com')
    user.set_password('Secret123')
    db.session.add(user)
    db.session.commit()
    seed_user_defaults(user.id)
    print("User and default accounts/categories seeded.")

    # Verify defaults
    accounts = Account.query.filter_by(user_id=user.id).all()
    categories = Category.query.filter_by(user_id=user.id).all()
    assert len(accounts) == 4, f"Expected 4 accounts, got {len(accounts)}"
    assert len(categories) == 17, f"Expected 17 categories, got {len(categories)}"
    print(f"Verified: {len(accounts)} accounts, {len(categories)} categories.")

    # 2. Seed realistic demo transactions
    seed_demo_transactions(user.id)
    tx_count = Transaction.query.filter_by(user_id=user.id).count()
    assert tx_count > 0, "No transactions seeded"
    print(f"Verified: {tx_count} demo transactions seeded successfully.")

    # 3. Natural Language Parser
    nl_res = ExpenseCategorizer.parse_natural_language_transaction("Spent $54.20 on groceries yesterday", user_id=user.id)
    assert nl_res['amount'] == 54.20
    assert nl_res['transaction_type'] == 'expense'
    assert 'Groceries' in nl_res['category_name'] or 'Food' in nl_res['category_name']
    print(f"Verified: Natural language parser parsed: {nl_res['amount']} into {nl_res['category_name']}")

    # 4. AI Financial Assistant
    ai_bal = FinancialAssistant.ask("What is my total balance across accounts?", user.id)
    assert ai_bal['intent'] == 'account_balance'
    print(f"Verified AI Assistant balance query: {ai_bal['answer']}")

    ai_high = FinancialAssistant.ask("What was my highest expense?", user.id)
    assert ai_high['intent'] == 'highest_expense'
    print(f"Verified AI Assistant highest expense: {ai_high['answer']}")

    # 5. ML Anomaly Detector
    anomalies = AnomalyDetector.detect_anomalies_for_user(user.id)
    print(f"Verified Anomaly Detector: found {len(anomalies)} statistical/ML anomalies.")

    # 6. ML Forecaster
    forecast = ExpenseForecaster.forecast_monthly_expenses(user.id, horizon_months=3)
    assert len(forecast['forecast']) == 3
    print(f"Verified Forecaster: Next month projected spend = ${forecast['predicted_next_month']:,.2f}, trend = {forecast['trend_direction']}")

    # 7. Financial Health Score
    health = FinancialInsightsEngine.calculate_financial_health_score(user.id)
    assert 0 <= health['score'] <= 100
    print(f"Verified Health Score: {health['score']}/100 ({health['grade']})")

    # 8. Monthly Report
    monthly_rep = FinancialInsightsEngine.generate_monthly_report(user.id, date.today().year, date.today().month)
    assert 'rule_50_30_20' in monthly_rep
    print(f"Verified Monthly Report: Total Inflow = ${monthly_rep['total_income']:,.2f}, Total Outflow = ${monthly_rep['total_expense']:,.2f}")

    # 9. Test client routes
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    # Test all rendered pages
    pages = [
        ('/', 'Financial Overview'),
        ('/transactions/', 'Transaction Ledger'),
        ('/accounts/', 'Account Management'),
        ('/budgets/', 'Monthly Budgets'),
        ('/recurring/', 'Recurring Bills & Subscriptions'),
        ('/goals/', 'Savings Goals'),
        ('/reports/', 'Financial Reports'),
        ('/ai/assistant', 'AI Financial Assistant'),
        ('/ai/forecast', 'Machine Learning Expense Forecasting'),
        ('/ai/anomalies', 'ML Anomaly Scanner'),
        ('/ai/monthly-report', 'AI Monthly Financial Report'),
        ('/notifications/', 'Notification Center')
    ]

    for url, expected_str in pages:
        res = client.get(url)
        assert res.status_code == 200, f"Page {url} returned status {res.status_code}"
        assert expected_str.encode() in res.data, f"Page {url} did not contain expected text '{expected_str}'"
        print(f"Page OK (200): {url}")

print("\n===========================================================")
print(" ALL TESTS AND VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
print("===========================================================\n")
