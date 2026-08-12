from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Entry(Base):
    __tablename__ = "dict_entries"
    __table_args__ = (UniqueConstraint("user_id", "entry", name="uq_user_entry"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entry: Mapped[str] = mapped_column(String(100))

    def __repr__(self):
        return f"{self.id}: {self.entry}"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean(), default=False)

    def __repr__(self):
        return f"{self.id}: {self.email}"
