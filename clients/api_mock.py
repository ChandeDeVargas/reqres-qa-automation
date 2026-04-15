"""
clients/api_mock.py
───────────────────
Mock generator for ReqRes API. Bypasses the need for real API calls and API keys.
Simulates exactly the paginated responses of GET /users and GET /users/{id}.
"""

import re
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

def get_mock_response(method: str, path: str, params: dict | None) -> APIResponse:
    """Returns an APIResponse with simulated ReqRes data."""
    if method.upper() != "GET":
        # Only GET /users and GET /users/{id} are fully mocked right now
        return APIResponse(status=200, body={}, headers={}, elapsed_ms=15.0)

    # Normalize path
    clean_path = path.lstrip("/")

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
        total_pages = -(-total // per_page) # ceiling division
        
        # Slicing for pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # If page is completely out of bounds (e.g. page 30), return empty data
        if start_idx >= total:
            data = []
        else:
            data = USERS[start_idx:end_idx]

        body = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "data": data,
            "support": SUPPORT
        }
        return APIResponse(status=200, body=body, headers={}, elapsed_ms=12.0)

    # Regex to match /users/{id}
    match = re.match(r"^users/(\d+)$", clean_path)
    if match:
        user_id = int(match.group(1))
        # Find user
        user = next((u for u in USERS if u["id"] == user_id), None)
        if user:
            body = {
                "data": user,
                "support": SUPPORT
            }
            return APIResponse(status=200, body=body, headers={}, elapsed_ms=10.0)
        else:
            # 404
            return APIResponse(status=404, body={}, headers={}, elapsed_ms=8.0)

    # Fallback mock for anything else
    return APIResponse(status=200, body={}, headers={}, elapsed_ms=5.0)
