from datetime import date
from models import db


class RecurringExpense(db.Model):
    __tablename__ = 'recurring_expenses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    frequency = db.Column(db.String(30), nullable=False, default='Monthly')  # Daily, Weekly, Monthly, Yearly
    next_due_date = db.Column(db.Date, nullable=False, index=True)
    last_processed_date = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'account_name': self.account.account_name if self.account else 'Unknown',
            'category_id': self.category_id,
            'category_name': self.category.category_name if self.category else 'Unknown',
            'name': self.name,
            'amount': float(self.amount),
            'frequency': self.frequency,
            'next_due_date': self.next_due_date.strftime('%Y-%m-%d') if self.next_due_date else '',
            'last_processed_date': self.last_processed_date.strftime('%Y-%m-%d') if self.last_processed_date else None,
            'active': self.active
        }

    def __repr__(self):
        return f'<RecurringExpense {self.name} - {self.amount} ({self.frequency})>'
