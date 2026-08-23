import hashlib
import hmac

from itsdangerous import BadData, URLSafeTimedSerializer
from pwdlib import PasswordHash

from .config import settings

pwd_context = PasswordHash.recommended()
_RESET_TOKEN_SALT = "password-reset"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _reset_fingerprint(password_hash: str) -> str:
    return hmac.new(
        settings.secret_key.get_secret_value().encode(),
        password_hash.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_password_reset_token(user_id: int, password_hash: str) -> str:
    serializer = URLSafeTimedSerializer(settings.secret_key.get_secret_value())
    return serializer.dumps(
        {"user_id": user_id, "fingerprint": _reset_fingerprint(password_hash)},
        salt=_RESET_TOKEN_SALT,
    )


def decode_password_reset_token(token: str) -> tuple[int, str] | None:
    serializer = URLSafeTimedSerializer(settings.secret_key.get_secret_value())

    try:
        payload = serializer.loads(
            token,
            salt=_RESET_TOKEN_SALT,
            max_age=settings.reset_token_expire_minutes * 60,
        )
    except BadData:
        return None

    if not isinstance(payload, dict):
        return None

    user_id = payload.get("user_id")
    fingerprint = payload.get("fingerprint")
    if (
        not isinstance(user_id, int)
        or user_id <= 0
        or not isinstance(fingerprint, str)
    ):
        return None

    return user_id, fingerprint


def password_reset_token_matches(password_hash: str, fingerprint: str) -> bool:
    return hmac.compare_digest(_reset_fingerprint(password_hash), fingerprint)
