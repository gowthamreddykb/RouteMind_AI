def format_response(text, actions=None):
    return {
        'response_text': text,
        'suggested_actions': actions or ['Acknowledge Alert', 'Escalate to Supervisor']
    }
