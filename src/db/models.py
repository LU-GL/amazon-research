from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), unique=True, nullable=False)
    title = Column(Text)
    brand = Column(String(200))
    price = Column(Float)
    rating = Column(Float)
    review_count = Column(Integer)
    bullet_points = Column(JSON)
    bsr = Column(JSON)
    images = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reviews = relationship("Review", back_populates="product")
    sentiment_analyses = relationship("SentimentAnalysis", back_populates="product")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    title = Column(Text)
    content = Column(Text, nullable=False)
    rating = Column(Float)
    review_date = Column(String(50))
    verified = Column(String(10))
    variant = Column(Text)
    source = Column(String(20), default="seller_jing")
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="reviews")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(30), nullable=False)
    category = Column(String(100), default="")
    status = Column(String(20), default="pending")
    asins_analyzed = Column(Integer, default=0)
    total_reviews = Column(Integer, default=0)
    total_batches = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    sentiment_analyses = relationship("SentimentAnalysis", back_populates="run")
    comparison = relationship("ComparisonResult", back_populates="run", uselist=False)


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    total_reviews = Column(Integer, default=0)
    analyzed_batches = Column(Integer, default=0)
    pain_points = Column(JSON)
    praise_points = Column(JSON)
    feature_requests = Column(JSON)
    quality_issues = Column(JSON)
    sentiment_summary = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AnalysisRun", back_populates="sentiment_analyses")
    product = relationship("Product", back_populates="sentiment_analyses")


class ComparisonResult(Base):
    __tablename__ = "comparison_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False, unique=True)
    common_pain_points = Column(JSON)
    unique_pain_points = Column(JSON)
    common_praise_points = Column(JSON)
    feature_opportunities = Column(JSON)
    insights = Column(JSON)
    total_asins = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("AnalysisRun", back_populates="comparison")
