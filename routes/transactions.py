from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import or_

from models import db
from models.transaction import Transaction
from models.account import Account
from models.category import Category
from models.notification import Notification
from ai.anomaly_detection import AnomalyDetector
from ai.categorizer import ExpenseCategorizer

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/')
@login_required
def index():
    # Filtering parameters
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    account_id = request.args.get('account_id', type=int)
    tx_type = request.args.get('type', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort_by = request.args.get('sort_by', 'date_desc')
    page = request.args.get('page', 1, type=int)
    per_page = 15

    query = Transaction.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(
            or_(
                Transaction.description.ilike(f"%{search}%"),
                Transaction.amount.cast(db.String).ilike(f"%{search}%")
            )
        )

    if category_id:
        query = query.filter(Transaction.category_id == category_id)

    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    if tx_type in ['expense', 'income']:
        query = query.filter(Transaction.transaction_type == tx_type)

    if start_date:
        try:
            d = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.transaction_date >= d)
        except ValueError:
            pass

    if end_date:
        try:
            d = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Transaction.transaction_date <= d)
        except ValueError:
            pass

    # Sorting
    if sort_by == 'date_asc':
        query = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    elif sort_by == 'amount_desc':
        query = query.order_by(Transaction.amount.desc())
    elif sort_by == 'amount_asc':
        query = query.order_by(Transaction.amount.asc())
    else:  # date_desc
        query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.category_name.asc()).all()
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.account_name.asc()).all()

    return render_template(
        'transactions/index.html',
        transactions=transactions,
        pagination=pagination,
        categories=categories,
        accounts=accounts,
        search=search,
        selected_category_id=category_id,
        selected_account_id=account_id,
        selected_type=tx_type,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by
    )


@transactions_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.category_name.asc()).all()
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.account_name.asc()).all()

    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        category_id = request.form.get('category_id', type=int)
        tx_type = request.form.get('transaction_type', 'expense')
        amount_str = request.form.get('amount', '0')
        description = request.form.get('description', '').strip()
        date_str = request.form.get('transaction_date', '')

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
        except ValueError:
            flash('Please enter a valid positive transaction amount.', 'danger')
            return render_template('transactions/form.html', categories=categories, accounts=accounts, transaction=None)

        try:
            tx_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
        except ValueError:
            tx_date = date.today()

        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
        if not account:
            flash('Selected account is invalid.', 'danger')
            return render_template('transactions/form.html', categories=categories, accounts=accounts, transaction=None)

        # AI / ML Anomaly Check
        is_anomaly = False
        if tx_type == 'expense':
            is_anomaly, reason = AnomalyDetector.evaluate_single_transaction(
                user_id=current_user.id,
                amount=amount,
                category_id=category_id,
                description=description
            )
            if is_anomaly:
                db.session.add(Notification(
                    user_id=current_user.id,
                    title="Unusual Expense Detected",
                    message=f"Added ${amount:,.2f} for '{description}'. {reason}",
                    type="anomaly"
                ))

        # Create Transaction
        tx = Transaction(
            user_id=current_user.id,
            account_id=account_id,
            category_id=category_id,
            transaction_type=tx_type,
            amount=amount,
            description=description,
            transaction_date=tx_date,
            is_anomaly=is_anomaly
        )
        db.session.add(tx)

        # Adjust Account Balance
        if tx_type == 'income':
            account.balance = float(account.balance or 0.0) + amount
        else:
            account.balance = float(account.balance or 0.0) - amount

        db.session.commit()
        flash(f'Transaction of ${amount:,.2f} added successfully!', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('transactions/form.html', categories=categories, accounts=accounts, transaction=None)


@transactions_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    tx = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.category_name.asc()).all()
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.account_name.asc()).all()

    if request.method == 'POST':
        old_account = tx.account
        old_type = tx.transaction_type
        old_amount = float(tx.amount)

        account_id = request.form.get('account_id', type=int)
        category_id = request.form.get('category_id', type=int)
        tx_type = request.form.get('transaction_type', 'expense')
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '').strip()
        date_str = request.form.get('transaction_date', '')

        new_account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

        # Revert old balance effect
        if old_type == 'income':
            old_account.balance = float(old_account.balance or 0.0) - old_amount
        else:
            old_account.balance = float(old_account.balance or 0.0) + old_amount

        # Update transaction
        tx.account_id = account_id
        tx.category_id = category_id
        tx.transaction_type = tx_type
        tx.amount = amount
        tx.description = description
        if date_str:
            tx.transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Apply new balance effect
        if tx_type == 'income':
            new_account.balance = float(new_account.balance or 0.0) + amount
        else:
            new_account.balance = float(new_account.balance or 0.0) - amount

        db.session.commit()
        flash('Transaction updated successfully.', 'success')
        return redirect(url_for('transactions.index'))

    return render_template('transactions/form.html', categories=categories, accounts=accounts, transaction=tx)


@transactions_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    tx = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    account = tx.account
    amt = float(tx.amount)

    # Revert balance
    if account:
        if tx.transaction_type == 'income':
            account.balance = float(account.balance or 0.0) - amt
        else:
            account.balance = float(account.balance or 0.0) + amt

    db.session.delete(tx)
    db.session.commit()
    flash('Transaction deleted successfully.', 'info')
    return redirect(url_for('transactions.index'))


@transactions_bp.route('/api/predict-category', methods=['POST'])
@login_required
def predict_category():
    """AJAX helper to dynamically auto-suggest category while typing description."""
    data = request.get_json() or {}
    desc = data.get('description', '')
    cat_name, cat_obj = ExpenseCategorizer.predict_category(desc, user_id=current_user.id)
    return jsonify({
        'category_name': cat_name,
        'category_id': cat_obj.id if cat_obj else None
    })
