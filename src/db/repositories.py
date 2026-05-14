from datetime import datetime

import pandas as pd
from sqlalchemy import func

from src.db.models import Product, Review, AnalysisRun, SentimentAnalysis, ComparisonResult


class ProductRepo:
    def __init__(self, session):
        self.session = session

    def get_or_create(self, asin):
        product = self.session.query(Product).filter_by(asin=asin).first()
        if not product:
            product = Product(asin=asin)
            self.session.add(product)
            self.session.flush()
        return product

    def upsert_from_listing(self, asin, listing_data):
        product = self.get_or_create(asin)
        product.title = listing_data.get("title") or product.title
        product.brand = listing_data.get("brand") or product.brand

        price_str = listing_data.get("price")
        if price_str:
            try:
                product.price = float(str(price_str).replace("$", "").replace(",", "").strip())
            except (ValueError, TypeError):
                pass

        product.rating = listing_data.get("rating") or product.rating
        product.review_count = listing_data.get("review_count") or product.review_count
        product.bullet_points = listing_data.get("bullet_points") or product.bullet_points
        product.bsr = listing_data.get("bsr") or product.bsr
        product.images = listing_data.get("images") or product.images
        product.updated_at = datetime.utcnow()
        self.session.flush()
        return product

    def get_by_asin(self, asin):
        return self.session.query(Product).filter_by(asin=asin).first()

    def list_all(self):
        return self.session.query(Product).all()

    def list_asins(self):
        return [p.asin for p in self.session.query(Product.asin).all()]

    def count(self):
        return self.session.query(func.count(Product.id)).scalar()

    def import_listings_from_dir(self, listings_dir):
        import json
        from pathlib import Path
        count = 0
        listings_dir = Path(listings_dir)
        if not listings_dir.exists():
            return 0
        for f in listings_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                asin = data.get("asin", f.stem)
                self.upsert_from_listing(asin, data)
                count += 1
            except (json.JSONDecodeError, IOError):
                continue
        self.session.commit()
        return count


class ReviewRepo:
    def __init__(self, session):
        self.session = session

    def import_from_dataframe(self, product_id, df, source="seller_jing"):
        self.session.query(Review).filter_by(product_id=product_id, source=source).delete()
        count = 0
        for _, row in df.iterrows():
            content = str(row.get("content", "")).strip()
            if not content:
                continue
            review = Review(
                product_id=product_id,
                title=str(row.get("title", "")).strip() or None,
                content=content,
                rating=float(row["rating"]) if pd.notna(row.get("rating")) else None,
                review_date=str(row.get("date", "")).strip() or None,
                verified=str(row.get("verified", "")).strip() or None,
                variant=str(row.get("variant", "")).strip() or None,
                source=source,
            )
            self.session.add(review)
            count += 1
        self.session.flush()
        return count

    def count_by_product(self, product_id):
        return self.session.query(func.count(Review.id)).filter_by(product_id=product_id).scalar()

    def count_all(self):
        return self.session.query(func.count(Review.id)).scalar()

    def list_by_product(self, product_id, limit=100):
        return self.session.query(Review).filter_by(product_id=product_id).limit(limit).all()

    def to_dataframe(self, product_id):
        reviews = self.session.query(Review).filter_by(product_id=product_id).all()
        if not reviews:
            return pd.DataFrame()
        data = []
        for r in reviews:
            data.append({
                "asin": r.product.asin if r.product else "",
                "title": r.title or "",
                "content": r.content,
                "rating": r.rating,
                "date": r.review_date or "",
                "verified": r.verified or "",
                "brand": r.product.brand if r.product and r.product.brand else "",
                "variant": r.variant or "",
            })
        return pd.DataFrame(data)

    def to_dataframe_by_asin(self, asin):
        reviews = self.session.query(Review).join(Product).filter(Product.asin == asin).all()
        if not reviews:
            return pd.DataFrame()
        data = []
        for r in reviews:
            data.append({
                "asin": asin,
                "title": r.title or "",
                "content": r.content,
                "rating": r.rating,
                "date": r.review_date or "",
                "verified": r.verified or "",
                "brand": r.product.brand if r.product and r.product.brand else "",
                "variant": r.variant or "",
            })
        return pd.DataFrame(data)


class AnalysisRunRepo:
    def __init__(self, session):
        self.session = session

    def create(self, run_type, category=""):
        run = AnalysisRun(run_type=run_type, category=category, status="pending")
        self.session.add(run)
        self.session.flush()
        return run

    def start(self, run_id):
        run = self.get(run_id)
        if run:
            run.status = "running"
            run.started_at = datetime.utcnow()
            self.session.flush()

    def complete(self, run_id, asins_analyzed=0, total_reviews=0):
        run = self.get(run_id)
        if run:
            run.status = "completed"
            run.asins_analyzed = asins_analyzed
            run.total_reviews = total_reviews
            run.completed_at = datetime.utcnow()
            self.session.flush()

    def fail(self, run_id, error):
        run = self.get(run_id)
        if run:
            run.status = "failed"
            run.error_message = error
            run.completed_at = datetime.utcnow()
            self.session.flush()

    def list_recent(self, limit=20):
        return self.session.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit).all()

    def list_all(self):
        return self.session.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).all()

    def get(self, run_id):
        return self.session.query(AnalysisRun).get(run_id)

    def count(self):
        return self.session.query(func.count(AnalysisRun.id)).scalar()


class SentimentRepo:
    def __init__(self, session):
        self.session = session

    def save_analysis(self, run_id, product_id, analysis):
        sa = SentimentAnalysis(
            run_id=run_id,
            product_id=product_id,
            total_reviews=analysis.get("total_reviews", 0),
            analyzed_batches=analysis.get("analyzed_batches", 0),
            pain_points=analysis.get("pain_points", []),
            praise_points=analysis.get("praise_points", []),
            feature_requests=analysis.get("feature_requests", []),
            quality_issues=analysis.get("quality_issues", []),
            sentiment_summary=analysis.get("sentiment_summary", {}),
        )
        self.session.add(sa)
        self.session.flush()
        return sa

    def save_comparison(self, run_id, comparison):
        cr = ComparisonResult(
            run_id=run_id,
            common_pain_points=comparison.get("common_pain_points", []),
            unique_pain_points=comparison.get("unique_pain_points", []),
            common_praise_points=comparison.get("common_praise_points", []),
            feature_opportunities=comparison.get("feature_opportunities", []),
            insights=comparison.get("insights", []),
            total_asins=comparison.get("total_asins", 0),
        )
        self.session.add(cr)
        self.session.flush()
        return cr

    def get_by_run(self, run_id):
        return self.session.query(SentimentAnalysis).filter_by(run_id=run_id).all()

    def get_comparison(self, run_id):
        cr = self.session.query(ComparisonResult).filter_by(run_id=run_id).first()
        if not cr:
            return None
        return {
            "common_pain_points": cr.common_pain_points or [],
            "unique_pain_points": cr.unique_pain_points or [],
            "common_praise_points": cr.common_praise_points or [],
            "feature_opportunities": cr.feature_opportunities or [],
            "insights": cr.insights or [],
            "total_asins": cr.total_asins or 0,
        }

    def to_asin_analyses_dict(self, run_id):
        analyses = self.get_by_run(run_id)
        result = {}
        for sa in analyses:
            asin = sa.product.asin if sa.product else f"product_{sa.product_id}"
            result[asin] = {
                "asin": asin,
                "total_reviews": sa.total_reviews,
                "analyzed_batches": sa.analyzed_batches,
                "pain_points": sa.pain_points or [],
                "praise_points": sa.praise_points or [],
                "feature_requests": sa.feature_requests or [],
                "quality_issues": sa.quality_issues or [],
                "sentiment_summary": sa.sentiment_summary or {},
            }
        return result
