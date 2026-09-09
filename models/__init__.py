# pyrefly: ignore [missing-import]
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User
from models.account import Account
from models.category import Category
from models.transaction import Transaction
from models.budget import Budget
from models.recurring import RecurringExpense
from models.goal import FinancialGoal
from models.ai_insight import AIInsight
from models.notification import Notification

__all__ = [
    'db',
    'User',
    'Account',
    'Category',
    'Transaction',
    'Budget',
    'RecurringExpense',
    'FinancialGoal',
    'AIInsight',
    'Notification'
]
