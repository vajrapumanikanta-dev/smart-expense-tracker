from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime
from models import db
from models.goal import FinancialGoal
from models.account import Account
from models.transaction import Transaction

goals_bp = Blueprint('goals', __name__)


@goals_bp.route('/')
@login_required
def index():
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).order_by(FinancialGoal.created_at.desc()).all()
    accounts = Account.query.filter_by(user_id=current_user.id).all()

    total_target = sum(float(g.target_amount) for g in goals)
    total_saved = sum(float(g.current_amount or 0.0) for g in goals)
    overall_progress = round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0

    today = date.today()

    # Calculate suggested monthly contribution for each goal
    goal_insights = []
    for g in goals:
        monthly_needed = 0.0
        if g.target_date and g.target_date > today:
            months_left = max(1, (g.target_date.year - today.year) * 12 + (g.target_date.month - today.month))
            monthly_needed = round(g.remaining_amount / months_left, 2)

        goal_insights.append({
            'goal': g,
            'monthly_needed': monthly_needed
        })

    return render_template(
        'goals/index.html',
        goals=goals,
        goal_insights=goal_insights,
        total_target=total_target,
        total_saved=total_saved,
        overall_progress=overall_progress,
        accounts=accounts,
        today=today
    )


@goals_bp.route('/add', methods=['POST'])
@login_required
def add():
    name = request.form.get('name', '').strip()
    target_amount = float(request.form.get('target_amount', 0.0))
    current_amount = float(request.form.get('current_amount', 0.0))
    category = request.form.get('category', 'Savings')
    target_date_str = request.form.get('target_date', '')

    if not name or target_amount <= 0:
        flash('Please provide a valid goal name and target amount.', 'danger')
        return redirect(url_for('goals.index'))

    target_date = None
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = None

    status = 'Achieved' if current_amount >= target_amount else 'In Progress'

    goal = FinancialGoal(
        user_id=current_user.id,
        name=name,
        target_amount=target_amount,
        current_amount=current_amount,
        category=category,
        target_date=target_date,
        status=status
    )
    db.session.add(goal)
    db.session.commit()
    flash(f'Financial goal "{name}" created!', 'success')
    return redirect(url_for('goals.index'))


@goals_bp.route('/contribute/<int:id>', methods=['POST'])
@login_required
def contribute(id):
    """Add funds to a goal from an account."""
    goal = FinancialGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    account_id = request.form.get('account_id', type=int)
    amount = float(request.form.get('amount', 0.0))

    if amount <= 0:
        flash('Contribution amount must be greater than zero.', 'danger')
        return redirect(url_for('goals.index'))

    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
    if account:
        account.balance = float(account.balance or 0.0) - amount

    goal.current_amount = float(goal.current_amount or 0.0) + amount
    if goal.current_amount >= float(goal.target_amount):
        goal.status = 'Achieved'
        flash(f'🎉 Congratulations! You have achieved your goal: "{goal.name}"!', 'success')
    else:
        flash(f'Added ${amount:,.2f} to "{goal.name}". Progress: {goal.progress_percentage}%.', 'success')

    db.session.commit()
    return redirect(url_for('goals.index'))


@goals_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    goal = FinancialGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = goal.name
    db.session.delete(goal)
    db.session.commit()
    flash(f'Goal "{name}" deleted.', 'info')
    return redirect(url_for('goals.index'))
