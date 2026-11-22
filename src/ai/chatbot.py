from src.ai.query_handler import QueryHandler

class Chatbot:
    def __init__(self):
        self.handler = QueryHandler()

    def chat(self, user_message, context=None, conversation_id=None):
        res = self.handler.handle(user_message, context, conversation_id=conversation_id)
        if isinstance(res, dict):
            res.setdefault('sender', 'RouteMind AI Copilot')
            return res
        return {
            'success': True,
            'sender': 'RouteMind AI Copilot',
            'response': res,
            'message': res,
            'conversation_id': conversation_id
        }
