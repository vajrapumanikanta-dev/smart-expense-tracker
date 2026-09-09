from flask import Blueprint

def register_blueprints(app):
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.transactions import transactions_bp
    from routes.accounts import accounts_bp
    from routes.budgets import budgets_bp
    from routes.recurring import recurring_bp
    from routes.goals import goals_bp
    from routes.reports import reports_bp
    from routes.ai import ai_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    app.register_blueprint(accounts_bp, url_prefix='/accounts')
    app.register_blueprint(budgets_bp, url_prefix='/budgets')
    app.register_blueprint(recurring_bp, url_prefix='/recurring')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
