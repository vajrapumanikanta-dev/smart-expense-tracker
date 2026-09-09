from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
import calendar

from models import db
from models.recurring import RecurringExpense
from models.account import Account
from models.category import Category
from models.transaction import Transaction
from ai.recommendations import FinancialRecommender

recurring_bp = Blueprint('recurring', __name__)


def advance_due_date(current_date, frequency):
    """Calculate the next due date based on recurrence frequency."""
    if frequency == 'Weekly':
        return current_date + timedelta(days=7)
    elif frequency == 'Bi-Weekly':
        return current_date + timedelta(days=14)
    elif frequency == 'Yearly':
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            return current_date + timedelta(days=365)
    else:  # Monthly default
        m = current_date.month % 12 + 1
        y = current_date.year + (1 if current_date.month == 12 else 0)
        day = min(current_date.day, calendar.monthrange(y, m)[1])
        return date(y, m, day)


@recurring_bp.route('/')
@login_required
def index():
    recurrings = RecurringExpense.query.filter_by(user_id=current_user.id).order_by(RecurringExpense.next_due_date.asc()).all()
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id, category_type='expense').all()

    today = date.today()
    total_monthly_commitment = 0.0

    for r in recurrings:
        amt = float(r.amount)
        if r.frequency == 'Monthly':
            total_monthly_commitment += amt
        elif r.frequency == 'Weekly':
            total_monthly_commitment += amt * 4.33
        elif r.frequency == 'Yearly':
            total_monthly_commitment += amt / 12.0

    # Auto-detected recurring subscriptions from historical transactions
    detected_subscriptions = FinancialRecommender.detect_subscriptions(current_user.id)

    return render_template(
        'recurring/index.html',
        recurrings=recurrings,
        accounts=accounts,
        categories=categories,
        total_monthly_commitment=total_monthly_commitment,
        detected_subscriptions=detected_subscriptions,
        today=today
    )


@recurring_bp.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form.get('name', '').strip()
    amount = float(request.form.get('amount', 0.0))
    frequency = request.form.get('frequency', 'Monthly')
    account_id = request.form.get('account_id', type=int)
    category_id = request.form.get('category_id', type=int)
    due_date_str = request.form.get('next_due_date', '')

    if not name or amount <= 0:
        flash('Please provide a valid bill name and amount.', 'danger')
        return redirect(url_for('recurring.index'))

    try:
        next_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else date.today()
    except ValueError:
        next_due_date = date.today()

    rec = RecurringExpense(
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        name=name,
        amount=amount,
        frequency=frequency,
        next_due_date=next_due_date,
        active=True
    )
    db.session.add(rec)
    db.session.commit()
    flash(f'Recurring expense "{name}" registered.', 'success')
    return redirect(url_for('recurring.index'))


@recurring_bp.route('/process/<int:id>', methods=['POST'])
@login_required
def process_payment(id):
    """Logs the recurring bill as a real transaction and moves the next due date forward."""
    rec = RecurringExpense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    account = rec.account
    amt = float(rec.amount)

    today = date.today()

    # Create transaction
    tx = Transaction(
        user_id=current_user.id,
        account_id=rec.account_id,
        category_id=rec.category_id,
        transaction_type='expense',
        amount=amt,
        description=f"Recurring: {rec.name}",
        transaction_date=today,
        is_recurring=True
    )
    db.session.add(tx)

    # Deduct account balance
    if account:
        account.balance = float(account.balance or 0.0) - amt

    # Advance next due date
    rec.last_processed_date = today
    rec.next_due_date = advance_due_date(rec.next_due_date, rec.frequency)

    db.session.commit()
    flash(f'Payment of ${amt:,.2f} recorded for "{rec.name}". Next due date updated to {rec.next_due_date.strftime("%b %d, %Y")}.', 'success')
    return redirect(url_for('recurring.index'))


@recurring_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    rec = RecurringExpense.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = rec.name
    db.session.delete(rec)
    db.session.commit()
    flash(f'Recurring expense "{name}" removed.', 'info')
    return redirect(url_for('recurring.index'))
