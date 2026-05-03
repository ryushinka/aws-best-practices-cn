# IAM 分组访问 EC2 — 控制台操作手册（中国区）

> **场景**: GroupA（10人）和 GroupB（10人）分别访问各自的 EC2 实例
> **权限**: SSH 登录、启停、重启（不含创建/终止）
> **区域**: AWS 中国区 (aws-cn)
> **登录方式**: SSH 密钥

---

## 架构总览

```
GroupA (10人)                          GroupB (10人)
   │                                      │
   ├── IAM Group: GroupA                   ├── IAM Group: GroupB
   │     │                                 │     │
   │     └── Policy: GroupA-EC2-Access     │     └── Policy: GroupB-EC2-Access
   │                                       │
   └── 可访问:                             └── 可访问:
       ├── EC2 (Tag: Team=GroupA) ✅           ├── EC2 (Tag: Team=GroupB) ✅
       └── EC2 (Tag: Team=GroupB) ❌           └── EC2 (Tag: Team=GroupA) ❌
```

---

## 第一步：给 EC2 实例打标签

### 1.1 打开 EC2 控制台

1. 登录 AWS 中国区控制台: `https://console.amazonaws.cn`
2. 在顶部搜索栏输入 **EC2**，点击进入

### 1.2 给 GroupA 的实例打标签

1. 左侧菜单点击 **实例 (Instances)**
2. 勾选属于 GroupA 的实例（可多选）
3. 点击上方 **操作 (Actions)** → **实例设置 (Instance Settings)** → **管理标签 (Manage Tags)**
4. 点击 **添加标签 (Add Tag)**:
   - **键 (Key)**: `Team`
   - **值 (Value)**: `GroupA`
5. 点击 **保存 (Save)**

### 1.3 给 GroupB 的实例打标签

重复上述步骤，选择 GroupB 的实例，标签值改为：
- **键 (Key)**: `Team`
- **值 (Value)**: `GroupB`

### 1.4 验证标签

1. 在实例列表页，点击任意一台实例
2. 切换到 **标签 (Tags)** 选项卡
3. 确认 `Team` 标签值正确

> ⚠️ **注意**: 标签值大小写敏感，`GroupA` 和 `groupa` 是不同的，后面策略要完全匹配。

---

## 第二步：创建 IAM 策略

### 2.1 创建 GroupA 的 EC2 策略

1. 顶部搜索栏输入 **IAM**，点击进入
2. 左侧菜单点击 **策略 (Policies)**
3. 点击 **创建策略 (Create Policy)**
4. 点击 **JSON** 选项卡
5. 粘贴以下内容：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowDescribeAll",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeTags",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "ec2:DescribeKeyPairs",
        "ec2:DescribeImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowEC2ActionsGroupA",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances"
      ],
      "Resource": "arn:aws-cn:ec2:*:*:instance/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Team": "GroupA"
        }
      }
    },
    {
      "Sid": "DenyTeamTagModification",
      "Effect": "Deny",
      "Action": [
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "arn:aws-cn:ec2:*:*:instance/*",
      "Condition": {
        "ForAnyValue:StringEquals": {
          "aws:TagKeys": ["Team"]
        }
      }
    }
  ]
}
```

6. 点击 **下一步 (Next)**
7. **策略名称**: `GroupA-EC2-Access`
8. **描述**: `允许 GroupA 成员启停和重启 Team=GroupA 的 EC2 实例`
9. 点击 **创建策略 (Create Policy)**

### 2.2 创建 GroupB 的 EC2 策略

重复 2.1 的步骤，但把 JSON 中的 `GroupA` 改为 `GroupB`：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowDescribeAll",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeTags",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "ec2:DescribeKeyPairs",
        "ec2:DescribeImages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowEC2ActionsGroupB",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances"
      ],
      "Resource": "arn:aws-cn:ec2:*:*:instance/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Team": "GroupB"
        }
      }
    },
    {
      "Sid": "DenyTeamTagModification",
      "Effect": "Deny",
      "Action": [
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "arn:aws-cn:ec2:*:*:instance/*",
      "Condition": {
        "ForAnyValue:StringEquals": {
          "aws:TagKeys": ["Team"]
        }
      }
    }
  ]
}
```

- **策略名称**: `GroupB-EC2-Access`
- **描述**: `允许 GroupB 成员启停和重启 Team=GroupB 的 EC2 实例`

---

## 第三步：创建 IAM 用户组

### 3.1 创建 GroupA

1. IAM 控制台左侧菜单点击 **用户组 (User Groups)**
2. 点击 **创建组 (Create Group)**
3. **组名**: `GroupA`
4. 在 **附加权限策略 (Attach permissions policies)** 搜索框中：
   - 搜索 `GroupA-EC2-Access`，勾选 ✅
5. 点击 **创建组 (Create Group)**

### 3.2 创建 GroupB

重复上述步骤：
- **组名**: `GroupB`
- 附加策略: `GroupB-EC2-Access`

---

## 第四步：创建 IAM 用户并加入组

### 4.1 创建用户（以 GroupA 的第一个用户为例）

1. IAM 左侧菜单点击 **用户 (Users)**
2. 点击 **创建用户 (Create User)**
3. **用户名**: 例如 `groupa-user01`
4. 勾选 **提供用户对 AWS 管理控制台的访问权限**（如果需要控制台登录）
5. 选择 **我想创建 IAM 用户**
6. 设置密码方式（自定义或自动生成）
7. 点击 **下一步 (Next)**

### 4.2 将用户加入组

1. 选择 **将用户添加到组 (Add user to group)**
2. 勾选 **GroupA** ✅
3. 点击 **下一步 (Next)**
4. 点击 **创建用户 (Create User)**

### 4.3 创建 Access Key（用于 CLI 场景）

1. 点击刚创建的用户名进入详情
2. 切换到 **安全凭证 (Security Credentials)** 选项卡
3. 滚动到 **访问密钥 (Access Keys)** 部分
4. 点击 **创建访问密钥 (Create Access Key)**
5. 选择用途: **命令行界面 (CLI)**
6. 点击 **创建**
7. **⚠️ 立即下载或复制 Access Key ID 和 Secret Access Key**（只显示一次）

### 4.4 重复创建其余用户

- GroupA: `groupa-user01` 到 `groupa-user10`，全部加入 `GroupA` 组
- GroupB: `groupb-user01` 到 `groupb-user10`，全部加入 `GroupB` 组

---

## 第五步：配置 SSH 密钥对

### 5.1 创建密钥对（如果还没有）

1. 进入 **EC2 控制台** → 左侧菜单 **网络与安全 (Network & Security)** → **密钥对 (Key Pairs)**
2. 点击 **创建密钥对 (Create Key Pair)**
3. 方案选择（二选一）：

**方案 A：每组一个密钥对**（简单，推荐）
- 创建 `keypair-groupa`，下载 `.pem` 文件，分发给 GroupA 10 人
- 创建 `keypair-groupb`，下载 `.pem` 文件，分发给 GroupB 10 人

**方案 B：每人一个密钥对**（更安全，可追溯）
- 为每个用户创建独立密钥对

### 5.2 确保 EC2 实例使用对应密钥对

- GroupA 的实例启动时选择 `keypair-groupa`
- GroupB 的实例启动时选择 `keypair-groupb`

> 已有实例如果要换密钥，需要登录实例修改 `~/.ssh/authorized_keys` 文件。

### 5.3 安全组配置

确保 EC2 实例的安全组允许 SSH 入站：

1. EC2 控制台 → **安全组 (Security Groups)**
2. 选择实例关联的安全组
3. **入站规则 (Inbound Rules)** → **编辑**
4. 添加规则:
   - **类型**: SSH
   - **端口**: 22
   - **来源**: 限制为公司 IP 段（如 `203.0.113.0/24`），**不要用 0.0.0.0/0**

---

## 第六步：验证

### 6.1 验证 EC2 权限

**用 GroupA 用户登录控制台测试：**

1. 用 `groupa-user01` 登录 AWS 控制台
2. 进入 EC2 → 实例列表
3. 选择一台 **Team=GroupA** 的实例 → 点击 **实例状态 (Instance State)** → **停止实例**
   - ✅ 应该成功
4. 选择一台 **Team=GroupB** 的实例 → 点击 **实例状态** → **停止实例**
   - ❌ 应该报错: `You are not authorized to perform this operation`

### 6.2 验证 SSH 登录

```bash
# GroupA 用户 SSH 到 GroupA 的实例 — 应该成功
ssh -i keypair-groupa.pem ec2-user@<GroupA实例公网IP>

# GroupA 用户 SSH 到 GroupB 的实例 — 连不上（密钥不匹配）
ssh -i keypair-groupa.pem ec2-user@<GroupB实例公网IP>
```

---

## 第七步：日常运维操作

### 新增用户

1. IAM → 用户 → 创建用户
2. 加入对应的组（GroupA 或 GroupB）
3. 分发对应的 SSH 密钥文件
4. 完成，不需要改任何策略

### 新增 EC2 实例

1. 启动新实例时选择对应的密钥对
2. 给实例打标签: `Team` = `GroupA` 或 `GroupB`
3. 完成，不需要改任何策略

### 用户离职

1. IAM → 用户 → 选择用户 → 删除
2. 如果用的是每人独立密钥对，可以去实例上删除对应的 `authorized_keys` 条目

---

## 完整策略清单

| 策略名称 | 附加到 | 作用 |
|----------|--------|------|
| `GroupA-EC2-Access` | GroupA | 允许启停/重启 Team=GroupA 的 EC2 |
| `GroupB-EC2-Access` | GroupB | 允许启停/重启 Team=GroupB 的 EC2 |

## 资源标签规范

| 标签键 | 标签值 | 用途 |
|--------|--------|------|
| `Team` | `GroupA` 或 `GroupB` | EC2 实例权限隔离 |

---

## 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 用户看不到任何实例 | 缺少 `ec2:Describe*` 权限 | 检查策略中 AllowDescribeAll 部分 |
| 用户能看到但不能操作自己组的实例 | 标签值不匹配 | 检查实例标签 `Team` 的值是否和策略中完全一致（大小写敏感） |
| 用户能操作别人组的实例 | 有其他策略给了更宽权限 | 检查用户是否还在其他组，或是否有直接附加的策略 |
| SSH 连不上 | 安全组/密钥/网络问题 | 1. 检查安全组 22 端口 2. 检查密钥文件权限 `chmod 400` 3. 检查实例是否有公网 IP |
| 控制台登录后什么都看不到 | 用户没有控制台访问权限 | 创建用户时要勾选"控制台访问" |

---

## 安全建议

1. **启用 MFA**: IAM → 用户 → 安全凭证 → 分配 MFA 设备
2. **定期轮换密钥**: 建议每 90 天轮换 Access Key 和 SSH 密钥
3. **启用 CloudTrail**: 记录所有 API 调用，便于审计
4. **最小权限原则**: 当前策略已经是最小权限，不要随意添加 `*` 通配符
5. **SSH 来源限制**: 安全组中 SSH 来源一定要限制 IP，不要开放 `0.0.0.0/0`
