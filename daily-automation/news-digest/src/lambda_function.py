import boto3
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

RECIPIENT = "zhhliu@amazon.com"
SENDER = "zhhliu@amazon.com"
SES_REGION = "us-west-2"
BEDROCK_REGION = "us-west-2"
BEDROCK_MODEL = "us.anthropic.claude-opus-4-7"
DYNAMODB_TABLE = "daily-news-stats"
MAX_ARTICLES = 100


def lambda_handler(event, context):
    config = load_config()
    feeds = [f for f in config["feeds"] if f.get("enabled", True)]

    # 1. Fetch all RSS feeds concurrently
    all_articles, stats = fetch_all_feeds(feeds)

    # 2. Filter last 24h, dedupe, cap at MAX_ARTICLES
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = [a for a in all_articles if a["published"] > cutoff]
    recent.sort(key=lambda x: x["published"], reverse=True)
    deduped = dedupe(recent)
    selected = deduped[:MAX_ARTICLES]

    # Update stats with adopted counts
    for a in selected:
        stats[a["source"]]["adopted"] += 1

    # 3. Generate summary via Bedrock
    if selected:
        summary_html = generate_summary(selected)
    else:
        summary_html = "<p>今日无新文章。</p>"

    # 4. Write stats to DynamoDB
    write_stats(stats)

    # 5. Build and send email
    stats_html = build_stats_table(stats)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto">
      <h2 style="color:#232f3e">📰 每日新闻摘要 — {today_str} | {len(selected)} 条</h2>
      {summary_html}
      <hr style="margin:24px 0">
      <h3 style="color:#232f3e">📊 来源统计</h3>
      {stats_html}
      <p style="color:#666;font-size:12px">由 AWS Lambda + Bedrock Claude 自动生成</p>
    </div>
    """

    ses = boto3.client("ses", region_name=SES_REGION)
    ses.send_email(
        Source=SENDER,
        Destination={"ToAddresses": [RECIPIENT]},
        Message={
            "Subject": {
                "Data": f"📰 每日新闻摘要 — {today_str} | {len(selected)} 条",
                "Charset": "UTF-8",
            },
            "Body": {"Html": {"Data": html, "Charset": "UTF-8"}},
        },
    )
    return {"statusCode": 200, "body": f"Sent {len(selected)} articles"}


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "feeds.json")
    with open(config_path) as f:
        return json.load(f)


def fetch_feed(feed):
    articles = []
    try:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        root = ET.fromstring(data)

        # Handle both RSS and Atom formats
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        for item in items:
            title = (
                getattr(item.find("title"), "text", None)
                or getattr(item.find("atom:title", ns), "text", None)
                or ""
            )
            link = ""
            link_el = item.find("link")
            if link_el is not None:
                link = link_el.text or link_el.get("href", "")
            if not link:
                link_el = item.find("atom:link", ns)
                if link_el is not None:
                    link = link_el.get("href", "")

            desc = (
                getattr(item.find("description"), "text", None)
                or getattr(item.find("atom:summary", ns), "text", None)
                or ""
            )
            # Truncate description
            if len(desc) > 300:
                desc = desc[:300] + "..."

            pub_date = (
                getattr(item.find("pubDate"), "text", None)
                or getattr(item.find("atom:published", ns), "text", None)
                or getattr(item.find("atom:updated", ns), "text", None)
                or ""
            )
            published = parse_date(pub_date)

            if title.strip():
                articles.append(
                    {
                        "title": title.strip(),
                        "link": link.strip(),
                        "description": desc.strip(),
                        "published": published,
                        "source": feed["name"],
                        "category": feed["category"],
                    }
                )
    except Exception as e:
        print(f"Error fetching {feed['name']}: {e}")
    return articles


def parse_date(date_str):
    if not date_str:
        return datetime.now(timezone.utc) - timedelta(hours=12)
    for fmt in [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return datetime.now(timezone.utc) - timedelta(hours=12)


def fetch_all_feeds(feeds):
    all_articles = []
    stats = {}
    for f in feeds:
        stats[f["name"]] = {"category": f["category"], "fetched": 0, "adopted": 0}

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_feed, f): f for f in feeds}
        for future in as_completed(future_map):
            feed = future_map[future]
            try:
                articles = future.result()
                stats[feed["name"]]["fetched"] = len(articles)
                all_articles.extend(articles)
            except Exception as e:
                print(f"Error processing {feed['name']}: {e}")

    return all_articles, stats


def dedupe(articles):
    seen = set()
    result = []
    for a in articles:
        key = a["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            result.append(a)
    return result


def generate_summary(articles):
    # Group by category
    by_cat = {}
    for a in articles:
        by_cat.setdefault(a["category"], []).append(a)

    # Build prompt
    article_text = ""
    for cat, items in by_cat.items():
        article_text += f"\n## {cat}\n"
        for i, a in enumerate(items, 1):
            article_text += f"{i}. [{a['source']}] {a['title']}\n   {a['description'][:200]}\n"

    prompt = f"""请将以下英文新闻整理成中文摘要邮件。要求：
1. 按分类整理，保持原有分类
2. 每条新闻翻译成中文，写 2-3 句话的摘要
3. 标注来源名称
4. 输出 HTML 格式，使用 <h3> 作为分类标题，<ol> 列表展示新闻
5. 每条新闻格式：<li><b>标题中文</b><br>摘要内容 <span style="color:#888">(来源: xxx)</span></li>
6. 分类标题前加 emoji：AWS=☁️ AI=🤖 云计算/科技=💻 金融=💰 HCLS=🏥 零售=🛒 新能源=⚡
7. 不要输出 markdown，只输出纯 HTML

新闻列表：
{article_text}"""

    bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def build_stats_table(stats):
    rows = ""
    total_fetched = 0
    total_adopted = 0
    for name, s in sorted(stats.items(), key=lambda x: -x[1]["adopted"]):
        fetched = s["fetched"]
        adopted = s["adopted"]
        total_fetched += fetched
        total_adopted += adopted
        rate = f"{adopted/fetched*100:.0f}%" if fetched > 0 else "0%"
        warn = " ⚠️" if fetched > 0 and adopted == 0 else ""
        rows += f"""<tr>
          <td style="padding:4px 8px;border-bottom:1px solid #eee">{name}</td>
          <td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:center">{s['category']}</td>
          <td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right">{fetched}</td>
          <td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right">{adopted}</td>
          <td style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right">{rate}{warn}</td>
        </tr>"""

    total_rate = (
        f"{total_adopted/total_fetched*100:.0f}%" if total_fetched > 0 else "0%"
    )
    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <tr style="background:#232f3e;color:white">
        <th style="padding:6px 8px;text-align:left">来源</th>
        <th style="padding:6px 8px;text-align:center">分类</th>
        <th style="padding:6px 8px;text-align:right">抓取</th>
        <th style="padding:6px 8px;text-align:right">采用</th>
        <th style="padding:6px 8px;text-align:right">采用率</th>
      </tr>
      {rows}
      <tr style="background:#f5f5f5;font-weight:bold">
        <td style="padding:6px 8px" colspan="2">合计</td>
        <td style="padding:6px 8px;text-align:right">{total_fetched}</td>
        <td style="padding:6px 8px;text-align:right">{total_adopted}</td>
        <td style="padding:6px 8px;text-align:right">{total_rate}</td>
      </tr>
    </table>"""


def write_stats(stats):
    try:
        ddb = boto3.resource("dynamodb", region_name=SES_REGION)
        table = ddb.Table(DYNAMODB_TABLE)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        table.put_item(
            Item={
                "date": today_str,
                "stats": json.loads(json.dumps(stats)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        print(f"Error writing stats: {e}")
