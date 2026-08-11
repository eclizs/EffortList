from collections.abc import Iterable
import io
import re

from pandas import read_csv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Entry, User


_MALFORMED_TRAILING_QUOTED_TOKEN = re.compile(r"(?<!\S)(\S+)\"\"$")


def _normalize_csv_entry(value: object) -> str:
    entry = str(value)
    return _MALFORMED_TRAILING_QUOTED_TOKEN.sub(r'"\1"', entry) 


async def get_user_by_email(
    session: AsyncSession,
    email: str,
) -> User | None:
    result = await session.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    return result.scalars().first()


async def get_user_by_id(
    session: AsyncSession,
    user_id: int,
) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user_with_entries(
    session: AsyncSession,
    user: User,
    entries: Iterable[str] = (),
) -> User:
    session.add(user)
    await session.flush()

    session.add_all(
        Entry(user_id=user.id, entry=entry)
        for entry in entries
    )

    await session.commit()
    return user

def parse_user_csv(contents: bytes, column: str | None) -> list[str]:
    df = read_csv(io.BytesIO(contents))
    if not column:
        values = df.iloc[:, 0]
    else:
        values = df[column]

    return [_normalize_csv_entry(value) for value in values]

def parse_admin_csv(contents: bytes) -> list[str]:
    df = read_csv(io.BytesIO(contents), header=None)

    values = [_normalize_csv_entry(value) for value in df[df.columns[2]]]

    return [re.sub(r'"\w+"', "", value).strip() for value in values]
