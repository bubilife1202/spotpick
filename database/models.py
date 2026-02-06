from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .connection import Base


class CommercialArea(Base):
    __tablename__ = "commercial_areas"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(50))

    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    region_code: Mapped[str] = mapped_column(String(20), index=True)
    region_name: Mapped[str] = mapped_column(String(100))

    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    floating_population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_rent_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    stores: Mapped[list["Store"]] = relationship(back_populates="commercial_area")

    __table_args__ = (Index("idx_area_location", "lat", "lng"),)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))

    category_large: Mapped[str] = mapped_column(String(100), index=True)
    category_medium: Mapped[str] = mapped_column(String(100), index=True)
    category_small: Mapped[str] = mapped_column(String(100))

    address: Mapped[str] = mapped_column(String(500))
    road_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    commercial_area_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("commercial_areas.id"), nullable=True
    )
    commercial_area: Mapped[Optional["CommercialArea"]] = relationship(back_populates="stores")

    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(100))

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    estimated_open_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_closed: Mapped[bool] = mapped_column(default=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    reviews: Mapped[list["Review"]] = relationship(back_populates="store")
    success_metrics: Mapped[list["SuccessMetric"]] = relationship(back_populates="store")

    __table_args__ = (
        Index("idx_store_location", "lat", "lng"),
        Index("idx_store_source", "source", "source_id"),
        Index("idx_store_category", "category_large", "category_medium"),
    )


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(50), ForeignKey("stores.id"), index=True)
    store: Mapped["Store"] = relationship(back_populates="reviews")

    source: Mapped[str] = mapped_column(String(50))
    source_review_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_review_store_date", "store_id", "reviewed_at"),)


class SuccessMetric(Base):
    __tablename__ = "success_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[str] = mapped_column(String(50), ForeignKey("stores.id"), index=True)
    store: Mapped["Store"] = relationship(back_populates="success_metrics")

    measured_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    survival_months: Mapped[int] = mapped_column(Integer)

    review_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_review_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    estimated_monthly_revenue: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    success_score: Mapped[float] = mapped_column(Float)

    factors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_metric_store_date", "store_id", "measured_at"),
        Index("idx_metric_score", "success_score"),
    )


class CollectionLog(Base):
    __tablename__ = "collection_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    collection_type: Mapped[str] = mapped_column(String(50))

    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
