import ctypes
from datetime import UTC, datetime
import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..auth import (
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    password_reset_token_matches,
    verify_password,
)
from ..crud import create_user_with_entries, get_user_by_email, get_user_by_id
from ..dependencies import DatabaseSession, Identity, get_current_user
from ..email_utils import send_password_reset_email
from ..models import User
from ..schema import (
    PasswordResetConfirm,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
    UserRead,
)
from ..trie_state import discard_root, get_trie_words, locked_root

router = APIRouter()
logger = logging.getLogger(__name__)
_RESET_REQUEST_RESPONSE = {
    "message": "If an account exists for that email, a password reset link has been sent."
}
_INVALID_RESET_TOKEN = "This password reset link is invalid or has expired"


async def _deliver_password_reset_email(to_email: str, token: str) -> None:
    try:
        await send_password_reset_email(to_email, token)
    except Exception:
        logger.exception("Could not deliver password reset email")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    identity: Identity,
    user_data: UserCreate,
    session: DatabaseSession,
) -> User:
    existing_user = await get_user_by_email(session, user_data.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    user = User(
        email=user_data.email.lower(),
        password_hash=hash_password(user_data.password),
        created_at=datetime.now(UTC)
    )

    try:
        if identity.startswith("guest:"):
            async with locked_root(request, identity, session) as guest_root:
                guest_entries = get_trie_words(request.app, guest_root)
                await create_user_with_entries(session, user, guest_entries)
                discard_root(request.app, identity)
        else:
            await create_user_with_entries(session, user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user"
        )

    request.session.clear()
    request.session["identity"] = f"user:{user.id}"

    return user


@router.post("/login", response_model=UserRead)
async def login(
    request: Request,
    credentials: UserLogin,
    session: DatabaseSession,
) -> User:
    user = await get_user_by_email(session, credentials.email)

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    request.session.clear()
    request.session["identity"] = f"user:{user.id}"

    return user


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
) -> dict[str, str]:
    user = await get_user_by_email(session, reset_request.email)

    if user is not None:
        token = create_password_reset_token(user.id, user.password_hash)
        background_tasks.add_task(
            _deliver_password_reset_email,
            user.email,
            token,
        )

    return _RESET_REQUEST_RESPONSE


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request: Request,
    reset: PasswordResetConfirm,
    session: DatabaseSession,
) -> dict[str, str]:
    token_data = decode_password_reset_token(reset.token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVALID_RESET_TOKEN,
        )

    user_id, fingerprint = token_data
    user = await get_user_by_id(session, user_id)
    if user is None or not password_reset_token_matches(
        user.password_hash,
        fingerprint,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVALID_RESET_TOKEN,
        )

    try:
        result = await session.execute(
            update(User)
            .where(
                User.id == user.id,
                User.password_hash == user.password_hash,
            )
            .values(password_hash=hash_password(reset.password))
        )
        if result.rowcount != 1:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_INVALID_RESET_TOKEN,
            )
        await session.commit()
    except HTTPException:
        raise
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reset password",
        )

    request.session.clear()
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, session: DatabaseSession) -> Response:
    identity = request.session.get("identity")

    destroyTrieNode = request.app.state.functions["destroyTrieNode"]

    async with locked_root(request, identity, session) as root:# type: ignore
        destroyTrieNode(ctypes.byref(root))
        
    request.session.clear()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
