"""Amazon评论抓取模块。

作为卖家精灵CSV的备选方案，直接从Amazon抓取评论数据。
优先推荐使用卖家精灵导出CSV（数据更全、更稳定）。
"""
import json
import random
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from src.scraper.listing_scraper import _get_headers, DEFAULT_MARKETPLACE


async def fetch_reviews_page(
    asin: str,
    page: int = 1,
    client: httpx.AsyncClient = None,
    marketplace: str = DEFAULT_MARKETPLACE,
) -> str | None:
    """抓取评论列表页。"""
    url = f"{marketplace}/product-reviews/{asin}/ref=cm_cr_arp_d_viewopt_srt?sortBy=recent&page={page}"
    headers = _get_headers()
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        if resp.status_code == 503:
            print(f"  [!] CAPTCHA detected for {asin} page {page}")
            return None
        resp.raise_for_status()
        return resp.text
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        print(f"  [!] Error fetching reviews for {asin} page {page}: {e}")
        return None


def parse_reviews(html: str, asin: str) -> list[dict]:
    """从评论页HTML中提取评论列表。"""
    soup = BeautifulSoup(html, "lxml")
    reviews = []

    for review_el in soup.select('[data-hook="review"]'):
        review = {"asin": asin}

        # 标题
        title_el = review_el.select_one('[data-hook="review-title"] span:last-child')
        if not title_el:
            title_el = review_el.select_one('[data-hook="review-title"]')
        review["title"] = title_el.get_text(strip=True) if title_el else ""

        # 评分
        rating_el = review_el.select_one('[data-hook="review-star-rating"] .a-icon-alt, [data-hook="cmps-review-star-rating"] .a-icon-alt')
        if rating_el:
            text = rating_el.get_text(strip=True)
            try:
                review["rating"] = float(text.split(" ")[0])
            except (ValueError, IndexError):
                review["rating"] = None
        else:
            review["rating"] = None

        # 日期
        date_el = review_el.select_one('[data-hook="review-date"]')
        review["date"] = date_el.get_text(strip=True) if date_el else ""

        # 评论内容
        body_el = review_el.select_one('[data-hook="review-body"] span')
        review["content"] = body_el.get_text(strip=True) if body_el else ""

        # 是否已验证购买
        verified_el = review_el.select_one('[data-hook="avp-badge"]')
        review["verified"] = "Yes" if verified_el else ""

        # 变体信息
        variant_el = review_el.select_one('[data-hook="format-strip"]')
        review["variant"] = variant_el.get_text(strip=True) if variant_el else ""

        if review["content"]:  # 只保留有内容的评论
            reviews.append(review)

    return reviews


async def scrape_all_reviews(
    asin: str,
    max_pages: int = 10,
    output_dir: Path = None,
    marketplace: str = DEFAULT_MARKETPLACE,
) -> list[dict]:
    """分页抓取一个ASIN的所有评论。"""
    all_reviews = []
    async with httpx.AsyncClient(http2=True) as client:
        for page in range(1, max_pages + 1):
            print(f"  ASIN {asin}: 抓取评论第 {page}/{max_pages} 页...")
            html = await fetch_reviews_page(asin, page, client, marketplace)
            if not html:
                break

            reviews = parse_reviews(html, asin)
            if not reviews:
                print(f"  无更多评论，停止")
                break

            all_reviews.extend(reviews)
            print(f"  本页 {len(reviews)} 条，累计 {len(all_reviews)} 条")

            # 随机延迟
            time.sleep(random.uniform(2.0, 4.0))

    # 保存结果
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{asin}_reviews.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_reviews, f, ensure_ascii=False, indent=2)
        print(f"  评论已保存: {output_file}")

    return all_reviews
