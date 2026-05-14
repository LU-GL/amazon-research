"""Amazon Listing抓取模块。

用httpx异步抓取Amazon产品页，提取标题/五点/价格/评分/BSR等结构化数据。
优先使用卖家精灵CSV数据，此模块作为补充数据源。
"""
import asyncio
import json
import random
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

DEFAULT_MARKETPLACE = "https://www.amazon.com"


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    }


async def fetch_listing_page(
    asin: str,
    client: httpx.AsyncClient,
    marketplace: str = DEFAULT_MARKETPLACE,
) -> str | None:
    """抓取单个ASIN的产品页面HTML。"""
    url = f"{marketplace}/dp/{asin}"
    try:
        resp = await client.get(url, headers=_get_headers(), follow_redirects=True, timeout=15.0)
        if resp.status_code == 503:
            print(f"  [!] CAPTCHA/503 detected for {asin}, skipping")
            return None
        if resp.status_code == 404:
            print(f"  [!] ASIN {asin} not found (404)")
            return None
        resp.raise_for_status()
        return resp.text
    except httpx.TimeoutException:
        print(f"  [!] Timeout for {asin}")
        return None
    except httpx.HTTPError as e:
        print(f"  [!] HTTP error for {asin}: {e}")
        return None


def parse_listing(html: str, asin: str) -> dict:
    """从HTML中解析listing结构化数据。"""
    soup = BeautifulSoup(html, "lxml")
    data = {"asin": asin}

    # 标题
    title_el = soup.select_one("#productTitle")
    data["title"] = title_el.get_text(strip=True) if title_el else None

    # 五点描述
    bullets = soup.select("#feature-bullets li span.a-list-item")
    data["bullet_points"] = [b.get_text(strip=True) for b in bullets if b.get_text(strip=True)]

    # 价格
    price_el = soup.select_one(".a-price .a-offscreen")
    data["price"] = price_el.get_text(strip=True) if price_el else None

    # 评分
    rating_el = soup.select_one("#acrPopover .a-icon-alt")
    if rating_el:
        text = rating_el.get_text(strip=True)
        try:
            data["rating"] = float(text.split(" ")[0])
        except (ValueError, IndexError):
            data["rating"] = None
    else:
        data["rating"] = None

    # 评论数
    review_count_el = soup.select_one("#acrCustomerReviewText")
    if review_count_el:
        text = review_count_el.get_text(strip=True).replace(",", "").replace(".", "")
        try:
            data["review_count"] = int("".join(filter(str.isdigit, text)))
        except ValueError:
            data["review_count"] = None
    else:
        data["review_count"] = None

    # 品牌
    brand_el = soup.select_one("#bylineInfo")
    data["brand"] = brand_el.get_text(strip=True) if brand_el else None

    # BSR - 从产品详情表格中提取
    data["bsr"] = _extract_bsr(soup)

    # 图片
    images = soup.select("#altImages img")
    data["images"] = []
    for img in images:
        src = img.get("src", "")
        if src and "play-icon" not in src:
            # 获取高清图URL（去掉._SL75_等缩放标记）
            hi_res = src.replace("._SS40_", "._SL1000_").replace("._SX38_SY50_", "._SL1000_")
            data["images"].append(hi_res)

    return data


def _extract_bsr(soup: BeautifulSoup) -> list[dict]:
    """提取Best Sellers Rank信息。"""
    bsr_list = []
    # 尝试多种选择器
    for selector in ["#detailBulletsWrapper_feature_div", "#productDetails_detailBullets_sections1", "#detailBullets_feature_div"]:
        section = soup.select_one(selector)
        if section:
            text = section.get_text()
            # 查找 "Best Sellers Rank" 模式
            import re
            matches = re.findall(r"#([\d,]+)\s+in\s+([^(]+?)(?:\(|$)", text)
            for rank, category in matches:
                bsr_list.append({
                    "rank": int(rank.replace(",", "")),
                    "category": category.strip(),
                })
            if bsr_list:
                break
    return bsr_list


async def scrape_listings(
    asins: list[str],
    output_dir: Path,
    marketplace: str = DEFAULT_MARKETPLACE,
    delay_range: tuple[float, float] = (2.0, 5.0),
) -> dict[str, dict]:
    """批量抓取ASIN listing，保存为JSON文件。返回 {asin: data} 字典。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    async with httpx.AsyncClient(http2=True) as client:
        for i, asin in enumerate(asins):
            output_file = output_dir / f"{asin}.json"

            # 增量：已有数据则跳过
            if output_file.exists():
                print(f"  [{i+1}/{len(asins)}] {asin} - 已存在，跳过")
                with open(output_file, "r", encoding="utf-8") as f:
                    results[asin] = json.load(f)
                continue

            print(f"  [{i+1}/{len(asins)}] 抓取 {asin}...")
            html = await fetch_listing_page(asin, client, marketplace)
            if html:
                data = parse_listing(html, asin)
                results[asin] = data
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                results[asin] = {"asin": asin, "error": "fetch_failed"}

            if i < len(asins) - 1:
                delay = random.uniform(*delay_range)
                time.sleep(delay)

    return results
