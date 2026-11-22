import pytest
from src.ai.chatbot import Chatbot

def test_ai_copilot():
    bot = Chatbot()
    ans = bot.chat('What is Model 02 accuracy?')
    assert '97.52%' in ans['message'] or '97.52%' in ans['response']
