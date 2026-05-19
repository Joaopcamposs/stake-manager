from config import settings
from fastapi import Request, Response
from itsdangerous import URLSafeSerializer

serializer = URLSafeSerializer(settings.session_secret)


def create_session_cookie(response: Response) -> Response:
    data = serializer.dumps({"authenticated": True})
    response.set_cookie(
        key="session",
        value=data,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


def clear_session_cookie(response: Response) -> Response:
    response.delete_cookie(key="session")
    return response


def verify_session(request: Request) -> bool:
    cookie = request.cookies.get("session")
    if not cookie:
        return False
    try:
        data = serializer.loads(cookie)
        return data.get("authenticated", False)
    except Exception:
        return False
