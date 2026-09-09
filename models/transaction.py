from datetime import datetime, date
from models import db


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'expense' or 'income'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    transaction_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    is_recurring = db.Column(db.Boolean, default=False)
    is_anomaly = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'account_name': self.account.account_name if self.account else 'Unknown',
            'category_id': self.category_id,
            'category_name': self.category.category_name if self.category else 'Uncategorized',
            'category_color': self.category.color if self.category else '#94a3b8',
            'category_icon': self.category.icon if self.category else 'receipt',
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'description': self.description or '',
            'transaction_date': self.transaction_date.strftime('%Y-%m-%d') if self.transaction_date else '',
            'is_recurring': self.is_recurring,
            'is_anomaly': self.is_anomaly,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

    def __repr__(self):
        return f'<Transaction #{self.id}: {self.transaction_type} {self.amount} - {self.description}>'
