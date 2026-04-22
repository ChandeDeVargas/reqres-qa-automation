"""
clients/api_mock.py
───────────────────
Mock generator for ReqRes API. Bypasses the need for real API calls and API keys.
Simulates exactly the paginated responses of GET /users and POST schemas.
"""

import re
import datetime
from clients.api_client import APIResponse

# 12 seed users like the real ReqRes
USERS = [
    {"id": i, "email": f"eve.holt{i}@reqres.in", "first_name": "Eve", "last_name": f"Holt{i}", "avatar": f"https://reqres.in/img/faces/{i}-image.jpg"}
    for i in range(1, 13)
]

SUPPORT = {
    "url": "https://reqres.in/#support-heading",
    "text": "To keep ReqRes free, contributions towards server costs are appreciated!"
}

# Unique ID generator state for tests that assert uniqueness
_mock_id_counter = 500

def get_mock_response(method: str, path: str, params: dict | None = None, data: dict | None = None) -> APIResponse:
    """Returns an APIResponse with simulated ReqRes data."""
    global _mock_id_counter
    clean_path = path.lstrip("/")

    if method.upper() == "GET":
        if clean_path == "users":
            # GET /users
            page = 1
            per_page = 6
            if params and "page" in params:
                 try:
                     page = int(params["page"])
                 except ValueError:
                     pass
            
            total = len(USERS)
            total_pages = -(-total // per_page)
            
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            if start_idx >= total:
                data_list = []
            else:
                data_list = USERS[start_idx:end_idx]

            body = {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "data": data_list,
                "support": SUPPORT
            }
            return APIResponse(status=200, body=body, headers={}, elapsed_ms=12.0)

        # GET /users/{id}
        match = re.match(r"^users/(.+)$", clean_path)
        if match:
            id_str = match.group(1)
            if not id_str.isdigit():
                return APIResponse(status=404, body={}, headers={}, elapsed_ms=8.0)
            user_id = int(id_str)
            user = next((u for u in USERS if u["id"] == user_id), None)
            if user:
                body = {
                    "data": user,
                    "support": SUPPORT
                }
                return APIResponse(status=200, body=body, headers={}, elapsed_ms=10.0)
            else:
                return APIResponse(status=404, body={}, headers={}, elapsed_ms=8.0)

    elif method.upper() == "POST":
        if clean_path == "users":
            # POST /users
            _mock_id_counter += 1
            body = data.copy() if data else {}
            body["id"] = str(_mock_id_counter)
            body["createdAt"] = datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')
            return APIResponse(status=201, body=body, headers={}, elapsed_ms=15.0)

        elif clean_path == "login":
            # POST /login
            if not data or not data.get("email"):
                return APIResponse(status=400, body={"error": "Missing email or username"}, headers={}, elapsed_ms=10.0)
            if not data.get("password"):
                return APIResponse(status=400, body={"error": "Missing password"}, headers={}, elapsed_ms=10.0)
            
            from config import settings
            if data["email"] != settings.TEST_EMAIL:
                return APIResponse(status=400, body={"error": "user not found"}, headers={}, elapsed_ms=10.0)
            if data["password"] != settings.TEST_PASSWORD:
                return APIResponse(status=400, body={"error": "invalid password"}, headers={}, elapsed_ms=10.0)
                
            return APIResponse(status=200, body={"token": "QpwL5tke4Pnpja7X4"}, headers={}, elapsed_ms=15.0)

        elif clean_path == "register":
            # POST /register
            if not data or not data.get("email"):
                return APIResponse(status=400, body={"error": "Missing email or username"}, headers={}, elapsed_ms=10.0)
            if not data.get("password"):
                return APIResponse(status=400, body={"error": "Missing password"}, headers={}, elapsed_ms=10.0)
            
            from config import settings
            if data["email"] != settings.TEST_EMAIL:
                return APIResponse(status=400, body={"error": "Note: Only defined users succeed registration"}, headers={}, elapsed_ms=10.0)
                
            return APIResponse(status=200, body={"id": 4, "token": "QpwL5tke4Pnpja7X4"}, headers={}, elapsed_ms=15.0)

    elif method.upper() in ("PUT", "PATCH"):
        match = re.match(r"^users/(\d+)$", clean_path)
        if match:
            body = data.copy() if data else {}
            body["updatedAt"] = datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')
            return APIResponse(status=200, body=body, headers={}, elapsed_ms=12.0)

    elif method.upper() == "DELETE":
        match = re.match(r"^users/(\d+)$", clean_path)
        if match:
            return APIResponse(status=204, body=None, headers={}, elapsed_ms=10.0, raw_text="")

    # Fallback mock for anything else
    return APIResponse(status=200, body={}, headers={}, elapsed_ms=5.0)
