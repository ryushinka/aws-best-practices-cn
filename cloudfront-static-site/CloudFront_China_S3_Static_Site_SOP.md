# CloudFront 中国区 + S3 静态网站 + 自定义域名 + SSL 证书 完整 SOP

> 适用：AWS 中国区（cn-north-1 / cn-northwest-1），将 S3 静态站点通过 CloudFront 暴露到自定义域名并启用 HTTPS。
> 编写背景：基于真实项目排障过程沉淀，含中国区特殊性 + 常见错误对照表。

---

## 1. 架构 & 适用场景

### 1.1 目标架构

```
用户浏览器
   │ HTTPS (自定义域名 + 第三方 SSL 证书)
   ↓
CloudFront 分配（中国区 .cloudfront.cn）
   │ 终结 TLS、缓存、HTTP→HTTPS 重定向
   │ 通过 OAI/OAC 签名访问 S3 REST endpoint
   ↓
S3 桶（私有，仅 CloudFront 可读）
```

### 1.2 何时使用本方案

- 静态网站（HTML/JS/CSS）或 SPA（React/Vue），可能调用 API Gateway
- 需要绑定自定义域名（已 ICP 备案）
- 需要 HTTPS（第三方证书或购买的证书）
- 在 AWS 中国区部署

### 1.3 不适用

- 需要服务端动态渲染（用 ECS/Lambda 或 EC2）
- 没有 ICP 备案（中国区强制要求）
- 想用 ACM 自动续期（中国区 CloudFront 暂不支持 ACM）

---

## 2. 中国区 vs 全球区 差异速查

| 维度 | 全球区 | 中国区 |
|---|---|---|
| 证书来源 | ACM（us-east-1，免费、自动续期） | 必须用 IAM Server Certificate |
| 证书 path 要求 | 任意（ACM 透明） | 必须 `/cloudfront/` 开头 |
| ARN 前缀 | `arn:aws:...` | `arn:aws-cn:...` |
| CloudFront 域名后缀 | `.cloudfront.net` | `.cloudfront.cn` |
| ICP 备案 | 不需要 | **强制**，且需走 AWS 互联网内容备案 |
| OAI vs OAC | 推荐 OAC | 目前 **OAI** 仍是主流可靠方案，OAC 部分场景可用 |
| 桶策略 Service Principal | `cloudfront.amazonaws.com` | 同上（**没有** `.cn` 后缀） |
| 边缘节点位置 | 全球 | 仅中国大陆境内 |

---

## 3. 端到端操作步骤

### 3.1 S3 准备

#### 3.1.1 创建桶 + 上传内容

- 桶名建议 = 自定义域名（例：`static.samplecompany.com.cn`）便于识别
- 区域 `cn-north-1` 或 `cn-northwest-1`
- 上传站点文件，确认根目录有 `index.html`

#### 3.1.2 关闭"静态网站托管"（OAI/OAC 模式不需要）

- 桶 → **属性** → **静态网站托管** → 编辑 → 选「禁用」
- 静态网站托管的 website endpoint（`xxx.s3-website.xxx`）只支持 HTTP，跟 OAI/OAC + REST endpoint 不兼容

#### 3.1.3 保持"阻止所有公共访问"开启

- 桶 → **权限** → **屏蔽公共访问权限** → 「阻止所有公共访问」**开启**
- OAI/OAC 模式下，桶不需要公开访问，CloudFront 通过签名身份读取

> ⚠️ 桶策略会单独授权给 CloudFront，不算公开访问，不与"阻止所有公共访问"冲突。

---

### 3.2 上传 SSL 证书到 IAM

#### 3.2.1 准备证书三件套

从签发平台（DigiCert、阿里云 CAS、腾讯云 SSL 等）下载 **Nginx 格式** 证书包，整理成：

```
cert.pem      # 服务器证书（一段 BEGIN/END CERTIFICATE）
chain.pem     # 中间 CA 证书（一段或多段，不要含根 CA）
privkey.pem   # 私钥（未加密的 RSA，PEM 格式）
```

如果只有一个 `.pem` 里塞了多段，拆分：

```bash
# 看里面有几段证书
grep -c "BEGIN CERTIFICATE" full.pem

# 自动拆分为 cert-1.pem cert-2.pem ...
awk '/-----BEGIN CERTIFICATE-----/{i++} {print > "cert-" i ".pem"}' full.pem
# cert-1.pem 是服务器证书 → 重命名为 cert.pem
# cert-2.pem (及之后) 是中间 CA → 合并/重命名为 chain.pem
```

#### 3.2.2 验证证书内容

```bash
# 确认 CN/SAN 与目标域名匹配
openssl x509 -in cert.pem -noout -subject -ext subjectAltName

# 期望输出包含目标域名，例：
# subject=CN=static.samplecompany.com.cn
# X509v3 Subject Alternative Name:
#     DNS:static.samplecompany.com.cn
#     DNS:www.static.samplecompany.com.cn

# 确认是 RSA 算法
openssl x509 -in cert.pem -noout -text | grep "Public Key Algorithm"
```

#### 3.2.3 上传到 IAM（path 必须 `/cloudfront/`）

```bash
aws iam upload-server-certificate \
  --server-certificate-name <证书别名> \
  --certificate-body file://cert.pem \
  --private-key file://privkey.pem \
  --certificate-chain file://chain.pem \
  --path /cloudfront/ \
  --profile <中国区 profile>
```

> ⚠️ IAM 是全局服务，命令不需要 `--region`，但需要中国区凭证（账号是 `arn:aws-cn:...`）。

#### 3.2.4 验证上传成功且链完整

```bash
# 列出所有 server certificate
aws iam list-server-certificates --profile <profile>

# 检查证书链是否非空（最常见的坑）
aws iam get-server-certificate \
  --server-certificate-name <证书别名> \
  --query 'ServerCertificate.CertificateChain' \
  --output text \
  --profile <profile>
```

期望输出：包含 `-----BEGIN CERTIFICATE-----` 的中间 CA 内容。
如果是 `None` → 链没传，CloudFront 下拉框会过滤掉这张证书。

---

### 3.3 创建 CloudFront 分配

#### 3.3.1 创建 OAI（Origin Access Identity）

控制台 → CloudFront → 左侧 **「源访问标识 / Origin access identities」** → 创建：

- 名称：`oai-<项目名>`
- 备注：随意

记下生成的 OAI ID（形如 `EXXXXXXXXXXXXX`）。

#### 3.3.2 创建分配

控制台 → CloudFront → **创建分配**：

| 配置项 | 值 |
|---|---|
| 源域名 | 选 S3 桶（**REST endpoint**，形如 `xxx.s3.cn-north-1.amazonaws.com.cn`，不要选 `.s3-website.` 那个） |
| 源路径 | 留空 |
| 名称 | 自动 |
| 源访问 / S3 桶访问 | **使用 OAI** → 选刚创建的 OAI |
| 桶策略 | 选「Yes, update the bucket policy」（控制台会自动更新桶策略） |
| 查看者协议策略 | **Redirect HTTP to HTTPS** |
| 允许的 HTTP 方法 | GET, HEAD |
| 缓存策略 | CachingOptimized（或自定义） |
| Alternate domain name (CNAMEs) | 填自定义域名，如 `static.samplecompany.com.cn` |
| 自定义 SSL 证书 | 下拉选刚才上传的 IAM 证书 |
| 安全策略 | TLSv1.2_2021（推荐） |
| **默认根对象** | `index.html`（**不可省略**，REST endpoint 不会自动找） |
| 价格级别 | 使用所有边缘站点 |
| ICP 备案号 | 填工信部备案号（如 `<你的 ICP 备案号>`） |

点「创建分配」，等状态从「正在部署」→「已部署」（中国区一般 5-15 分钟）。

#### 3.3.3（如果是 SPA）配置错误页面

分配 → **错误页面** tab → 创建两条：

| HTTP 错误代码 | TTL | 自定义错误响应 | 响应路径 | HTTP 响应代码 |
|---|---|---|---|---|
| 403 | 0 | 是 | `/index.html` | 200 |
| 404 | 0 | 是 | `/index.html` | 200 |

普通多页静态站可跳过。

---

### 3.4 配置 S3 桶策略（确认/修正）

如果上一步勾了「自动更新桶策略」，CloudFront 已经帮你写好。否则手动配置如下：

桶 → **权限** → **存储桶策略** → 编辑：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontOAI",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws-cn:iam::cloudfront:user/CloudFront Origin Access Identity <OAI_ID>"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws-cn:s3:::<桶名>/*"
        }
    ]
}
```

替换：
- `<OAI_ID>` → 你的 OAI ID（如 `EXXXXXXXXXXXXX`）
- `<桶名>` → 你的 S3 桶名

> ⚠️ 注意是 `arn:aws-cn:...` 不是 `arn:aws:...`。

---

### 3.5 配置 DNS

去域名注册商（万网/DNSPod/Cloudflare 等）添加 CNAME 记录：

| 类型 | 主机记录 | 值 | TTL |
|---|---|---|---|
| CNAME | `static`（子域部分） | `dXXXXXXXXXXXXX.cloudfront.cn`（你的分配域名） | 600 |

> ❌ **不要** 把 DNS 直接指向 `xxx.s3-website.cn-north-1.amazonaws.com.cn`，否则流量绕过 CloudFront，HTTPS 不通、CloudFront 配置全部失效。

DNS 生效验证：

```bash
dig +short <自定义域名>
# 期望看到解析到 dXXXXXXXXXXXXX.cloudfront.cn 然后是一堆 CloudFront 边缘 IP
```

---

### 3.6 ICP 备案（中国区强制）

#### 3.6.1 工信部 ICP 备案

- 主域名（如 `samplecompany.com.cn`）必须已在工信部完成 ICP 备案
- 子域名继承主域备案，无需单独申请
- 查询：https://beian.miit.gov.cn/

#### 3.6.2 AWS 互联网内容备案（独立流程）

- 在分配创建时需填写 ICP 备案号
- 分配创建后，**CNAME 状态**会从「待审核」→「已通过审核」（需 1-3 个工作日）
- 状态查看：CloudFront 分配列表 → 「CNAME 状态」列
- CLI：`aws cloudfront list-distributions --query 'DistributionList.Items[*].AliasICPRecordals'`

只有 **AWS 互联网内容备案** 通过后，分配才能正常服务流量。

---

## 4. 验证清单（端到端）

按顺序验证：

```bash
# 1. DNS 是否指向 CloudFront
dig +short <自定义域名>
# ✅ 期望：解析链含 .cloudfront.cn

# 2. HTTPS 访问通畅
curl -I https://<自定义域名>/
# ✅ 期望：HTTP/2 200，header 有 x-cache: ... CloudFront

# 3. HTTP 自动重定向到 HTTPS
curl -I http://<自定义域名>/
# ✅ 期望：301，Location: https://...

# 4. SSL 证书正确
openssl s_client -connect <自定义域名>:443 -servername <自定义域名> < /dev/null 2>/dev/null | openssl x509 -noout -subject -dates
# ✅ 期望：subject CN 与域名匹配，有效期内

# 5. 直连 S3 应被拒绝
curl -I https://<桶名>.s3.cn-north-1.amazonaws.com.cn/index.html
# ✅ 期望：403 AccessDenied（说明桶私有，必须经过 CloudFront）
```

---

## 5. 常见错误对照表

| 现象 | 根因 | 解决 |
|---|---|---|
| CloudFront 创建分配时「自定义 SSL 证书」下拉框为空 | 1️⃣ 没填 CNAME；2️⃣ 证书 path 不是 `/cloudfront/`；3️⃣ 证书 CN/SAN 与 CNAME 不匹配；4️⃣ **证书链 (CertificateChain) 为空** | 检查这 4 项；最常见是 #4，需重传带 `--certificate-chain` |
| HTTP 通、HTTPS 不通 | DNS 直接指向 S3 website endpoint，绕过了 CloudFront | DNS CNAME 改成指向 `.cloudfront.cn` 域名 |
| HTTPS 报 `AccessDenied` | 1️⃣ 桶策略未授权 OAI；2️⃣ 用了 REST endpoint 但没配 OAI/OAC；3️⃣ 桶策略 ARN 用了 `arn:aws:` 而非 `arn:aws-cn:` | 按 3.4 节配置桶策略 |
| 访问 `/` 返回 403，访问 `/index.html` 正常 | REST endpoint 不会自动找 index | CloudFront 分配 → 设置 → **默认根对象** = `index.html` |
| SPA 刷新非首页路径（如 `/dashboard`）返回 403 | S3 没有该 key，REST endpoint 直接 403 | 配置错误页面规则：403/404 → `/index.html` → 200 |
| 证书上传 IAM 成功但 CloudFront 看不到 | 99% 是证书链没传 | `aws iam get-server-certificate ... --query 'ServerCertificate.CertificateChain'` 检查，为空就删除重传 |
| `aws iam list-server-certificates` 看不到证书 | profile 用错了（用了全球区 profile 查中国区证书） | 加 `--profile <中国区profile>` |
| 改了配置但访问还是旧的 | CloudFront 缓存或浏览器缓存 | CloudFront → 失效（Invalidation）→ 创建 `/*`；浏览器 Ctrl+Shift+R |
| CNAME 状态一直「待审核」 | AWS 互联网内容备案未通过 | 等待审核，或检查 ICP 备案号是否有效 |

---

## 6. CLI 速查

### 证书管理

```bash
# 列出所有 IAM server certificate
aws iam list-server-certificates --profile <profile>

# 上传（path 必须 /cloudfront/）
aws iam upload-server-certificate \
  --server-certificate-name <name> \
  --certificate-body file://cert.pem \
  --private-key file://privkey.pem \
  --certificate-chain file://chain.pem \
  --path /cloudfront/ \
  --profile <profile>

# 检查证书链
aws iam get-server-certificate \
  --server-certificate-name <name> \
  --query 'ServerCertificate.CertificateChain' \
  --output text \
  --profile <profile>

# 删除（如该证书已被 CloudFront 引用，需先解除引用）
aws iam delete-server-certificate \
  --server-certificate-name <name> \
  --profile <profile>
```

### CloudFront 管理

```bash
# 列分配
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].[Id,DomainName,Aliases.Items,Status]' \
  --output table \
  --profile <profile>

# 看某个分配的备案状态
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].AliasICPRecordals' \
  --output json \
  --profile <profile>

# 创建失效（清缓存）
aws cloudfront create-invalidation \
  --distribution-id <DistID> \
  --paths "/*" \
  --profile <profile>
```

### DNS / 网络验证

```bash
# 解析链
dig +short <domain>

# 含 CNAME 详情
dig <domain> CNAME +short

# 测试 HTTPS
curl -I https://<domain>/
curl -vI https://<domain>/ 2>&1 | grep -E "subject|issuer|HTTP"

# 测试 HTTP 重定向
curl -I http://<domain>/
```

---

## 7. 维护建议

### 7.1 证书续期

- 第三方证书一般 1 年期，到期前 30 天准备续期
- 续期流程：在签发平台续费 → 下载新证书 → 上传 IAM（用新名字，如加 `-2027`）→ CloudFront 分配编辑 → 切换到新证书 → 等部署完 → 删旧证书

### 7.2 OAI 迁移到 OAC（可选，未来优化）

- AWS 推荐新部署用 OAC，OAI 是遗留方案
- 中国区 OAC 已支持，但部分场景兼容性需测试
- 迁移时桶策略 `Principal` 从 `AWS: ...iam:...OAI...` 改为 `Service: cloudfront.amazonaws.com` + `Condition: AWS:SourceArn`

### 7.3 监控

- CloudFront → 报告和分析 → 缓存统计/常用对象 → 看命中率
- CloudWatch → CloudFront namespace → `4xxErrorRate`、`5xxErrorRate` 设告警
- 大量 403 通常意味着 SPA 错误页配置丢了或新增了路径

---

## 8. 本次实战时间线（参考）

实战中遇到的问题顺序，可作为后续踩坑判断参考：

1. ❌ 证书上传 IAM，path 默认 `/`，CloudFront 下拉看不到 → 改 path `/cloudfront/`
2. ❌ path 改对了，下拉还是空 → 发现没填 CNAME（或 CNAME 与 CN/SAN 不匹配）
3. ❌ CNAME 也填了，下拉还是空 → 发现证书链 `CertificateChain=None`，删除重传带 chain
4. ✅ 证书绑定成功，但 HTTPS 访问失败、HTTP 正常 → DNS 直接指向了 S3 website endpoint，改 CNAME 指向 `.cloudfront.cn`
5. ❌ HTTPS 通了但报 `AccessDenied` → 桶策略与 endpoint 模式冲突，改用 OAI + 私有桶
6. ✅ 配置 OAI + 桶策略 `Principal: arn:aws-cn:iam::cloudfront:user/...OAI...` → 全部通畅

---

**文档版本**：v1.0
**编写日期**：2026-05-19
**适用区域**：AWS 中国区（cn-north-1 / cn-northwest-1）
