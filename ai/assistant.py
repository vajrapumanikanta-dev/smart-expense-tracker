import re
import os
import calendar
from datetime import date, datetime, timedelta
from sqlalchemy import func, extract
from models import db
from models.transaction import Transaction
from models.category import Category
from models.account import Account
from models.budget import Budget
from models.recurring import RecurringExpense
from models.goal import FinancialGoal
from ai.insights import FinancialInsightsEngine


class FinancialAssistant:
    """
    Natural Language Financial Assistant with Safe Structured Query Execution.
    Translates user questions into validated SQLAlchemy ORM queries and provides
    contextual financial insights.
    """

    @classmethod
    def ask(cls, query_text, user_id):
        """
        Processes a natural language question and returns a structured response with data and narrative.
        """
        text = query_text.strip().lower()
        today = date.today()
        current_year = today.year
        current_month = today.month

        # Intent 1: Total Balance Across Accounts
        if any(w in text for w in ["total balance", "net worth", "account balance", "how much money do i have", "my balance"]):
            accounts = Account.query.filter_by(user_id=user_id).all()
            total_bal = sum(float(a.balance or 0) for a in accounts)
            acc_list = [{"name": a.account_name, "type": a.account_type, "balance": float(a.balance)} for a in accounts]
            return {
                "intent": "account_balance",
                "answer": f"Your total balance across all {len(accounts)} accounts is **${total_bal:,.2f}**.",
                "data": {
                    "total_balance": total_bal,
                    "accounts": acc_list
                }
            }

        # Intent 2: Highest Expense
        if any(w in text for w in ["highest expense", "biggest expense", "largest purchase", "most expensive"]):
            highest = Transaction.query.filter_by(
                user_id=user_id,
                transaction_type='expense'
            ).order_by(Transaction.amount.desc()).first()

            if highest:
                cat_name = highest.category.category_name if highest.category else 'Uncategorized'
                return {
                    "intent": "highest_expense",
                    "answer": f"Your highest recorded expense is **${float(highest.amount):,.2f}** for *'{highest.description or cat_name}'* ({cat_name}) on {highest.transaction_date.strftime('%B %d, %Y')}.",
                    "data": highest.to_dict()
                }
            else:
                return {
                    "intent": "highest_expense",
                    "answer": "You don't have any expense transactions recorded yet.",
                    "data": None
                }

        # Intent 3: Spending on a Specific Category
        # Check if user mentioned a category name
        categories = Category.query.filter_by(user_id=user_id).all()
        matched_cat = None
        for cat in categories:
            # Check direct name or aliases
            words = cat.category_name.lower().replace('&', '').split()
            if cat.category_name.lower() in text or any(w in text for w in words if len(w) > 3):
                matched_cat = cat
                break

        if matched_cat and any(w in text for w in ["how much", "spent", "spending", "total", "cost"]):
            # Check if for specific month or current month
            target_month = current_month
            target_year = current_year
            
            # Simple month detector
            for m_idx in range(1, 13):
                m_name = calendar.month_name[m_idx].lower()
                if m_name in text:
                    target_month = m_idx
                    break

            start_d = date(target_year, target_month, 1)
            last_day = calendar.monthrange(target_year, target_month)[1]
            end_d = date(target_year, target_month, last_day)

            total_spent = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == matched_cat.id,
                Transaction.transaction_type == 'expense',
                Transaction.transaction_date >= start_d,
                Transaction.transaction_date <= end_d
            ).scalar() or 0.0

            m_label = calendar.month_name[target_month]
            return {
                "intent": "category_spending",
                "answer": f"You spent **${float(total_spent):,.2f}** on **{matched_cat.category_name}** in {m_label} {target_year}.",
                "data": {
                    "category": matched_cat.category_name,
                    "amount": float(total_spent),
                    "month": m_label,
                    "year": target_year
                }
            }

        # Intent 4: Financial Health Score
        if any(w in text for w in ["health score", "financial score", "health grade", "how am i doing financially", "score"]):
            health = FinancialInsightsEngine.calculate_financial_health_score(user_id)
            return {
                "intent": "financial_health",
                "answer": f"Your current Financial Health Score is **{health['score']}/100 ({health['grade']})**.\n\n"
                          f"• **Savings Rate**: {health['savings_rate']}% (${health['monthly_savings']:,.2f} saved this month)\n"
                          f"• **Budget Adherence**: {health['budget_score']}/30 pts\n"
                          f"• **Fixed Commitments**: ${health['monthly_recurring']:,.2f}/mo ({health['recurring_score']}/20 pts)",
                "data": health
            }

        # Intent 5: Recurring Bills / Subscriptions
        if any(w in text for w in ["recurring", "subscriptions", "upcoming bills", "due dates", "bills"]):
            recurrings = RecurringExpense.query.filter_by(user_id=user_id, active=True).order_by(RecurringExpense.next_due_date.asc()).all()
            if recurrings:
                total_rec = sum(float(r.amount) for r in recurrings)
                items = [f"• **{r.name}**: ${float(r.amount):,.2f} ({r.frequency}, next due {r.next_due_date.strftime('%b %d')})" for r in recurrings[:5]]
                return {
                    "intent": "recurring_expenses",
                    "answer": f"You have **{len(recurrings)} active recurring expenses** totaling approx. **${total_rec:,.2f}**:\n\n" + "\n".join(items),
                    "data": [r.to_dict() for r in recurrings]
                }
            else:
                return {
                    "intent": "recurring_expenses",
                    "answer": "You don't have any active recurring bills or subscriptions set up yet.",
                    "data": []
                }

        # Intent 6: Financial Goals
        if any(w in text for w in ["goals", "savings goal", "target", "emergency fund"]):
            goals = FinancialGoal.query.filter_by(user_id=user_id).all()
            if goals:
                items = [f"• **{g.name}**: ${float(g.current_amount):,.2f} / ${float(g.target_amount):,.2f} ({g.progress_percentage}% achieved)" for g in goals]
                return {
                    "intent": "goals",
                    "answer": f"Here is the status of your **{len(goals)} financial goals**:\n\n" + "\n".join(items),
                    "data": [g.to_dict() for g in goals]
                }
            else:
                return {
                    "intent": "goals",
                    "answer": "You haven't set up any savings goals yet. You can create one in the Goals section!",
                    "data": []
                }

        # Intent 7: Monthly Spending Summary / Income vs Expense
        start_d = date(current_year, current_month, 1)
        income_sum = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'income',
            Transaction.transaction_date >= start_d
        ).scalar() or 0.0

        expense_sum = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == 'expense',
            Transaction.transaction_date >= start_d
        ).scalar() or 0.0

        net_saved = float(income_sum) - float(expense_sum)
        month_label = calendar.month_name[current_month]

        # Check for Gemini LLM advisory if API key is provided and question is conversational
        gemini_api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if gemini_api_key and not any(w in text for w in ["summary", "monthly summary", "overview", "how much spent this month"]):
            try:
                from google import genai
                client = genai.Client(api_key=gemini_api_key)

                # Assemble concise user financial context
                accounts = Account.query.filter_by(user_id=user_id).all()
                total_bal = sum(float(a.balance or 0) for a in accounts)
                health = FinancialInsightsEngine.calculate_financial_health_score(user_id)
                
                context_prompt = (
                    f"You are a friendly, highly competent AI Personal Finance Advisor named SmartExpense Assistant. "
                    f"User's current financial profile:\n"
                    f"- Total Balance: ${total_bal:,.2f}\n"
                    f"- Current Month ({month_label} {current_year}) Income: ${float(income_sum):,.2f}\n"
                    f"- Current Month Expenses: ${float(expense_sum):,.2f}\n"
                    f"- Net Savings This Month: ${net_saved:,.2f}\n"
                    f"- Financial Health Score: {health['score']}/100 ({health['grade']})\n"
                    f"- Savings Rate: {health['savings_rate']}%\n\n"
                    f"User's Question: {query_text}\n\n"
                    f"Provide a clear, helpful, encouraging, and concise response using Markdown formatting where appropriate."
                )

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=context_prompt
                )
                if response and response.text:
                    return {
                        "intent": "ai_advisory",
                        "answer": response.text.strip(),
                        "data": {
                            "month": month_label,
                            "year": current_year,
                            "income": float(income_sum),
                            "expense": float(expense_sum),
                            "total_balance": total_bal
                        }
                    }
            except Exception:
                pass  # Clean fallback to deterministic local summary

        return {
            "intent": "general_monthly_summary",
            "answer": f"Here is your financial summary for **{month_label} {current_year}** so far:\n\n"
                      f"• **Total Income**: ${float(income_sum):,.2f}\n"
                      f"• **Total Expenses**: ${float(expense_sum):,.2f}\n"
                      f"• **Net Savings**: ${net_saved:,.2f}\n\n"
                      f"You can ask me questions about specific categories, highest expenses, account balances, or upcoming bills!",
            "data": {
                "month": month_label,
                "year": current_year,
                "income": float(income_sum),
                "expense": float(expense_sum),
                "net_savings": net_saved
            }
        }

