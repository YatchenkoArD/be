# app/models/models.py
import enum
from datetime import datetime, time
from typing import Optional, List, Dict

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey,
    Text, DateTime, Enum, CheckConstraint, Index, UniqueConstraint, JSON, text
)
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func

Base = declarative_base()

# --- Enums ---
class UserRole(str, enum.Enum):
    CLIENT = "client"
    MODEL = "model"
    MASTER = "master"
    BUSINESS = "business"
    ADMIN = "admin"

class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class SubscriptionTier(str, enum.Enum):
    START = "start"
    PRO = "pro"
    PREMIUM = "premium"

class SalonRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    # MASTER сюда сознательно не входит: у мастера уже есть своя таблица
    # Master с operatonal-доступом, заскоупленным через Master.user_id —
    # ему не нужен настраиваемый словарь прав, который тут нужен owner/admin.

# Ключи прав салона. Значение — можно ли делать соответствующее действие.
# У создателя салона (SalonMember.is_creator=True) все права всегда True
# независимо от словаря, плюс только он может удалить сам салон.
SALON_PERMISSION_KEYS = (
    "manage_salon",      # настройки, фото, описание, график салона
    "manage_owners",     # приглашать/снимать совладельцев, менять их права
    "manage_admins",     # приглашать/снимать админов
    "manage_masters",    # CRUD мастеров, услуг, графика мастера
    "manage_schedule",   # быстрые записи, отметка выполнено/неявка
    "manage_promotions",
    "manage_reviews",    # ответы на отзывы
    "view_finances",
    "manage_tariff",
    "view_audit_log",
)

OWNER_DEFAULT_PERMISSIONS: Dict[str, bool] = {k: True for k in SALON_PERMISSION_KEYS}
ADMIN_DEFAULT_PERMISSIONS: Dict[str, bool] = {
    **OWNER_DEFAULT_PERMISSIONS,
    "view_finances": False,
    "manage_tariff": False,
    "manage_owners": False,
    "view_audit_log": False,
}

# --- Core Tables ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    subscription_tier: Mapped[Optional[SubscriptionTier]] = mapped_column(Enum(SubscriptionTier), nullable=True)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    master_profile: Mapped[Optional["Master"]] = relationship(back_populates="user", uselist=False)
    created_salons: Mapped[List["Salon"]] = relationship(back_populates="creator")
    salon_memberships: Mapped[List["SalonMember"]] = relationship(back_populates="user", foreign_keys="SalonMember.user_id")
    bookings: Mapped[List["Booking"]] = relationship(back_populates="client", foreign_keys="Booking.client_id")
    reviews: Mapped[List["Review"]] = relationship(back_populates="client")
    favorites: Mapped[List["Favorite"]] = relationship(back_populates="user")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Salon(Base):
    __tablename__ = "salons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Пользователь, создавший карточку салона. Не источник правды для прав —
    # тот источник теперь SalonMember (role=owner, is_creator=True для этого же
    # user_id). creator_id остаётся как исторический/справочный указатель и не
    # уникален: один человек может быть создателем нескольких салонов.
    creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    creator: Mapped["User"] = relationship(back_populates="created_salons")
    members: Mapped[List["SalonMember"]] = relationship(back_populates="salon", cascade="all, delete-orphan")
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    photos: Mapped[List["SalonPhoto"]] = relationship(back_populates="salon")

    rating: Mapped[float] = mapped_column(Float, default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)

    working_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", server_default="Europe/Moscow", nullable=False)

    masters: Mapped[List["Master"]] = relationship(back_populates="salon")
    promotions: Mapped[List["Promotion"]] = relationship(back_populates="salon")
    reviews: Mapped[List["Review"]] = relationship(back_populates="salon")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SalonPhoto(Base):
    __tablename__ = "salon_photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))
    salon: Mapped["Salon"] = relationship(back_populates="photos")

class SalonMember(Base):
    """Членство пользователя в бизнес-панели салона (owner/admin) с гибкими правами."""
    __tablename__ = "salon_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    role: Mapped[SalonRole] = mapped_column(Enum(SalonRole), nullable=False)
    is_creator: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    permissions: Mapped[Dict[str, bool]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    invited_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    salon: Mapped["Salon"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="salon_memberships", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("salon_id", "user_id", name="uq_salon_member"),
        Index("ix_salon_members_user", "user_id"),
        Index(
            "uq_salon_creator", "salon_id", unique=True,
            postgresql_where=text("is_creator = true"),
        ),
    )

class Master(Base):
    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id"))

    specialization: Mapped[str] = mapped_column(String(100), nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rating: Mapped[float] = mapped_column(Float, default=0.0)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    break_minutes: Mapped[int] = mapped_column(Integer, default=15, server_default="15", nullable=False)
    
    user: Mapped["User"] = relationship(back_populates="master_profile")
    salon: Mapped["Salon"] = relationship(back_populates="masters")
    services: Mapped[List["Service"]] = relationship(back_populates="master")
    schedule: Mapped[List["Schedule"]] = relationship(back_populates="master")
    reviews: Mapped[List["Review"]] = relationship(back_populates="master")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    master: Mapped["Master"] = relationship(back_populates="services")

class Schedule(Base):
    __tablename__ = "schedule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"))
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column()
    end_time: Mapped[time] = mapped_column()

    master: Mapped["Master"] = relationship(back_populates="schedule")

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.PENDING)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    final_price: Mapped[int] = mapped_column(Integer, nullable=True)

    client: Mapped["User"] = relationship(back_populates="bookings", foreign_keys=[client_id])
    master: Mapped["Master"] = relationship()
    service: Mapped["Service"] = relationship()

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_bookings_master_start', 'master_id', 'start_time'),
    )

class Promotion(Base):
    __tablename__ = "promotions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id"))
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tag: Mapped[str] = mapped_column(String(30), nullable=False)

    salon: Mapped["Salon"] = relationship(back_populates="promotions")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"))
    salon_id: Mapped[int] = mapped_column(ForeignKey("salons.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["User"] = relationship(back_populates="reviews")
    master: Mapped["Master"] = relationship(back_populates="reviews")
    salon: Mapped["Salon"] = relationship(back_populates="reviews")

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )

# ========== НОВАЯ МОДЕЛЬ: Избранное ==========
class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    salon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("salons.id"), nullable=True)
    master_id: Mapped[Optional[int]] = mapped_column(ForeignKey("masters.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="favorites")
    salon: Mapped[Optional["Salon"]] = relationship()
    master: Mapped[Optional["Master"]] = relationship()

# ========== Аудит действий администратора ==========
class AdminAudit(Base):
    __tablename__ = "admin_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))   # кто совершил действие
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # change_role, toggle_active, delete_user, …
    target_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # user / salon / review
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # человекочитаемое описание
    # NULL = платформенное действие (суперадмин). Заполнено — действие внутри
    # конкретного салона (приглашение/снятие сотрудника, удаление салона и т.п.).
    # ondelete=SET NULL: при удалении салона лог остаётся, просто теряет привязку.
    salon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("salons.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_admin_audit_created", "created_at"),
        Index("ix_admin_audit_salon", "salon_id"),
    )