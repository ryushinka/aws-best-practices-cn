import boto3
import json
import urllib.parse
from datetime import datetime, timezone

DYNAMODB_TABLE = "daily-news-bookmarks"
REGION = "us-west-2"
DEFAULT_USER = "zhhliu"


def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    action = params.get("action", "save")

    if action == "list":
        return list_bookmarks()
    elif action == "delete":
        return delete_bookmark(params)
    else:
        return save_bookmark(params)


def save_bookmark(params):
    title = urllib.parse.unquote(params.get("title", ""))
    url = urllib.parse.unquote(params.get("url", ""))
    source = urllib.parse.unquote(params.get("source", ""))
    date = params.get("date", "")

    if not title or not url:
        return response_html("❌ 缺少参数", "标题和链接不能为空。")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(DYNAMODB_TABLE)

    bookmark_id = f"{date}#{title[:50]}"
    table.put_item(
        Item={
            "userId": DEFAULT_USER,
            "bookmarkId": bookmark_id,
            "title": title,
            "url": url,
            "source": source,
            "date": date,
            "savedAt": datetime.now(timezone.utc).isoformat(),
        }
    )

    return response_html(
        "⭐ 已收藏",
        f'<p><b>{title}</b></p>'
        f'<p>来源: {source} | 日期: {date}</p>'
        f'<p><a href="{url}">查看原文 →</a></p>'
        f'<hr><p><a href="?action=list">📚 查看所有收藏</a></p>',
    )


def list_bookmarks():
    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(DYNAMODB_TABLE)

    result = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("userId").eq(DEFAULT_USER),
        ScanIndexForward=False,
    )

    items = result.get("Items", [])
    if not items:
        return response_html("📚 收藏列表", "<p>暂无收藏。</p>")

    rows = ""
    for item in items:
        bid = urllib.parse.quote(item["bookmarkId"])
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">{item.get("date", "")}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">'
            f'<a href="{item["url"]}" style="color:#0073bb">{item["title"]}</a></td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">{item.get("source", "")}</td>'
            f'<td style="padding:6px 8px;border-bottom:1px solid #eee">'
            f'<a href="?action=delete&bookmarkId={bid}" style="color:red">删除</a></td>'
            f"</tr>"
        )

    html = f"""
    <table style="width:100%;border-collapse:collapse">
      <tr style="background:#232f3e;color:white">
        <th style="padding:8px;text-align:left">日期</th>
        <th style="padding:8px;text-align:left">标题</th>
        <th style="padding:8px;text-align:left">来源</th>
        <th style="padding:8px">操作</th>
      </tr>
      {rows}
    </table>
    <p style="color:#888;margin-top:16px">共 {len(items)} 条收藏</p>
    """
    return response_html(f"📚 收藏列表（{len(items)} 条）", html)


def delete_bookmark(params):
    bookmark_id = urllib.parse.unquote(params.get("bookmarkId", ""))
    if not bookmark_id:
        return response_html("❌ 错误", "缺少 bookmarkId。")

    ddb = boto3.resource("dynamodb", region_name=REGION)
    table = ddb.Table(DYNAMODB_TABLE)
    table.delete_item(Key={"userId": DEFAULT_USER, "bookmarkId": bookmark_id})

    return response_html(
        "🗑️ 已删除",
        f'<p>收藏已删除。</p><p><a href="?action=list">📚 返回收藏列表</a></p>',
    )


def response_html(title, body):
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:Arial,sans-serif;max-width:700px;margin:40px auto;padding:0 20px}}
a{{color:#0073bb}}</style></head>
<body><h2>{title}</h2>{body}</body></html>"""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": html,
    }
