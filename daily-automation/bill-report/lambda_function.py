import boto3
from datetime import datetime, timedelta

RECIPIENT = "zhhliu@amazon.com"
SENDER = "zhhliu@amazon.com"
SES_REGION = "us-west-2"

def lambda_handler(event, context):
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = datetime.utcnow().strftime('%Y-%m-%d')
    first_of_month = datetime.utcnow().replace(day=1).strftime('%Y-%m-%d')

    ce = boto3.client('ce', region_name='us-east-1')

    # 昨日明细
    daily = ce.get_cost_and_usage(
        TimePeriod={'Start': yesterday, 'End': today},
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )

    # 本月累计
    mtd = ce.get_cost_and_usage(
        TimePeriod={'Start': first_of_month, 'End': today},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )

    mtd_total = float(mtd['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

    # 构建服务明细
    services = []
    total = 0
    for g in daily['ResultsByTime'][0].get('Groups', []):
        cost = float(g['Metrics']['UnblendedCost']['Amount'])
        if cost > 0.005:
            services.append((g['Keys'][0], cost))
            total += cost
    services.sort(key=lambda x: -x[1])

    # 生成 HTML
    rows = ""
    for svc, cost in services:
        rows += f"<tr><td style='padding:6px 12px;border-bottom:1px solid #eee'>{svc}</td>"
        rows += f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right'>${cost:.2f}</td></tr>"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:#232f3e">☁️ AWS 每日账单 — {yesterday}</h2>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr style="background:#232f3e;color:white">
          <th style="padding:8px 12px;text-align:left">服务</th>
          <th style="padding:8px 12px;text-align:right">费用 (USD)</th>
        </tr>
        {rows}
        <tr style="background:#f5f5f5;font-weight:bold">
          <td style="padding:8px 12px">昨日合计</td>
          <td style="padding:8px 12px;text-align:right">${total:.2f}</td>
        </tr>
        <tr style="background:#fff3cd;font-weight:bold">
          <td style="padding:8px 12px">📊 本月累计</td>
          <td style="padding:8px 12px;text-align:right">${mtd_total:.2f}</td>
        </tr>
      </table>
      <p style="color:#666;font-size:12px">Account: 570326752681 | 数据来源: AWS Cost Explorer (有 ~12h 延迟)</p>
    </div>
    """

    ses = boto3.client('ses', region_name=SES_REGION)
    ses.send_email(
        Source=SENDER,
        Destination={'ToAddresses': [RECIPIENT]},
        Message={
            'Subject': {'Data': f'AWS 每日账单 — {yesterday} | 合计 ${total:.2f}', 'Charset': 'UTF-8'},
            'Body': {'Html': {'Data': html, 'Charset': 'UTF-8'}}
        }
    )
    return {'statusCode': 200, 'body': f'Sent bill report for {yesterday}'}
