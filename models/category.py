from models import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category_name = db.Column(db.String(100), nullable=False)
    category_type = db.Column(db.String(20), nullable=False)  # 'expense' or 'income'
    icon = db.Column(db.String(50), default='folder')
    color = db.Column(db.String(20), default='#6366f1')

    # Relationships
    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True, cascade='all, delete-orphan')
    recurring_expenses = db.relationship('RecurringExpense', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category_name': self.category_name,
            'category_type': self.category_type,
            'icon': self.icon,
            'color': self.color
        }

    def __repr__(self):
        return f'<Category {self.category_name} ({self.category_type})>'
