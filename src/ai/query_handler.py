from src.services.ai_assistant_service import AIAssistantService

class QueryHandler:
    @staticmethod
    def handle(query, context=None, conversation_id=None):
        return AIAssistantService.answer_query(query, context, conversation_id=conversation_id)
