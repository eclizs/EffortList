import ctypes
import re

from typing import Annotated
from fastapi import Body, Form, status, FastAPI, Query, Request, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from .crud import parse_admin_csv, parse_user_csv

from .models import Entry, User

from .database import engine
from .dependencies import DatabaseSession, Identity, get_user_id
from .routers.users import router
from .trie_state import discard_root, destroy_trie_state, initialize_trie_state, locked_root
from .config import settings

re.ASCII

@asynccontextmanager
async def lifespan(app: FastAPI):
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    
    initialize_trie_state(app)

    yield

    destroy_trie_state(app)

    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key.get_secret_value(),
    max_age=24 * 60 * 60,
    same_site="lax",
    https_only=False
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.include_router(router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse("frontend/login.html")

@app.get("/register", include_in_schema=False)
async def register_page():
    return FileResponse("frontend/register.html")

@app.get("/search")
async def search_word(
    request: Request,
    identity: Identity,
    session: DatabaseSession,
    prefix: Annotated[
        str | None, Query(max_length=100, pattern=r'^[-a-zA-Z0-9 /@"()+.,]*$')
    ] = None
):
    findWords = request.app.state.functions["findWords"]
    freeWordList = request.app.state.functions["freeWordList"]

    async with locked_root(request, identity, session) as root:
        if not prefix:
            prefix = ""

        c_prefix = ctypes.create_string_buffer(prefix.encode("utf-8"))
        word_list = findWords(root, c_prefix)

        response = []

        try:
            for i in range(word_list.count):
                entry = word_list.entries[i]
                response.append(entry.decode('utf-8'))
        finally:
            freeWordList(word_list)

    if response == []:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matches found")
    return {"words": response}

@app.post("/insert")
async def insert_word(
    request: Request,
    identity: Identity,
    session: DatabaseSession,
    word: Annotated[ str, Query(max_length=100, pattern=r'^[-a-zA-Z0-9 /@"()+.,]*$') ],
):
    insertTrieNode = request.app.state.functions["insertTrieNode"]
    c_word = ctypes.create_string_buffer(word.encode("utf-8"))

    async with locked_root(request, identity, session) as root:
        user_id = get_user_id(identity)
        if user_id != -1:
            entry = Entry(
                user_id=user_id,
                entry=word
            )
            session.add(entry)

            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"this word already exists"
                )
            except SQLAlchemyError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not save word"
                )

            result = insertTrieNode(ctypes.byref(root), c_word)

            if result != status.HTTP_201_CREATED:
                await session.rollback()
            else:
                try:
                    await session.commit()
                except SQLAlchemyError:
                    await session.rollback()
                    discard_root(request.app, identity)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Unexpected response from server"
                    )
        else:
            result = insertTrieNode(ctypes.byref(root), c_word)

        if result == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty input")
        elif result == 409:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This word already exists")
        elif result == 422:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="This word has invalid characters")
        elif result == 201:
            return {"message": f"successfully inserted '{word}'"}
        else:
            discard_root(request.app, identity)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected response from server"
            )

@app.post("/insert_csv/preview", include_in_schema=False)
async def csv_preview(
    request: Request,
    identity: Identity,
    session: DatabaseSession,
    column: Annotated[str | None, Form()] = None,
    file: UploadFile = File(...),
):
    user = None

    user_id = get_user_id(identity)
    if user_id != -1:
        result = await session.execute(select(User).where(User.id == get_user_id(identity)))
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User doesn't exists"
            )

    contents = await file.read()

    if user is None or not user.is_admin:
        entries = parse_user_csv(contents, column)
    elif user.is_admin:
        entries = parse_admin_csv(contents)

    return {"entries": entries}

@app.post("/insert_csv", include_in_schema=False)
async def insert_csv(
    request: Request,
    identity: Identity,
    session: DatabaseSession,
    entries: Annotated[list[str], Body(embed=True)],
):
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="List is empty"
        )
    results = {"inserted": [], "failed": []}
    for entry in entries:
        try:
            await insert_word(request, identity, session, entry)
            results["inserted"].append(entry)
        except HTTPException as e:
            results["failed"].append({"word": entry, "reason": e.detail, "status_code": e.status_code})

    return results

@app.delete("/delete")
async def delete_word(
    request: Request,
    identity: Identity,
    session: DatabaseSession,
    word: Annotated[
        str, Query(max_length=100, pattern=r'^[-a-zA-Z0-9 /@"()+.,]*$')
    ],
):
    deleteWord = request.app.state.functions["deleteWord"]
    c_word = ctypes.create_string_buffer(word.encode("utf-8"))

    async with locked_root(request, identity, session) as root:
        user_id = get_user_id(identity)
        if user_id != -1:
            result = await session.execute(
                select(Entry).where(
                    Entry.user_id == user_id,
                    func.lower(Entry.entry) == word.lower(),
                )
            )
            entry = result.scalars().first()

            if entry is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"'{word}' not found"
                )
            await session.delete(entry)
            try:
                await session.flush()
            except SQLAlchemyError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not delete word"
                )

            result = deleteWord(ctypes.byref(root), c_word)

            if not result:
                await session.rollback()
                discard_root(request.app, identity)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stored word could not be removed from the trie"
                )

            try:
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                discard_root(request.app, identity)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not delete word"
                )
        else:
            result = deleteWord(ctypes.byref(root), c_word)

        if result == False:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"'{word}' not found"
            )
        else:
            return {"message": f"successfully deleted '{word}'"}


@app.delete("/delete_all")
async def delete_all(
    request: Request,
    identity: Identity,
    session: DatabaseSession,
):
    destroy_trie_node = request.app.state.functions["destroyTrieNode"]

    async with locked_root(request, identity, session) as root:
        user_id = get_user_id(identity)
        if user_id != -1:
            results = await session.execute(
                select(Entry).where(Entry.user_id == user_id)
            )
            entries = results.scalars().all()

            for entry in entries:
                await session.delete(entry)

            try:
                await session.flush()
            except SQLAlchemyError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not delete word from the database"
                )

            destroy_trie_node(ctypes.byref(root))

            try:
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                discard_root(request.app, identity)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not delete all words"
                )
        else:
            destroy_trie_node(ctypes.byref(root))

    return {"message": "Deleted all entries"}


@app.get("/{path:path}", include_in_schema=False)
async def not_found_page(path: str):
    return FileResponse(
        "frontend/404.html",
        status_code=status.HTTP_404_NOT_FOUND,
    )
