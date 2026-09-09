import pytest
import os
import sys
import json
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Account, Category, Transaction, Budget, RecurringExpense, FinancialGoal, Notification, AIInsight
from models.seed import seed_user_defaults, seed_demo_transactions
from ai.assistant import FinancialAssistant
from ai.categorizer import ExpenseCategorizer
from ai.anomaly_detection import AnomalyDetector
from ai.forecasting import ExpenseForecaster
from ai.recommendations import FinancialRecommender
from ai.insights import FinancialInsightsEngine


@pytest.fixture
def app():
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_user(app):
    with app.app_context():
        user = User(name='Alex Mercer', email='alex@example.com')
        user.set_password('Password123!')
        db.session.add(user)
        db.session.commit()
        seed_user_defaults(user.id)
        seed_demo_transactions(user.id)
        return user.id


def test_user_authentication_flow(client, app):
    # 1. Register new user
    res = client.post('/register', data={
        'name': 'Sarah Connor',
        'email': 'sarah@example.com',
        'password': 'SecurePassword123',
        'confirm_password': 'SecurePassword123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Sarah Connor' in res.data or b'Dashboard' in res.data

    with app.app_context():
        user = User.query.filter_by(email='sarah@example.com').first()
        assert user is not None
        assert user.check_password('SecurePassword123')
        # Check default accounts and categories
        accounts = Account.query.filter_by(user_id=user.id).all()
        assert len(accounts) >= 4
        categories = Category.query.filter_by(user_id=user.id).all()
        assert len(categories) >= 12

    # 2. Logout
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200

    # 3. Login
    res = client.post('/login', data={
        'email': 'sarah@example.com',
        'password': 'SecurePassword123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Financial Overview' in res.data or b'Dashboard' in res.data


def test_transaction_crud(client, auth_user, app):
    # Log in as auth_user
    with client.session_transaction() as sess:
        sess['_user_id'] = str(auth_user)
        sess['_fresh'] = True

    with app.app_context():
        acc = Account.query.filter_by(user_id=auth_user).first()
        cat = Category.query.filter_by(user_id=auth_user, category_type='expense').first()
        initial_balance = float(acc.balance)

    # Add Expense Transaction
    res = client.post('/transactions/add', data={
        'account_id': acc.id,
        'category_id': cat.id,
        'transaction_type': 'expense',
        'amount': '75.50',
        'description': 'Trader Joes Dinner Groceries',
        'transaction_date': date.today().strftime('%Y-%m-%d')
    }, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        acc_updated = db.session.get(Account, acc.id)
        assert round(float(acc_updated.balance), 2) == round(initial_balance - 75.50, 2)
        tx = Transaction.query.filter_by(description='Trader Joes Dinner Groceries').first()
        assert tx is not None
        assert float(tx.amount) == 75.50


def test_natural_language_parsing(app, auth_user):
    with app.app_context():
        # Test NL parser
        prompt1 = "Spent $65.40 at Whole Foods for groceries yesterday"
        parsed = ExpenseCategorizer.parse_natural_language_transaction(prompt1, user_id=auth_user)
        assert parsed['amount'] == 65.40
        assert parsed['transaction_type'] == 'expense'
        assert 'Groceries' in parsed['category_name'] or 'Food' in parsed['category_name']
        assert parsed['transaction_date'] == (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Test Income NL parser
        prompt2 = "Received $4200 salary from Acme Corp today"
        parsed2 = ExpenseCategorizer.parse_natural_language_transaction(prompt2, user_id=auth_user)
        assert parsed2['amount'] == 4200.00
        assert parsed2['transaction_type'] == 'income'
        assert parsed2['transaction_date'] == date.today().strftime('%Y-%m-%d')


def test_ai_assistant_nlp(app, auth_user):
    with app.app_context():
        # Test total balance intent
        resp1 = FinancialAssistant.ask("What is my total balance across accounts?", auth_user)
        assert resp1['intent'] == 'account_balance'
        assert 'total_balance' in resp1['data']

        # Test highest expense intent
        resp2 = FinancialAssistant.ask("What was my highest expense?", auth_user)
        assert resp2['intent'] == 'highest_expense'

        # Test health score intent
        resp3 = FinancialAssistant.ask("What is my financial health score?", auth_user)
        assert resp3['intent'] == 'financial_health'
        assert 0 <= resp3['data']['score'] <= 100


def test_anomaly_detection_and_forecasting(app, auth_user):
    with app.app_context():
        # 1. Anomaly Detector
        anomalies = AnomalyDetector.detect_anomalies_for_user(auth_user)
        assert isinstance(anomalies, list)

        # 2. Expense Forecaster
        forecast = ExpenseForecaster.forecast_monthly_expenses(auth_user, horizon_months=3)
        assert 'historical' in forecast
        assert 'forecast' in forecast
        assert len(forecast['forecast']) == 3
        assert forecast['trend_direction'] in ['increasing', 'decreasing', 'stable']


def test_financial_insights_and_health_score(app, auth_user):
    with app.app_context():
        health = FinancialInsightsEngine.calculate_financial_health_score(auth_user)
        assert 'score' in health
        assert 'grade' in health
        assert 'savings_rate' in health
        assert 0 <= health['score'] <= 100

        report = FinancialInsightsEngine.generate_monthly_report(auth_user, date.today().year, date.today().month)
        assert 'total_income' in report
        assert 'total_expense' in report
        assert 'rule_50_30_20' in report
        assert 'top_categories' in report


def test_report_exports(client, auth_user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(auth_user)
        sess['_fresh'] = True

    # CSV Export
    res_csv = client.get('/reports/export/csv')
    assert res_csv.status_code == 200
    assert res_csv.mimetype == 'text/csv'

    # Excel Export
    res_excel = client.get('/reports/export/excel')
    assert res_excel.status_code == 200
    assert 'spreadsheet' in res_excel.mimetype or 'openxmlformats' in res_excel.mimetype

    # PDF Export
    res_pdf = client.get('/reports/export/pdf')
    assert res_pdf.status_code == 200
    assert res_pdf.mimetype == 'application/pdf'


def test_ai_templates_rendering(client, auth_user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(auth_user)
        sess['_fresh'] = True

    # 1. Assistant page
    res = client.get('/ai/assistant')
    assert res.status_code == 200
    assert b'AI Financial Assistant' in res.data

    # 2. Forecast page
    res = client.get('/ai/forecast')
    assert res.status_code == 200
    assert b'ML Expense Forecasting' in res.data

    # 3. Anomalies page
    res = client.get('/ai/anomalies')
    assert res.status_code == 200
    assert b'ML Anomaly Scanner' in res.data

    # 4. Monthly Report page
    res = client.get('/ai/monthly-report')
    assert res.status_code == 200
    assert b'AI Monthly Financial Report' in res.data

    # 5. Notifications page
    res = client.get('/notifications/')
    assert res.status_code == 200
    assert b'Notification Center' in res.data
