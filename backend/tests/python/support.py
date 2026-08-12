import asyncio
import os
import unittest
import warnings
from uuid import uuid4

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

os.environ.setdefault(
    "SECRET_KEY",
    "python-test-suite-secret-key-not-for-production",
)

from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.src import database, main
from backend.src.config import settings
from backend.src.models import Base


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.database_url = os.environ.get(
            "TEST_DATABASE_URL",
            settings.database_url,
        )
        if make_url(self.database_url).get_backend_name() != "postgresql":
            raise RuntimeError(
                "Python integration tests require a PostgreSQL database URL"
            )

        self.schema_name = f"test_{uuid4().hex}"
        self.engine = create_async_engine(
            self.database_url,
            connect_args={
                "options": f"-csearch_path={self.schema_name}",
            },
            poolclass=NullPool,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

        asyncio.run(self._create_schema())

        self.original_engine = main.engine
        self.original_session_factory = database.AsyncSessionLocal
        main.engine = self.engine
        database.AsyncSessionLocal = self.session_factory

        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        main.engine = self.original_engine
        database.AsyncSessionLocal = self.original_session_factory
        asyncio.run(self._drop_schema())

    async def _create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(CreateSchema(self.schema_name))
            await connection.run_sync(Base.metadata.create_all)

    async def _drop_schema(self) -> None:
        try:
            async with self.engine.begin() as connection:
                await connection.execute(
                    DropSchema(self.schema_name, cascade=True)
                )
        finally:
            await self.engine.dispose()

    @staticmethod
    def _postgres_query(query: str) -> str:
        return query.replace("?", "%s")

    def database_rows(
        self,
        query: str,
        parameters: tuple = (),
    ) -> list[tuple]:
        async def fetch_rows() -> list[tuple]:
            async with self.engine.connect() as connection:
                result = await connection.exec_driver_sql(
                    self._postgres_query(query),
                    parameters,
                )
                return [tuple(row) for row in result.fetchall()]

        return self.client.portal.call(fetch_rows)

    def execute_sql(self, query: str, parameters: tuple = ()) -> None:
        async def execute() -> None:
            async with self.engine.begin() as connection:
                await connection.exec_driver_sql(
                    self._postgres_query(query),
                    parameters,
                )

        self.client.portal.call(execute)

    def register(
        self,
        email: str = "user@example.com",
        password: str = "password123",
    ):
        return self.client.post(
            "/users/register",
            json={"email": email, "password": password},
        )

    def login(
        self,
        email: str = "user@example.com",
        password: str = "password123",
    ):
        return self.client.post(
            "/users/login",
            json={"email": email, "password": password},
        )

    def identity_with_prefix(self, prefix: str) -> str:
        return next(
            identity
            for identity in main.app.state.roots
            if identity.startswith(prefix)
        )
