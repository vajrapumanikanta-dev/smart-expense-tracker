from datetime import datetime, date
from models import db


class FinancialGoal(db.Model):
    __tablename__ = 'financial_goals'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    current_amount = db.Column(db.Numeric(12, 2), default=0.0)
    target_date = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(50), default='Savings')  # Emergency Fund, Vacation, House, Car, Investment, Debt
    status = db.Column(db.String(20), default='In Progress')  # In Progress, Achieved, Paused
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progress_percentage(self):
        if not self.target_amount or float(self.target_amount) <= 0:
            return 0.0
        pct = (float(self.current_amount or 0.0) / float(self.target_amount)) * 100
        return min(round(pct, 1), 100.0)

    @property
    def remaining_amount(self):
        rem = float(self.target_amount) - float(self.current_amount or 0.0)
        return max(rem, 0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'target_amount': float(self.target_amount),
            'current_amount': float(self.current_amount or 0.0),
            'target_date': self.target_date.strftime('%Y-%m-%d') if self.target_date else '',
            'category': self.category,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'remaining_amount': self.remaining_amount,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else ''
        }

    def __repr__(self):
        return f'<FinancialGoal {self.name}: {self.current_amount}/{self.target_amount}>'
