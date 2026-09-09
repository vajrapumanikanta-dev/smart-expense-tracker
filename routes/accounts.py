from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date
from models import db
from models.account import Account
from models.transaction import Transaction
from models.category import Category

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/')
@login_required
def index():
    accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.account_name.asc()).all()
    total_balance = sum(float(a.balance or 0.0) for a in accounts)

    # Calculate transactions count and recent transactions per account
    account_stats = []
    for a in accounts:
        tx_count = Transaction.query.filter_by(account_id=a.id).count()
        recent_txs = Transaction.query.filter_by(account_id=a.id).order_by(Transaction.transaction_date.desc()).limit(5).all()
        account_stats.append({
            'account': a,
            'tx_count': tx_count,
            'recent_txs': recent_txs
        })

    return render_template(
        'accounts/index.html',
        accounts=accounts,
        account_stats=account_stats,
        total_balance=total_balance
    )


@accounts_bp.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form.get('account_name', '').strip()
    acc_type = request.form.get('account_type', 'Checking')
    balance = float(request.form.get('balance', 0.0))

    if not name:
        flash('Account name is required.', 'danger')
        return redirect(url_for('accounts.index'))

    acc = Account(
        user_id=current_user.id,
        account_name=name,
        account_type=acc_type,
        balance=balance
    )
    db.session.add(acc)
    db.session.commit()
    flash(f'Account "{name}" added successfully.', 'success')
    return redirect(url_for('accounts.index'))


@accounts_bp.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit(id):
    acc = Account.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = request.form.get('account_name', '').strip()
    acc_type = request.form.get('account_type', 'Checking')
    balance = float(request.form.get('balance', 0.0))

    if not name:
        flash('Account name cannot be empty.', 'danger')
        return redirect(url_for('accounts.index'))

    acc.account_name = name
    acc.account_type = acc_type
    acc.balance = balance
    db.session.commit()
    flash(f'Account "{name}" updated successfully.', 'success')
    return redirect(url_for('accounts.index'))


@accounts_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    acc = Account.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    # Check if this is the only account
    count = Account.query.filter_by(user_id=current_user.id).count()
    if count <= 1:
        flash('You must keep at least one active account.', 'warning')
        return redirect(url_for('accounts.index'))

    name = acc.account_name
    db.session.delete(acc)
    db.session.commit()
    flash(f'Account "{name}" and associated transactions deleted.', 'info')
    return redirect(url_for('accounts.index'))


@accounts_bp.route('/transfer', methods=['POST'])
@login_required
def transfer():
    """Transfer funds between two accounts."""
    from_acc_id = request.form.get('from_account_id', type=int)
    to_acc_id = request.form.get('to_account_id', type=int)
    amount = float(request.form.get('amount', 0.0))
    notes = request.form.get('notes', 'Internal Account Transfer').strip()

    if from_acc_id == to_acc_id:
        flash('Source and destination accounts must be different.', 'danger')
        return redirect(url_for('accounts.index'))

    if amount <= 0:
        flash('Transfer amount must be greater than zero.', 'danger')
        return redirect(url_for('accounts.index'))

    from_acc = Account.query.filter_by(id=from_acc_id, user_id=current_user.id).first_or_404()
    to_acc = Account.query.filter_by(id=to_acc_id, user_id=current_user.id).first_or_404()

    # Create transfer category if not existing
    transfer_cat = Category.query.filter_by(user_id=current_user.id, category_name='Transfer').first()
    if not transfer_cat:
        transfer_cat = Category(user_id=current_user.id, category_name='Transfer', category_type='expense', icon='arrow-right-arrow-left', color='#64748b')
        db.session.add(transfer_cat)
        db.session.commit()

    today = date.today()

    # 1. Outgoing transaction
    tx_out = Transaction(
        user_id=current_user.id,
        account_id=from_acc.id,
        category_id=transfer_cat.id,
        transaction_type='expense',
        amount=amount,
        description=f"Transfer to {to_acc.account_name}: {notes}",
        transaction_date=today
    )
    from_acc.balance = float(from_acc.balance or 0.0) - amount
    db.session.add(tx_out)

    # 2. Incoming transaction
    tx_in = Transaction(
        user_id=current_user.id,
        account_id=to_acc.id,
        category_id=transfer_cat.id,
        transaction_type='income',
        amount=amount,
        description=f"Transfer from {from_acc.account_name}: {notes}",
        transaction_date=today
    )
    to_acc.balance = float(to_acc.balance or 0.0) + amount
    db.session.add(tx_in)

    db.session.commit()
    flash(f'Successfully transferred ${amount:,.2f} from "{from_acc.account_name}" to "{to_acc.account_name}".', 'success')
    return redirect(url_for('accounts.index'))
