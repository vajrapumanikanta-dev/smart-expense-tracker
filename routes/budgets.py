from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date
import calendar

from models import db
from models.budget import Budget
from models.category import Category
from models.transaction import Transaction
from ai.recommendations import FinancialRecommender

budgets_bp = Blueprint('budgets', __name__)


@budgets_bp.route('/')
@login_required
def index():
    today = date.today()
    selected_month = request.args.get('month', today.month, type=int)
    selected_year = request.args.get('year', today.year, type=int)

    categories = Category.query.filter_by(user_id=current_user.id, category_type='expense').order_by(Category.category_name.asc()).all()
    budgets = Budget.query.filter_by(user_id=current_user.id, month=selected_month, year=selected_year).all()
    budget_map = {b.category_id: b for b in budgets}

    start_date = date(selected_year, selected_month, 1)
    last_day = calendar.monthrange(selected_year, selected_month)[1]
    end_date = date(selected_year, selected_month, last_day)

    # Actual expenses per category in this month
    expenses = db.session.query(
        Transaction.category_id,
        func.sum(Transaction.amount).label('total_spent')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'expense',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).group_by(Transaction.category_id).all()

    spent_map = {e[0]: float(e[1]) for e in expenses}

    # Build status list
    budget_items = []
    total_budgeted = 0.0
    total_spent = 0.0

    for cat in categories:
        b = budget_map.get(cat.id)
        budget_amt = float(b.amount) if b else 0.0
        spent_amt = spent_map.get(cat.id, 0.0)

        if budget_amt > 0 or spent_amt > 0:
            total_budgeted += budget_amt
            total_spent += spent_amt

            progress_pct = round((spent_amt / budget_amt * 100), 1) if budget_amt > 0 else 100.0
            remaining = budget_amt - spent_amt

            status_color = 'success' if progress_pct <= 75 else ('warning' if progress_pct <= 100 else 'danger')

            budget_items.append({
                'budget_id': b.id if b else None,
                'category_id': cat.id,
                'category_name': cat.category_name,
                'category_icon': cat.icon,
                'category_color': cat.color,
                'budget_amount': budget_amt,
                'spent_amount': spent_amt,
                'remaining_amount': remaining,
                'progress_pct': min(progress_pct, 100.0),
                'actual_pct': progress_pct,
                'status_color': status_color
            })

    # AI Recommendations & Overspending Predictions
    ai_recommendations = FinancialRecommender.generate_budget_recommendations(current_user.id)
    overspending_alerts = FinancialRecommender.predict_overspending(current_user.id)

    months_list = [(i, calendar.month_name[i]) for i in range(1, 13)]
    years_list = [today.year - 1, today.year, today.year + 1]

    return render_template(
        'budgets/index.html',
        budget_items=budget_items,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        total_remaining=total_budgeted - total_spent,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_month_name=calendar.month_name[selected_month],
        categories=categories,
        ai_recommendations=ai_recommendations,
        overspending_alerts=overspending_alerts,
        months_list=months_list,
        years_list=years_list
    )


@budgets_bp.route('/save', methods=['POST'])
@login_required
def save():
    category_id = request.form.get('category_id', type=int)
    amount = float(request.form.get('amount', 0.0))
    month = request.form.get('month', date.today().month, type=int)
    year = request.form.get('year', date.today().year, type=int)

    if amount <= 0:
        flash('Budget amount must be greater than zero.', 'danger')
        return redirect(url_for('budgets.index', month=month, year=year))

    budget = Budget.query.filter_by(
        user_id=current_user.id,
        category_id=category_id,
        month=month,
        year=year
    ).first()

    if budget:
        budget.amount = amount
    else:
        budget = Budget(
            user_id=current_user.id,
            category_id=category_id,
            amount=amount,
            month=month,
            year=year
        )
        db.session.add(budget)

    db.session.commit()
    cat_name = budget.category.category_name if budget.category else 'Category'
    flash(f'Budget for "{cat_name}" set to ${amount:,.2f} for {calendar.month_name[month]} {year}.', 'success')
    return redirect(url_for('budgets.index', month=month, year=year))


@budgets_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    m, y = budget.month, budget.year
    db.session.delete(budget)
    db.session.commit()
    flash('Budget removed.', 'info')
    return redirect(url_for('budgets.index', month=m, year=y))


@budgets_bp.route('/apply-ai-recommendations', methods=['POST'])
@login_required
def apply_recommendations():
    """Applies AI-suggested budget amounts for all categories for the current month."""
    today = date.today()
    recs = FinancialRecommender.generate_budget_recommendations(current_user.id)
    applied_count = 0

    for r in recs:
        cat = Category.query.filter_by(user_id=current_user.id, category_name=r['category_name']).first()
        if cat and r['recommended_budget'] > 0:
            b = Budget.query.filter_by(user_id=current_user.id, category_id=cat.id, month=today.month, year=today.year).first()
            if b:
                b.amount = r['recommended_budget']
            else:
                b = Budget(user_id=current_user.id, category_id=cat.id, amount=r['recommended_budget'], month=today.month, year=today.year)
                db.session.add(b)
            applied_count += 1

    db.session.commit()
    flash(f'Successfully adopted AI budget recommendations for {applied_count} categories!', 'success')
    return redirect(url_for('budgets.index', month=today.month, year=today.year))
