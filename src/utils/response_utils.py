from flask import jsonify

def success_response(data=None, message="Success", status_code=200):
    payload = {"status": "success", "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code

def error_response(message="An error occurred", code="ERROR", status_code=400, details=None):
    payload = {
        "status": "error",
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code
