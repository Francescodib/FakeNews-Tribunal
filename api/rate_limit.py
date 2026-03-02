from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_user_id(request: Request) -> str:
    """Rate limit key: authenticated user ID when available, else IP."""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_id)
