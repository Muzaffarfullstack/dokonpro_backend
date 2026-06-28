import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import ActiveMixin, BaseEntity, StoreScopedEntity


def test_base_entity_adds_common_columns() -> None:
    class DemoEntity(BaseEntity):
        __tablename__ = f"test_demo_{uuid.uuid4().hex}"

        name: Mapped[str] = mapped_column(String(50))

    columns = DemoEntity.__table__.columns

    assert "id" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_store_scoped_entity_adds_store_id() -> None:
    class DemoStoreEntity(StoreScopedEntity):
        __tablename__ = f"test_store_demo_{uuid.uuid4().hex}"

        name: Mapped[str] = mapped_column(String(50))

    columns = DemoStoreEntity.__table__.columns

    assert "store_id" in columns
    assert isinstance(columns["store_id"].type, UUID)


def test_active_mixin_adds_is_active() -> None:
    class DemoActiveEntity(BaseEntity, ActiveMixin):
        __tablename__ = f"test_active_demo_{uuid.uuid4().hex}"

        name: Mapped[str] = mapped_column(String(50))

    assert "is_active" in DemoActiveEntity.__table__.columns
