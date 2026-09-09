from models import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), default='Checking')  # Checking, Savings, Credit Card, Cash, Wallet, Investment
    balance = db.Column(db.Numeric(12, 2), default=0.0)

    # Relationships
    transactions = db.relationship('Transaction', backref='account', lazy=True, cascade='all, delete-orphan')
    recurring_expenses = db.relationship('RecurringExpense', backref='account', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_name': self.account_name,
            'account_type': self.account_type,
            'balance': float(self.balance or 0.0)
        }

    def __repr__(self):
        return f'<Account {self.account_name} ({self.account_type}): {self.balance}>'
