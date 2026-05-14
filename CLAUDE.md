# 亚马逊市调/竞品分析系统

## 数据源
- 卖家精灵导出的CSV放在 `data/seller_jing/`
- 亚马逊后台导出数据放在 `data/amazon_exports/`
- 抓取的listing数据自动存到 `data/raw_listings/`
- 抓取的评论数据自动存到 `data/raw_reviews/`

## 分析流程
1. 采集目标品类Top50 ASIN
2. 抓取各ASIN的listing和评论
3. 用Claude API批量分析评论痛点
4. 输出竞品矩阵Excel + 市调PPT

## 使用方式

### 仅用卖家精灵CSV做评论分析
```bash
python scripts/01_analyze_sentiment.py --input data/seller_jing/export.csv --category "宠物用品"
```

### 采集Listing数据
```bash
python scripts/02_scrape_listings.py --asin-file data/asins.txt
python scripts/02_scrape_listings.py --asin-file data/asins.txt --with-reviews  # 同时抓评论
```

### 生成报告（需先有分析结果）
```bash
python scripts/03_generate_report.py --sentiment output/sentiment_results.json --category "宠物用品"
```

### 一键运行完整流程
```bash
python scripts/run_all.py --category "宠物用品" --seller-jing-csv data/seller_jing/export.csv
```

## 项目结构
```
src/
  config.py              # 集中配置（API密钥、路径）
  sentiment/
    csv_parser.py        # 解析卖家精灵CSV（GBK/UTF-8兼容）
    analyzer.py          # Claude API批量评论分析（核心）
    aggregator.py        # 跨ASIN对比汇总
  scraper/
    listing_scraper.py   # Amazon Listing抓取（httpx异步）
    review_scraper.py    # Amazon评论抓取（CSV备选）
  analysis/
    competitive_matrix.py # 竞品矩阵构建
  report/
    excel_writer.py      # Excel报告（openpyxl格式化）
    pptx_writer.py       # PPT报告（python-pptx）
scripts/
  01_analyze_sentiment.py # 入口：评论分析
  02_scrape_listings.py   # 入口：数据采集
  03_generate_report.py   # 入口：报告生成
  run_all.py              # 一键全流程
output/                   # 生成的报告文件
```

## 环境要求
- Python 3.10+
- `pip install -r requirements.txt`
- `.env` 文件配置API密钥
