from .auth_routes import auth_bp
from .shipment_routes import shipment_bp
from .report_routes import report_bp
from .exception_routes import exception_bp
from .ai_assistant_routes import ai_bp, api_chat, chat_history, clear_chat_session
from .escalation_routes import escalation_bp
from .communication_routes import comm_bp
from .user_routes import user_bp
from .admin_routes import admin_bp
from .api_v1_routes import api_v1_bp
from .dashboard_routes import dashboard_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shipment_bp, url_prefix='/shipments')
    app.register_blueprint(report_bp, url_prefix='/reports')
    app.register_blueprint(exception_bp, url_prefix='/exceptions')
    app.register_blueprint(ai_bp, url_prefix='/ai/assistant')
    app.register_blueprint(escalation_bp, url_prefix='/escalations')
    app.register_blueprint(comm_bp, url_prefix='/communications')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_v1_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    
    # Global AI Assistant Routes & Aliases
    @app.route('/ai-assistant')
    @app.route('/ai-assistant/')
    def redirect_ai():
        from flask import redirect
        return redirect('/ai/assistant')

    @app.route('/api/chat', methods=['POST'])
    @app.route('/ai-assistant/api/chat', methods=['POST'])
    def global_api_chat():
        return api_chat()

    @app.route('/api/chat/history', methods=['GET'])
    @app.route('/ai-assistant/api/chat/history', methods=['GET'])
    def global_chat_history():
        return chat_history()

    @app.route('/api/chat/clear', methods=['POST'])
    @app.route('/ai-assistant/api/chat/clear', methods=['POST'])
    def global_clear_chat():
        return clear_chat_session()

    @app.route('/ai/communications')
    @app.route('/ai/communications/')
    def alias_ai_communications():
        from flask import redirect
        return redirect('/communications/')
