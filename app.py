import os
from flask import Flask, render_template
from flask_login import LoginManager
from dotenv import load_dotenv

from config import config_by_name
from models import db, User
from routes import register_blueprints


def create_app(config_name=None):
    """Application factory for AI-Powered Expense Tracker."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Ensure database, exports, and ml_models folders exist
    os.makedirs(os.path.join(app.root_path, 'database'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'exports'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'ml_models'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access your financial dashboard.'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register all blueprints
    register_blueprints(app)

    # Custom Jinja filters
    @app.template_filter('currency')
    def currency_filter(val):
        try:
            return f"${float(val):,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @app.template_filter('format_date')
    def date_filter(d, fmt='%b %d, %Y'):
        if not d:
            return ''
        if isinstance(d, str):
            try:
                from datetime import datetime
                d = datetime.strptime(d[:10], '%Y-%m-%d')
            except Exception:
                return d
        return d.strftime(fmt)

    # Global context processor
    @app.context_processor
    def inject_globals():
        from models.notification import Notification
        from models.account import Account
        from flask_login import current_user
        unread_notifs = 0
        user_accounts = []
        if current_user.is_authenticated:
            unread_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            user_accounts = Account.query.filter_by(user_id=current_user.id).all()
        return dict(unread_notifications_count=unread_notifs, accounts=user_accounts)

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Auto-create tables on launch
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
