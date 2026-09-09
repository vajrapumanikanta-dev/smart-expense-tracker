from models import db


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=True, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1 - 12
    year = db.Column(db.Integer, nullable=False)   # e.g., 2026

    # Unique constraint per user, category, month, and year
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category_id', 'month', 'year', name='uq_user_category_month_year'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'category_name': self.category.category_name if self.category else 'Overall Monthly Budget',
            'amount': float(self.amount),
            'month': self.month,
            'year': self.year
        }

    def __repr__(self):
        cat = self.category.category_name if self.category else 'Overall'
        return f'<Budget {cat} {self.month}/{self.year}: {self.amount}>'
