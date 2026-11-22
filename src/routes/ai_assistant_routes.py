from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.ai.chatbot import Chatbot
from src.security.permissions import roles_required, ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ROLE_SUPPORT
from src.models.shipment_model import Shipment
from src.models.exception_model import ShipmentException
from src.models.chat_model import ChatConversation, ChatMessage
from extensions import db

ai_bp = Blueprint('ai_bp', __name__)
bot = Chatbot()

@ai_bp.route('/')
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ROLE_SUPPORT)
def ai_assistant():
    return render_template('ai_assistant.html')

@ai_bp.route('/api/chat', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ROLE_SUPPORT)
def api_chat():
    data = request.get_json(silent=True) or {}
    msg = data.get('message', '').strip()
    if not msg:
        # Also check 'query' or 'prompt' keys
        msg = data.get('query', '').strip() or data.get('prompt', '').strip()

    if not msg:
        return jsonify({
            'success': False,
            'sender': 'RouteMind Copilot',
            'response': 'Please provide a valid question or query.',
            'message': 'Please provide a valid question or query.'
        }), 400

    conversation_id = data.get('conversation_id')
    try:
        conversation_id = int(conversation_id) if conversation_id else None
    except (ValueError, TypeError):
        conversation_id = None

    # Query operational context
    try:
        total_active = Shipment.query.filter(Shipment.order_status != 'DELIVERED').count()
        open_exc = ShipmentException.query.filter(ShipmentException.status.in_(['OPEN', 'INVESTIGATING', 'IN_PROGRESS'])).count()
    except Exception:
        total_active = 0
        open_exc = 0

    context = {
        'user': current_user.username if current_user.is_authenticated else 'Operations Specialist',
        'role': current_user.role if current_user.is_authenticated else 'Dispatcher',
        'user_id': current_user.id if current_user.is_authenticated else None,
        'active_shipments': total_active,
        'open_exceptions': open_exc
    }

    res = bot.chat(msg, context=context, conversation_id=conversation_id)
    return jsonify(res)

@ai_bp.route('/api/chat/history', methods=['GET'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ROLE_SUPPORT)
def chat_history():
    conv_id = request.args.get('conversation_id', type=int)
    if not conv_id:
        # Find latest conversation for this user
        conv = ChatConversation.query.filter_by(user_id=current_user.id).order_by(ChatConversation.updated_at.desc()).first()
    else:
        conv = ChatConversation.query.get(conv_id)

    if not conv:
        return jsonify({'success': True, 'conversation_id': None, 'messages': []})

    messages = [m.to_dict() for m in conv.messages]
    return jsonify({
        'success': True,
        'conversation_id': conv.id,
        'title': conv.title,
        'messages': messages
    })

@ai_bp.route('/api/chat/clear', methods=['POST'])
@login_required
@roles_required(ROLE_DISPATCHER, ROLE_MANAGER, ROLE_ADMIN, ROLE_SUPPORT)
def clear_chat_session():
    data = request.get_json(silent=True) or {}
    conv_id = data.get('conversation_id')
    if conv_id:
        try:
            conv = ChatConversation.query.get(conv_id)
            if conv and (conv.user_id == current_user.id or current_user.role in [ROLE_MANAGER, ROLE_ADMIN]):
                db.session.delete(conv)
                db.session.commit()
        except Exception:
            db.session.rollback()

    return jsonify({'success': True, 'message': 'Conversation cleared successfully.'})
