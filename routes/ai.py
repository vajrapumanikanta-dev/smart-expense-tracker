from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date
import calendar

from models import db
from models.transaction import Transaction
from models.category import Category
from models.account import Account
from models.ai_insight import AIInsight
from ai.assistant import FinancialAssistant
from ai.categorizer import ExpenseCategorizer
from ai.anomaly_detection import AnomalyDetector
from ai.forecasting import ExpenseForecaster
from ai.recommendations import FinancialRecommender
from ai.insights import FinancialInsightsEngine

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/assistant')
@login_required
def assistant():
    """Interactive AI Financial Assistant page with chat window & quick prompts."""
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    health_score = FinancialInsightsEngine.calculate_financial_health_score(current_user.id)
    return render_template('ai/assistant.html', accounts=accounts, categories=categories, health_score=health_score)


@ai_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handles conversational questions from the AI assistant chat interface."""
    data = request.get_json() or {}
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    response = FinancialAssistant.ask(message, current_user.id)
    return jsonify(response)


@ai_bp.route('/api/parse-nl-transaction', methods=['POST'])
@login_required
def parse_nl_transaction():
    """
    Parses natural language transaction entries like:
    'Spent $65 at Whole Foods for groceries yesterday'
    Returns structured form fields.
    """
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({'error': 'Prompt cannot be empty'}), 400

    parsed = ExpenseCategorizer.parse_natural_language_transaction(prompt, user_id=current_user.id)
    return jsonify(parsed)


@ai_bp.route('/forecast')
@login_required
def forecast():
    """Machine Learning Expense Forecasting page with interactive regression projection chart."""
    forecast_data = ExpenseForecaster.forecast_monthly_expenses(current_user.id, horizon_months=3)
    return render_template('ai/forecast.html', forecast_data=forecast_data)


@ai_bp.route('/api/forecast-data')
@login_required
def forecast_api():
    horizon = request.args.get('horizon', 3, type=int)
    data = ExpenseForecaster.forecast_monthly_expenses(current_user.id, horizon_months=horizon)
    return jsonify(data)


@ai_bp.route('/anomalies')
@login_required
def anomalies():
    """Machine Learning Anomaly Detection page."""
    anomalies_list = AnomalyDetector.detect_anomalies_for_user(current_user.id)
    return render_template('ai/anomalies.html', anomalies=anomalies_list)


@ai_bp.route('/api/scan-anomalies', methods=['POST'])
@login_required
def scan_anomalies():
    """Runs a full ML Isolation Forest & statistical scan and marks flagged transactions."""
    anomalies_list = AnomalyDetector.detect_anomalies_for_user(current_user.id)
    flagged_ids = [a['transaction_id'] for a in anomalies_list]

    # Reset existing flags and set new flags
    Transaction.query.filter_by(user_id=current_user.id).update({'is_anomaly': False})
    if flagged_ids:
        Transaction.query.filter(Transaction.id.in_(flagged_ids)).update({'is_anomaly': True}, synchronize_session=False)

    db.session.commit()
    return jsonify({
        'status': 'success',
        'anomalies_found': len(anomalies_list),
        'anomalies': anomalies_list
    })


@ai_bp.route('/monthly-report')
@login_required
def monthly_report():
    """Monthly AI-generated financial report with health metrics & category breakdown."""
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)

    report = FinancialInsightsEngine.generate_monthly_report(current_user.id, year=year, month=month)
    health = FinancialInsightsEngine.calculate_financial_health_score(current_user.id)
    recs = FinancialRecommender.generate_budget_recommendations(current_user.id)

    months_list = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years_list = [today.year - 1, today.year, today.year + 1]

    return render_template(
        'ai/monthly_report.html',
        report=report,
        health=health,
        recommendations=recs,
        selected_month=month,
        selected_year=year,
        months_list=months_list,
        years_list=years_list
    )
