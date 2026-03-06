import asyncio
import datetime
import decimal
import enum
import functools
import json
import uuid
from typing import Any, AsyncGenerator, Callable, Coroutine, Literal, Optional, TypeVar

from loguru import logger
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    JSON,
    Numeric,
    String,
    TypeDecorator,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# --- Configuration ---
# In a real application, these would come from environment variables or a config file.
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/invoicedb"
# Example for SQLite for quick local testing (uncomment if needed)
# DATABASE_URL = "sqlite+aiosqlite:///./invoiceiq.db"

# --- Logging Setup ---
logger.add(
    "invoiceiq.log",
    rotation="10 MB",
    compression="zip",
    level="INFO",
    format="{time} {level} {message}",
)


# --- Retry Decorator ---
R = TypeVar("R")


def retry_async(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    catch_exceptions: tuple[type[Exception], ...] = (
        ConnectionRefusedError,
        TimeoutError,
        OSError,
    ),
) -> Callable[[Callable[..., Coroutine[Any, Any, R]]], Callable[..., Coroutine[Any, Any, R]]]:
    """
    A decorator to retry an async function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts.
        initial_delay: Initial delay in seconds before the first retry.
        backoff_factor: Factor by which the delay increases each attempt.
        catch_exceptions: Tuple of exception types to catch and retry on.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, R]]) -> Callable[..., Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except catch_exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_attempts} attempts. "
                            f"Last error: {e}"
                        )
                        raise
                    logger.warning(
                        f"Function '{func.__name__}' failed (attempt {attempt}/{max_attempts}). "
                        f"Retrying in {delay:.2f} seconds. Error: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
                except Exception as e:
                    logger.error(
                        f"Function '{func.__name__}' encountered an unexpected error: {e}"
                    )
                    raise

        return wrapper

    return decorator


# --- Custom Type for UUID (Alembic compatibility) ---
class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    String type and stores UUIDs as strings.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value

    def copy(self, **kw):
        return GUID(self.impl.length)


# --- Invoice Status Enum ---
class InvoiceStatus(enum.Enum):
    """
    Represents the processing status of an invoice.
    """

    PENDING = "pending"
    EXTRACTED = "extracted"
    REVIEWED = "reviewed"
    EXPORTED = "exported"

    def __str__(self) -> str:
        return self.value


# --- SQLAlchemy Base ---
class Base(DeclarativeBase):
    """
    Base class for all declarative models, compatible with Alembic.
    """

    pass


# --- Invoice Model ---
class Invoice(Base):
    """
    Represents an invoice document in the InvoiceIQ system.
    """

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        default=InvoiceStatus.PENDING,
        nullable=False,
    )
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    tax: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    total: Mapped[Optional[decimal.Decimal]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    line_items: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=lambda: {}, nullable=False
    )
    confidence_scores: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=lambda: {}, nullable=False
    )
    exported_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(id='{self.id}', file_name='{self.file_name}', "
            f"status='{self.status.value}', total={self.total})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the Invoice object to a dictionary, handling special types.
        """
        data = {
            "id": str(self.id),
            "file_name": self.file_name,
            "file_type": self.file_type,
            "status": self.status.value,
            "vendor_name": self.vendor_name,
            "invoice_number": self.invoice_number,
            "invoice_date": (
                self.invoice_date.isoformat() if self.invoice_date else None
            ),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "subtotal": str(self.subtotal) if self.subtotal is not None else None,
            "tax": str(self.tax) if self.tax is not None else None,
            "total": str(self.total) if self.total is not None else None,
            "currency": self.currency,
            "line_items": self.line_items,
            "confidence_scores": self.confidence_scores,
            "exported_at": (
                self.exported_at.isoformat() if self.exported_at else None
            ),
            "created_at": self.created_at.isoformat(),
        }
        return data


# --- Async Database Engine and Session Factory ---
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


@retry_async(max_attempts=3, initial_delay=2.0)
async def init_db() -> None:
    """
    Initializes the database by creating all tables defined in Base.
    This function is typically used for development/testing.
    For production, Alembic migrations are preferred.
    """
    logger.info("Attempting to connect to the database and create tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully (if they didn't exist).")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injector for FastAPI or similar frameworks to get an async database session.
    Yields an AsyncSession and ensures it's closed after use.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()


# --- Example Usage (for demonstration) ---
async def main() -> None:
    """
    Demonstrates how to use the Invoice model and database setup.
    """
    logger.info("Starting InvoiceIQ database model demonstration.")

    # Initialize DB (create tables if they don't exist)
    await init_db()

    # Create a new invoice
    async with AsyncSessionFactory() as session:
        new_invoice = Invoice(
            file_name="invoice_123.pdf",
            file_type="application/pdf",
            vendor_name="Acme Corp",
            invoice_number="INV-2023-001",
            invoice_date=datetime.date(2023, 10, 26),
            due_date=datetime.date(2023, 11, 26),
            subtotal=decimal.Decimal("99.99"),
            tax=decimal.Decimal("5.00"),
            total=decimal.Decimal("104.99"),
            currency="EUR",
            line_items=[
                {"description": "Product A", "quantity": 1, "unit_price": "99.99"}
            ],
            confidence_scores={"vendor_name": 0.95, "total": 0.98},
        )
        session.add(new_invoice)
        await session.commit()
        await session.refresh(new_invoice)
        logger.info(f"Created new invoice: {new_invoice}")
        logger.info(f"Invoice as dict: {json.dumps(new_invoice.to_dict(), indent=2)}")

    # Fetch an invoice
    async with AsyncSessionFactory() as session:
        fetched_invoice: Optional[Invoice] = await session.get(Invoice, new_invoice.id)
        if fetched_invoice:
            logger.info(f"Fetched invoice: {fetched_invoice}")
            logger.info(f"Fetched invoice status: {fetched_invoice.status}")
            logger.info(f"Fetched invoice line items: {fetched_invoice.line_items}")
        else:
            logger.warning(f"Invoice with ID {new_invoice.id} not found.")

    # Update an invoice
    async with AsyncSessionFactory() as session:
        invoice_to_update: Optional[Invoice] = await session.get(Invoice, new_invoice.id)
        if invoice_to_update:
            invoice_to_update.status = InvoiceStatus.REVIEWED
            invoice_to_update.exported_at = datetime.datetime.now(datetime.timezone.utc)
            invoice_to_update.line_items.append(
                {"description": "Shipping", "quantity": 1, "unit_price": "10.00"}
            )
            # Mark JSON field as modified for SQLAlchemy to detect changes
            # For mutable types like dict/list, SQLAlchemy might not detect changes
            # unless you reassign or use mutable_scalar. For simple dict appends,
            # it often works, but explicit marking is safer.
            # For SQLAlchemy 2.0, direct modification of JSON fields is often detected.
            # If not, you might need:
            # from sqlalchemy.dialects.postgresql import JSONB
            # from sqlalchemy.orm.attributes import flag_modified
            # flag_modified(invoice_to_update, "line_items")

            await session.commit()
            await session.refresh(invoice_to_update)
            logger.info(f"Updated invoice: {invoice_to_update}")
            logger.info(f"Updated invoice status: {invoice_to_update.status}")
            logger.info(f"Updated invoice exported_at: {invoice_to_update.exported_at}")
            logger.info(f"Updated invoice line items: {invoice_to_update.line_items}")
        else:
            logger.warning(f"Invoice with ID {new_invoice.id} not found for update.")

    # Clean up (optional: delete the created invoice)
    async with AsyncSessionFactory() as session:
        invoice_to_delete: Optional[Invoice] = await session.get(Invoice, new_invoice.id)
        if invoice_to_delete:
            await session.delete(invoice_to_delete)
            await session.commit()
            logger.info(f"Deleted invoice with ID: {new_invoice.id}")
        else:
            logger.warning(f"Invoice with ID {new_invoice.id} not found for deletion.")

    logger.info("InvoiceIQ database model demonstration finished.")


if __name__ == "__main__":
    # To run this example:
    # 1. Make sure you have a PostgreSQL database running and accessible.
    # 2. Update DATABASE_URL with your credentials.
    # 3. Install dependencies:
    #    pip install sqlalchemy asyncpg loguru
    #    (If using SQLite: pip install sqlalchemy aiosqlite loguru)
    # 4. Run the script: python your_script_name.py
    asyncio.run(main())