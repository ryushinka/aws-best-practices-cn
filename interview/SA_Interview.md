# SA / 售前 面试题集

> 按 AWS Pillar 组织的 SA 面试题池。每题包含 **主问 → 追问 → 要点 → AWS 映射**。
> 挑和候选人简历相关的问，不用全问。
> 看重 **广度 + 选型思维 + 能把原理翻译到 AWS 服务 + 客户视角**。

---

## 目录

1. [计算](#一计算)
2. [存储与数据库](#二存储与数据库)
3. [网络](#三网络)
4. [安全](#四安全)
5. [应用集成与分布式架构](#五应用集成与分布式架构)
6. [GenAI](#六genai)
7. [架构白板题](#七架构白板题)
8. [软技能与异议处理](#八软技能与异议处理)

---

## 一、计算

### Q1. EC2 实例家族选型

**主问**：客户要跑一个 Java 后端服务，QPS 2 万，你会给他推荐什么实例类型？

**追问**：
- M / C / R / X / G / Inf 这几类实例家族分别是干嘛的？
- Graviton（ARM）和 Intel/AMD 实例怎么选？
- 内存密集型应用选 R 还是 X？
- T 系列可以跑生产吗？CPU 积分（burst credit）耗尽会发生什么？

**要点**：
- M 平衡型（通用后端）；C 计算型（CPU 密集，如视频转码）；R 内存型（内存计算、Redis）；X 超大内存（HANA、大数据）
- G 带 GPU（图形、训练小模型）；Inf 推理专用（Inferentia 芯片，LLM 推理成本更低）
- Graviton：**同代同规格比 x86 便宜 20%、性能更好**，几乎所有新 workload 都应考虑
- Graviton 不适合：有 x86 native 依赖（如老版本 Oracle JDK Native Agent）
- T 系列（可突增）：baseline 之下攒 **CPU 积分**，突发时消耗；T2 积分耗尽回落到 baseline，T3/T4g 可开 **Unlimited 模式**继续冲（按超额 vCPU-hour 收费）；**T4g（Graviton2）比 T3 便宜约 20%、性价比高约 40%**，小规格场景优先考虑

### Q2. Spot / On-Demand / Reserved / Savings Plans

**主问**：客户的 EC2 账单越来越贵，你会怎么帮他优化？

**追问**：
- Spot 实例的风险是什么？什么场景适合用 Spot？
- Reserved Instance 和 Savings Plans 的区别？
- Compute Savings Plans 和 EC2 Instance Savings Plans 怎么选？

**要点**：
- Spot：**折扣 70~90%**，但 2 分钟预警后会被回收；适合**无状态 + 可中断**（CI/CD、批处理、Spark、Fargate Spot）
- RI：绑定实例家族 + Region，1 年或 3 年
- Savings Plans：**更灵活**，承诺每小时 $X 消费，可用在 EC2/Fargate/Lambda，覆盖范围更广
- Compute SP > EC2 Instance SP：前者跨家族跨 Region 都适用，后者只锁定家族但折扣更大
- **Standard RI vs Convertible RI**：Standard 同 family 内可免费互转（2×large ↔ 1×xlarge）、可在 RI Marketplace 转卖；Convertible 贵约 10%，可跨 family 转但只补差价不退款、不能挂牌卖
- **Dedicated Instance vs Dedicated Host**：前者按硬件独占，但 Region 级 fee（约 $10/小时封顶，不随实例数线性叠加）+ 约 10% 实例溢价；后者可指定物理机（合规审计用）
- **优化顺序**：先 Right Sizing → 再 Savings Plans / RI → 再 Spot

### Q3. Lambda vs Fargate vs EC2

**主问**：一个新项目，Web 后端 + 定时任务，你会推 Lambda、Fargate 还是 EC2？

**追问**：
- Lambda 的使用边界是什么？什么场景不该用 Lambda？
- Lambda 冷启动的根因？怎么优化？
- 为什么说 Fargate 是"没有服务器的容器"？和 EC2 ECS 区别？
- Lambda container image 和 zip 部署的差异？Function URL 是什么？
- 老应用（PHP / Spring Boot）能不改代码上 Lambda 吗？

**要点**：
- **Lambda 不适合**：长时任务（> 15 分钟）、冷启动敏感（P99 要求 < 100ms）、WebSocket 长连接、重计算（CPU/GPU）
- 冷启动根因：解压部署包 + 启动 runtime + 初始化代码；Java/.NET 冷启动最严重
- 冷启动优化：**Provisioned Concurrency**（预留实例）、**SnapStart**（Java 快速启动）、**GraalVM Native Image**、减小部署包
- Fargate：按容器计费，不管底层 EC2；适合"容器化但不想管节点"
- EC2 适合：长连接、重计算、特殊硬件（GPU）、极致成本控制
- Lambda **Container Image** 支持最多 10GB 镜像（zip 包 250MB 解压后）；**Function URL** 直接给 Lambda 一个 HTTPS 端点，不需要 API Gateway
- **AWS Lambda Web Adapter** 可把 HTTP 请求转成 Lambda event，老 PHP/Spring Boot 等 web 框架一行代码不改也能上 Lambda

### Q4. Auto Scaling 策略

**主问**：客户流量有明显的早晚高峰，Auto Scaling 应该怎么配？

**追问**：
- Target Tracking / Step Scaling / Scheduled Scaling 分别什么场景？
- 为什么扩容快、缩容慢是最佳实践？
- 冷启动期间请求失败怎么办？
- 预测式扩缩容（Predictive Scaling）靠谱吗？
- 有状态应用缩容时怎么优雅下线（排日志、注销服务）？
- EC2 看得到 CPU，为什么看不到内存和磁盘？

**要点**：
- **Target Tracking**：最简单，锁定 CPU 50% 之类的目标值
- **Step Scaling**：按指标阈值分段扩容（CPU > 70 加 1 台，> 85 加 3 台）
- **Scheduled Scaling**：定时扩缩，适合业务规律明显（电商早高峰）
- 扩容快缩容慢：避免抖动，防止"刚缩完又来一波流量"
- 冷启动：加 **预热（Warmup）** 时间、健康检查未通过前不接流量
- Predictive Scaling：基于历史 ML 预测，适合周期性极强的场景
- **Lifecycle Hook**：实例进入 `Pending:Wait` / `Terminating:Wait` 时触发 EventBridge → SSM Automation，在终止前把日志打包上 S3、或从服务注册中心注销服务；默认心跳超时 1 小时、全局最长 48 小时，必须显式 `complete-lifecycle-action` 或超时放弃，否则扩缩会被挂住
- CloudWatch 默认**不采内存和磁盘使用率**（这些在 OS 内，属于客户数据），必须装 **CloudWatch Agent** 才能上报；配合 SSM Parameter Store 可把 agent 配置集中下发到多台 EC2

### Q4a. 服务配额与账户韧性

**主问**：客户大促当天开不出实例、ELB 建不出来，根因怎么排查、怎么预防？

**追问**：
- EC2、EBS、VPC、ELB、IAM 这些资源有哪些典型配额？
- 配额快打满了怎么提前预警？
- 跨账号怎么做"配额监控中枢"？

**要点**：
- Service Quotas 按服务和 Region 维度管理，部分可自助提升、部分要开 case
- 可用 **Trusted Advisor + Lambda + SNS** 组合：配额打到 80% 自动发邮件
- 跨账号方案：主账号配跨账号 IAM Role（成员账号信任主账号 + `ReadOnlyAccess` + `AWSSupportAccess` + 自定义策略），把一个主账号作为"配额监控中枢"
- 严重配额（例如 vCPU、EIP、NAT Gateway、ELB 数）**在大促前至少 2 周**走 case 提升

**AWS 映射**：Service Quotas、Trusted Advisor、CloudWatch Alarm、Lambda、SNS、Organizations（跨账号聚合）

### Q4b. EC2 实例无法启动的救援

**主问**：客户的 EC2 由于误改 `/etc/fstab` 开不起来，SSH 也进不去，怎么救？

**追问**：
- AWS 没有 VNC 控制台，怎么修复根盘？
- 同 AMI 产生的 EBS 挂到救援机，为什么 mount 报错？
- 救援修复完挂回原机需要注意什么？

**要点**：
- 流程：**停止原实例 → 从原实例卸载根 EBS → 挂到救援 EC2（同 AZ）→ 挂载修复 → 卸载 → 挂回原实例**
- 同 AMI（如 Amazon Linux 2 XFS）生成的卷挂载会有 **UUID 冲突**，必须 `mount -t xfs -o nouuid`
- 挂回去时**设备名必须是 `/dev/xvda`**（根设备），不能用默认的 `/dev/sdf`
- 平时预防：开 **EC2 Serial Console**（支持的实例家族）、定期打 EBS Snapshot、关键机器用 SSM Session Manager 替代 SSH

**AWS 映射**：EC2、EBS Snapshot、SSM Session Manager、EC2 Serial Console

---

## 二、存储与数据库

### Q5. S3 一致性与存储类

**主问**：S3 的一致性模型是什么？适合做哪些场景？

**追问**：
- S3 Standard / IA / Glacier / Glacier Deep Archive 怎么选？
- Intelligent-Tiering 是什么？什么时候用？
- S3 和 EFS、EBS 的本质区别？
- 大文件上传（> 100MB）怎么做？

**要点**：
- 2020 年后 S3 全部对象是**强一致性**（Read-after-Write + List-after-Write）
- 存储类按**访问频率**选：Standard（频繁）→ IA（每月几次）→ Glacier Instant（季度）→ Glacier Flexible（年）→ Deep Archive（极少，取回 12 小时）
- Intelligent-Tiering：**自动分层**，不知道访问模式时的默认选择
- EBS：块存储，挂到 EC2，单实例独占；EFS：NFS 文件系统，多实例共享；S3：对象存储，HTTP API 访问
- 大文件：**Multipart Upload**，并行上传分片，断点续传
- 单对象/文件大小上限：**S3 单对象 5TB**（PUT 单次 5GB，超过须 multipart）、**EFS 单文件 47.9TiB**、**EBS 单卷 16TB**
- S3 吞吐：单前缀 **PUT/LIST/DELETE 3500 TPS、GET 5500 TPS**，热点可按前缀分片横向扩

### Q6. EBS vs EFS vs FSx

**主问**：客户要在多台 EC2 之间共享文件，用什么？

**追问**：
- EBS 能挂到多台 EC2 吗？
- EFS 和 FSx 区别？FSx for Windows / FSx for Lustre 分别干嘛？
- EBS 的 gp3 和 gp2 有什么区别？什么时候用 io1/io2？

**要点**：
- EBS：块存储，单实例独占（EBS Multi-Attach 支持 Nitro 实例共享，但要应用层做并发控制）
- EFS：NFS 协议，**Linux 多实例共享**，弹性扩容
- FSx for Windows：**SMB 协议**，Windows 环境必选
- FSx for Lustre：**高性能并行文件系统**，HPC 和机器学习训练；可从 S3 导入/导出，训练任务复用避免重复下载 TB 级数据集
- EBS gp3：**可独立配置 IOPS 和吞吐**，比 gp2 更灵活且便宜；io1/io2：高 IOPS（数万以上）数据库场景
- EFS 默认吞吐随容量线性扩（约 50 MiB/s/TiB），或切 Provisioned Throughput；突发吞吐可达 3 GB/s

### Q7. MySQL 索引与查询优化

**主问**：联合索引 `(a, b, c)`，`where a=1 and b>10 and c=2`，哪些字段走索引？

**追问**：
- 聚簇索引和二级索引区别？什么是回表？
- 覆盖索引是什么？能解决什么问题？
- 什么情况下索引会失效？

**要点**：
- a 和 b 走索引，**c 不走**（b 的范围查询打乱了 c 的顺序）
- 聚簇索引叶子存**整行**，二级索引叶子存**主键值** → 需要**回表**
- 覆盖索引：查询字段都在索引里，不用回表
- 索引失效：**隐式类型转换**（字符串字段用数字比较）、函数操作列（`WHERE DATE(col) = ...`）、`!=` 和 `NOT IN`、`LIKE '%xxx'`

**AWS 映射**：
- RDS Performance Insights 直接看慢 SQL 和 wait event
- Performance Insights 核心指标是 **DB Load**，可按 **wait event / SQL / host / user** 四维度拆；RDS MySQL 的 wait event 命名来自 MySQL Performance Schema（如 `io/table/sql/handler` 是表 I/O 等待），不开 Performance Schema 时降级显示 processlist state
- Aurora 的索引结构和 MySQL 一致，但底层存储是 6 副本分布式

### Q8. 事务与隔离级别

**主问**：MySQL 默认是 RR，为什么大部分互联网公司改成 RC？

**追问**：
- 脏读、不可重复读、幻读分别举例？
- RR 下 InnoDB 怎么防幻读？
- RDS 和 Aurora 的默认隔离级别都是什么？能改吗？

**要点**：
- RC 性能更好、锁范围小、不会 gap lock 死锁
- RR 下 InnoDB 用 **MVCC + Next-Key Lock**（行锁 + 间隙锁）防幻读
- RDS / Aurora 默认 RR，可以通过 **Parameter Group** 改成 RC
- Aurora 底层存储分布式，但 MVCC 逻辑在计算层，和 MySQL 一致

### Q9. 分库分表 vs Aurora

**主问**：客户日订单 100 万，MySQL 单库快撑不住了，你会推分库分表、读写分离，还是 Aurora？

**追问**：
- 分库和分表有什么区别？什么时候分哪个？
- 水平拆分和垂直拆分？按 range 还是 hash？
- 分库分表后 ID 怎么生成？
- 已有系统分库分表，怎么平滑迁移？
- 从 RDS MySQL 或自建 MySQL 迁到 Aurora，怎么把停机时间压到最小？
- "优化数据库"从查询到分片有没有一条标准的演进路径？

**要点**：
- 选型顺序：**读写分离 → 加缓存 → 分表 → 分库 → 分库分表**（能不拆就不拆）
- 更完整的演进路径：**查询优化 + 连接池 → 应用缓存 → 读写分离 → 分区（partition）→ 分片（shard）→ 多主**，每一步出现的瓶颈决定下一步是否触发
- 单表经验：> 500 万~1000 万行性能明显下降
- Range 分片：扩容方便、但有**写入热点**（新数据集中）
- Hash 分片：分布均匀、但扩容要迁移
- ID：雪花算法 / 号段模式（Leaf）

**AWS 映射**：
- **很多场景可以用 Aurora 代替分库分表**：单库最大 128TB、15 个只读副本、自动扩容
- 真需要分片：**Aurora Limitless Database**（新）、Aurora + ShardingSphere、或 **DynamoDB**
- 迁移推荐：**DMS**（Database Migration Service），支持双写阶段
- 最小停机迁移两条路：
  1. **RDS MySQL → Aurora**："Create Aurora read replica" → promote，几乎零停机
  2. **自建/EC2 MySQL → Aurora**：`xtrabackup --slave-info` 全量传 S3 → "Restore from S3" → `CALL mysql.rds_set_external_master` 把 Aurora 配成源 MySQL 的 slave 做增量追平 → 切流

### Q10. Aurora 核心架构

**主问**：Aurora 和自建 MySQL 主从相比，核心差异是什么？

**追问**：
- Aurora 为什么能做到 15 个只读副本几乎无延迟？
- Aurora 的"存储层共享"是什么意思？数据丢失风险怎么样？
- Aurora Global Database 跨 Region 同步怎么保证？
- 什么场景下不该用 Aurora？

**要点**：
- 前提：**传统 RDS Multi-AZ 的同步复制是在 EBS 块级做的**（AWS 官方 re:Invent DAT302 口径："replication is at the block level, not logical replication"），不是 binlog；因此 standby **不能当读副本用**，本质上就是另一个挂着没启动的 EBS
- **存储和计算分离**：底层分布式存储（**6 副本跨 3 AZ**），所有实例共享同一份数据
- 存储层把数据切 **10GB 固定 Segment**，6 副本（3 AZ×2）构成一个 PG；满足 **Vw+Vr > V、Vw > V/2**（V=6, Vw=4, Vr=3），即"丢 2 副本不影响写、丢 3 副本不影响读"
- 主库只负责"**写 redo log 到存储层**"，不负责数据刷盘；只读副本直接从存储层读
- 读副本是**读同一份存储 + 消费 redo log**，不走传统主从复制，所以 15 副本几乎无延迟（典型 **< 20ms**）；副本只应用 **SDL ≤ VDL** 的记录，否则会读到未持久化页
- Aurora 用 **LSN / VCL / CPL / VDL** 四级指针代替传统 ARIES：VCL 是存储层连续 LSN 的上限、CPL 是 mini-transaction 的一致点、**VDL = 最新且 ≤ VCL 的 CPL**；crash recovery 由存储层自己完成，数据库层通常 10 秒内可用
- Aurora Global Database：底层存储级异步复制，跨 Region 延迟 < 1 秒
- 不该用 Aurora：对 MySQL 版本有特殊要求、依赖特殊插件、小规模（RDS 更便宜）；**成本上**，Aurora 每百万 I/O 请求 $0.2，而 gp2 RDS 的 I/O 已含在卷费中——中小库在 gp2 的 burst credit 下其实性能够用，不能一刀切改 Aurora

**AWS 映射**：
- **只有 Aurora、RDS 没有**：Aurora Serverless v2、Global Database、Limitless Database、机器学习集成（Bedrock/Comprehend/SageMaker）、零 ETL（Redshift）、Zero-Downtime Patching
- **两边都有**：RDS Proxy、Secrets Manager 集成、Blue/Green Deployment

### Q11. DynamoDB 分区键设计

**主问**：DynamoDB 和 RDS 什么时候选哪个？

**追问**：
- 分区键（Partition Key）设计的核心原则？
- 什么是**热分区**？怎么避免？
- GSI 和 LSI 区别？
- On-Demand vs Provisioned 怎么选？
- DynamoDB 的强一致读和最终一致读分别用在什么场景？

**要点**：
- 选 DynamoDB：**单表数据量大 + 访问模式固定 + 需要毫秒级延迟 + 不需要复杂 join**
- 选 RDS：**关系型数据 + 复杂查询 + 事务**
- 分区键设计原则：**高基数（唯一值多）+ 均匀分布**；避免 `userId` 当分区键如果有大 V 用户（热分区）
- 热分区解决：**写入 sharding**（分区键后拼 `#01~#10`）、使用 **Adaptive Capacity**（Auto）
- GSI：全局二级索引，分区键和主表不同；LSI：本地二级索引，分区键和主表相同、只能建表时创建
- On-Demand：无法预估流量用；Provisioned：流量可预测，更便宜，可配 Auto Scaling
- 强一致读：价格 2x，延迟稍高，用于事后立即读刚写入的数据

### Q12. ElastiCache 选型

**主问**：客户要上 Redis 做缓存，推 ElastiCache 还是自建？

**追问**：
- Redis vs Memcached 怎么选？
- Cluster Mode Enabled vs Disabled 区别？
- `maxmemory-policy` 几种策略？`allkeys-lru` 和 `volatile-lru` 区别？
- ElastiCache 和 MemoryDB 什么关系？什么时候用哪个？

**要点**：
- ElastiCache 优势：Multi-AZ、备份、监控、补丁、无需运维
- Redis vs Memcached：Redis 功能丰富（持久化、复制、复杂数据结构、Lua）；Memcached 更简单、多线程、仅做纯缓存
- Cluster Mode Enabled：**自动分片**到多个 shard；Disabled：单 shard 主从，适合容量不大
- `allkeys-lru`：任何 key 都可能淘汰；`volatile-lru`：只淘汰设过 TTL 的 key
- **MemoryDB** 是**持久化的 Redis**，用 Multi-AZ Transaction Log 代替 AOF，可做主数据库；ElastiCache 定位是缓存，可能丢数据
- **代价要知道**：MemoryDB 为了持久化**写性能约为 ElastiCache 的 1/5**（SET: 16k qps vs 106k qps），读性能基本持平（GET、SPOP 都 10 万+），且价格贵一些；选型口径：**"可能丢数据但便宜快"选 ElastiCache，"主数据库语义不丢"选 MemoryDB**

### Q13. 缓存三连

**主问**：缓存穿透、击穿、雪崩怎么处理？

**追问**：
- 布隆过滤器原理？缺点？
- 热点 key 失效除了永不过期还有啥办法？
- Redis 集群整个挂了怎么办？
- 缓存和 DB 一致性方案？

**要点**：
- 穿透（查不存在的 key）：参数校验 / 缓存空值 / 布隆过滤器 / IP 限流
- 击穿（热点 key 失效瞬间）：永不过期 / **互斥锁**（SETNX）
- 雪崩（大量 key 同时失效）：过期加随机 / 高可用 / 本地缓存 + 熔断
- 缓存一致性：**Cache Aside**（先写 DB 再删缓存）、**延迟双删**、**Canal 订阅 binlog** 异步更新

---

## 三、网络

### Q14. VPC 与子网设计

**主问**：客户要在 AWS 上搭一个电商系统，VPC 怎么设计？

**追问**：
- Public Subnet 和 Private Subnet 区别？
- NAT Gateway 和 Internet Gateway 区别？
- 一个 VPC 可以跨 Region 吗？
- 跨 VPC 通信有哪几种方式？
- 跨 Region VPC Peering 和同 Region 有什么硬差异？
- 混合云场景，IDC 到 VPC 的互联有哪几种选项？

**要点**：
- Public Subnet：有默认路由指向 IGW，EC2 可配公网 IP；Private Subnet：没有，通过 NAT 出网
- IGW：双向流量、提供公网 IP；NAT：只允许**出站**公网访问，本质是**多对一 SNAT 的出单行道**，公网没法直接访问 NAT 的 EIP 到内网 EC2
- Bastion Host：放在公有子网的入口跳板，用 Security Group 把 SSH 入站限到个人 IP；现在更推荐 **SSM Session Manager** 替代 Bastion
- VPC **不能跨 Region**，一个 VPC 在一个 Region；跨 Region 用 **VPC Peering** 或 **Transit Gateway**
- 跨 VPC：VPC Peering（点对点，不传递）、Transit Gateway（星型、传递）、PrivateLink（服务暴露）
- **跨 Region VPC Peering 的硬差异**：流量用 **AEAD 加密**走 AWS 骨干网；**不支持跨 Region 引用 Security Group、不支持 jumbo frame**，而同 Region Peering 支持
- 混合云三种方案：**Site-to-Site VPN**（托管 VGW+CGW，走 Internet 加密）、**自建 IPsec VPN**（EC2 装 strongSwan，可控但要自己运维）、**Direct Connect 专线**（最贵但延迟最低、带宽最稳）

### Q14a. AWS 数据传输费

**主问**：客户账单里"Data Transfer"占了很大一块，怎么向他拆解？

**追问**：
- 入 AWS 和出 AWS 的流量都收费吗？
- 同 AZ、跨 AZ、跨 Region 的 EC2 ↔ EC2 流量分别怎么收？
- VPC Peering 和 NAT Gateway 的费用模型有什么区别？
- Multi-AZ RDS 的主/standby 复制流量要钱吗？

**要点**：
- **入 AWS 零费**；出 AWS 按量收，不同 Region 价差很大（中国区 / 东南亚 / 欧美差异明显）
- 同 Region 走 **IGW** 到公网 service endpoint **零费**；走 **NAT Gateway** 要额外加 NAT 的 "data processing" 单价
- **同 AZ 零费**；**跨 AZ EC2 ↔ EC2 双向都收费**（这是常被忽略的大头）
- **VPC Peering**：同 AZ 零费、跨 AZ 按 ingress/egress 收
- **Multi-AZ RDS** 主/standby 的内部复制零费，但**客户端跨 AZ 访问 RDS 读写**要收
- 优化手段：VPC Endpoint（Gateway Endpoint for S3/DynamoDB 完全免费、Interface Endpoint 按小时 + 流量收）、同 AZ 部署、CloudFront 做出口（CloudFront → Internet 比 EC2 直出便宜）

**AWS 映射**：CUR + Cost Explorer（按 usage type 过滤）、VPC Flow Logs（定位跨 AZ 流量大户）、VPC Endpoint、CloudFront

### Q15. ALB vs NLB vs CloudFront

**主问**：ALB、NLB、CloudFront 分别适合什么场景？

**追问**：
- ALB 和 NLB 工作在哪一层？核心区别？
- CloudFront 和 ALB 一起用是什么架构？怎么防止客户端绕过 CloudFront 直连 ALB？
- NLB 的 Preserve Client IP 是干嘛的？ALB 呢？
- API Gateway 和 ALB 怎么选？
- ALB 一个 Listener 的路由规则有数量上限吗？
- ALB 怎么看慢请求和错误码？

**要点**：
- **ALB（L7）**：HTTP/HTTPS，支持基于 URL / Header 的路由、WebSocket、HTTP/2，适合 Web 应用
- **NLB（L4）**：TCP/UDP，**百万级并发**，静态 IP，低延迟，适合游戏/实时通信/非 HTTP 应用
- **CloudFront**：边缘缓存，就近接入，静态资源加速 + 动态加速，源可以是 ALB/S3/自定义
- 典型架构：Route 53 → CloudFront → ALB → EC2/ECS
- **防绕过 CloudFront**：CloudFront 分发配 **Origin Custom Header**（视作密码保密），ALB listener 加规则"命中 header 才 forward，否则 default → 404"；更严谨用 **CloudFront VPC Origin** 把 ALB 放到私有子网里，彻底不暴露公网；或订阅 SNS `AmazonIpSpaceChanged` 自动更新 ALB 入站白名单到 CloudFront 边缘 IP
- **真实客户端 IP 透传矩阵**：
  - NLB + Instance target：**直接透传真实 IP**，EC2 socket 层能拿到
  - NLB + IP target：**不透传**，需启用 **Proxy Protocol v2**（后端要能解析）
  - ALB + Instance / ALB + IP：**都不透传**，必须读 `X-Forwarded-For` 头
- `X-Forwarded-For` 规则：CloudFront 把真实 Client IP 放在**最前面**，中间 CDN/ELB 节点**追加**（不是替换）自己的 IP 到末尾——取第一个元素才是真实客户端
- API Gateway：Serverless + 内置限流/认证/API Key；ALB 适合容器化后端 + 自定义路由
- ALB **一个 Listener 最多 75 条规则**，每条规则最多 3 个通配符（* 或 ?），规则按**顺序**匹配（命中即止），细粒度规则放前面、兜底规则放后面
- 可观测：**ALB access log** 每 5 分钟/节点写一次 S3 gzip（默认关闭），路径 `AWSLogs/<account>/elasticloadbalancing/<region>/yyyy/mm/dd/...`；配合 **Athena** 直接查慢请求和错误码，S3 存储费 + 零 ELB 带宽费

### Q16. Route 53

**主问**：Route 53 有哪些路由策略？

**追问**：
- 简单路由 / 加权路由 / 延迟路由 / 地理路由 / 故障转移 分别什么场景？
- A 记录和 CNAME 区别？Route 53 的 Alias 和 CNAME 区别？
- Route 53 Resolver 是干嘛的？
- Health Check 怎么工作？

**要点**：
- Simple：单纯一个 IP
- Weighted：灰度发布、A/B 测试
- Latency：全球多 Region 部署，按延迟就近
- Geolocation：按用户地理位置返回不同内容（合规场景）
- Failover：主备切换，配 Health Check
- **Alias 记录**：Route 53 专有，可以指向 CloudFront/ALB/S3 等 AWS 资源，**根域名也能用**（CNAME 不能），**免费查询**
- Route 53 Resolver：VPC 内 DNS，可以转发到本地 IDC
- 迁 NS 到 Route 53：阿里云最多 13 个、腾讯云 6 个、GoDaddy 更新最长 48 小时生效；**中国区客户常问"NS 换到 Route 53 对备案有没有影响"**——备案看服务器所在 Region 和 ICP 牌照，不看 NS，所以 NS 可以放海外，但 CDN / Web 服务器国内还是要备案

### Q17. 浏览器输入 URL 到页面展示（SA 招牌题）

**主问**：浏览器输入 URL 到页面展示，中间发生了什么？用 AWS 服务讲一遍完整链路。

**追问**：
- DNS 递归和迭代查询区别？
- 建立 HTTPS 连接要几次 RTT？TLS 1.2 和 1.3 区别？
- 304 和 200 区别？
- 页面渲染中的回流和重绘？

**要点**（映射到 AWS 服务）：
1. **DNS 解析** → Route 53（权威 DNS），支持延迟/地理/健康检查路由
2. **就近接入** → CloudFront（边缘节点减少 RTT）
3. **TLS 握手** → ACM 签发证书，CloudFront 做 TLS termination；TLS 1.3 省一次 RTT
4. **L7 路由** → ALB（基于 URL/Header）或 API Gateway（Serverless API）
5. **应用层** → EC2 / ECS / EKS / Lambda
6. **缓存** → CloudFront（静态资源）+ ElastiCache（应用层）
7. **存储** → S3（对象）/ RDS / Aurora / DynamoDB

能把一个 URL 讲到完整 AWS 架构，是 SA 的基本功。

### Q18. HTTP/HTTPS/TCP 基础

**主问**：HTTP 2.0 相比 1.1 有什么核心改进？HTTPS 握手过程？

**追问**：
- 多路复用解决了什么问题？
- 对称加密和非对称加密分别用在哪一步？
- CloudFront 支持 HTTP/2 和 HTTP/3 吗？

**要点**：
- HTTP 2.0：**二进制分帧 + 多路复用 + 头部压缩（HPACK）+ Server Push**
- 多路复用：一个 TCP 连接并行多个请求，解决 HTTP 1.1 队头阻塞
- HTTPS：非对称加密**协商对称密钥** → 对称加密**传数据**
- TLS 1.3：1 RTT 握手（1.2 需要 2 RTT），支持 0-RTT 恢复
- CloudFront **支持 HTTP/2 和 HTTP/3**（2022 发布），TLS 1.3 默认开启
- CloudFront 有**两层缓存**：Edge Location + **Regional Edge Cache**（第二层，容量更大，Edge Miss 时先回源 Regional 再回源）；**PUT/POST/PATCH/OPTIONS/DELETE 和动态请求不走 Regional Edge Cache**，直接回源
- 容易被忽略的"回源暴涨"坑：**条件请求（If-Modified-Since / If-None-Match）在 CloudFront 配了 Cookie 转发时不生效**，304 回不来

### Q18a. Lambda@Edge 四类触发点

**主问**：客户要在边缘加一段"按设备返回不同图片 URL"的逻辑，用 CloudFront + Lambda@Edge 怎么做？四个触发点怎么选？

**追问**：
- Viewer Request / Origin Request / Origin Response / Viewer Response 分别在流程哪一步？
- 边缘动态缩略图（大图加工）应该挂在哪个触发点？为什么？
- 哪些触发点的响应有 1MB 大小限制？
- A/B 测试、反爬虫一般挂哪里？

**要点**：
- 四个触发点各自特性：
  - **Viewer Request**：每个请求都触发，**不缓存**；适合 A/B、鉴权、简单改写
  - **Origin Request**：**Cache Miss 时才触发**，响应最大 **1MB**，可直接返回不回源
  - **Origin Response**：源返回后、入缓存前触发，响应**无 1MB 限制**，适合**大图/视频加工、缩略图**
  - **Viewer Response**：响应给客户端前触发，**不缓存**；适合插头、改 header
- A/B 测试、反爬虫：**Viewer Request**（能看到所有流量）
- 按设备生成缩略图：**Origin Response**（可以大响应、能命中后续缓存）
- 比 CloudFront Functions 重：Lambda@Edge 冷启动稍长、能跑完整 Node.js/Python；CloudFront Functions 极轻量、只做 Viewer 层字符串处理

**AWS 映射**：CloudFront、Lambda@Edge、CloudFront Functions

---

## 四、安全

### Q19. IAM 策略评估

**主问**：IAM 策略怎么评估？多个策略冲突时谁优先？

**追问**：
- Identity-based 和 Resource-based policy 的区别？
- SCP、Permission Boundary、Session Policy 分别是什么？
- 显式 Deny 和显式 Allow 的优先级？
- `AssumeRole` 跨账号怎么做？

**要点**：
- 评估逻辑：**显式 Deny > 显式 Allow > 隐式 Deny（默认拒绝）**
- Identity-based：绑在 User / Group / Role 上
- Resource-based：绑在资源上（S3 Bucket Policy、SQS、Lambda Resource Policy），**可以给跨账号授权**
- **SCP**（Service Control Policy）：Organizations 层面的"天花板"，限制账号最大权限
- **Permission Boundary**：限制 IAM 实体的最大权限，不授予权限
- 跨账号 AssumeRole：目标账号创建 Role 允许源账号 AssumeRole，源账号用户带 `sts:AssumeRole` 权限

### Q20. KMS 与数据加密

**主问**：数据加密 at rest 和 in transit 有什么区别？KMS 怎么工作？

**追问**：
- CMK（Customer Managed Key）和 AWS Managed Key 区别？
- 对称密钥和非对称密钥分别什么场景？
- 什么是**信封加密**（Envelope Encryption）？为什么要用？
- KMS Key Rotation 怎么做？

**要点**：
- At Rest：数据存储时加密（S3 SSE、EBS、RDS）；In Transit：传输时加密（TLS）
- Customer Managed Key：**客户自己管理 Key 生命周期**，可以定义 Key Policy；AWS Managed Key：AWS 代管，不能自定义策略
- 对称：加解密同一密钥（AES-256），性能好，**绝大多数场景**
- 非对称：公钥加密 / 私钥解密（或签名），用于**跨组织**的加密 / 签名场景
- **信封加密**：用 Data Key 加密数据，用 KMS CMK 加密 Data Key；避免大数据量都走 KMS API（KMS 有限流）
- 自动轮换：CMK 每年自动轮换，老版本保留用于解密旧数据

### Q20a. Nitro Enclave 可信执行环境

**主问**：客户做金融 KYC，要求"密钥永远不出可信环境、父实例的 root 也不能看"，只有 KMS 还不够，怎么做？

**追问**：
- Nitro Enclave 和 Intel SGX / ARM TrustZone 有什么本质差异？
- Enclave 怎么和外部通信？能装 agent 吗？
- 怎么保证攻击者不能"换一个 Enclave 偷密钥"？

**要点**：
- Nitro Enclave = EC2 内部 **CPU + 内存隔离的子 VM**，父实例 root 都访问不到
- **无持久存储、无网络、无交互 shell**，和父实例只能通过 **vsock** 通信
- 典型用途：**私钥处理**（签名、解密）、**PII 令牌化**
- 对比：**不绑定 CPU 厂商**（SGX 要 Intel、TrustZone 要 ARM）、不额外收费、按 EC2 CPU/内存从父实例切片划
- **Attestation 证明文件**里有 Enclave 镜像的 PCR 哈希，外部服务（KMS、Vault）可按 PCR 建访问策略：**只有这个 Enclave 镜像能解密**；换镜像 PCR 就变，KMS 拒绝授权

**AWS 映射**：EC2 Nitro Enclave、KMS（Attestation 条件 Key Policy）、Secrets Manager

### Q21. Security Group vs NACL

**主问**：Security Group 和 Network ACL 区别？

**追问**：
- 分别作用在什么层级？
- Stateful 和 Stateless 的差异体现在哪？
- 一个 EC2 可以绑几个 Security Group？
- 用什么规则表示"允许 10.0.0.0/8 访问 80 端口，但禁止 10.0.1.5"？

**要点**：
- **Security Group**（**实例级**）：Stateful，只写入站规则出站自动放行；只能配 **允许**，默认 Deny
- **NACL**（**子网级**）：Stateless，入站和出站都要配；可以配**允许**和**拒绝**
- 一个 EC2 可以绑多个 Security Group（取并集），默认 5 个，最多 16 个
- 复杂场景（允许整个段但禁止某个 IP）**必须用 NACL**，Security Group 做不到 Deny

### Q22. WAF 与 Shield

**主问**：客户担心 DDoS 攻击，你会推什么方案？

**追问**：
- Shield Standard 和 Advanced 区别？
- WAF 能防什么攻击？
- Managed Rule 和 Custom Rule 怎么用？
- Rate-based Rule 是干嘛的？

**要点**：
- **Shield Standard**：**所有 AWS 客户免费**，防 L3/L4 常见 DDoS
- **Shield Advanced**：$3000/月，防 L7 攻击、提供 24/7 DRT 响应团队、费用保护（DDoS 导致的 ELB/CloudFront 账单 AWS 承担）
- WAF 工作在 L7（HTTP）：防 SQL 注入、XSS、路径穿越、Bad Bot
- Managed Rule：AWS 和第三方维护的规则组（OWASP Top 10、常见 CVE），拿来即用
- Rate-based Rule：**单 IP 一定时间内超过 N 次请求就拦截**，防爬虫和 CC 攻击
- 客户视角的实战顺位（cc 攻击、无特征海量请求）：**备份静态站点兜底 → iptables / nginx deny 特征流量 → 带宽扩容（多镜像 + DNS 负载）→ CDN + WAF**；关键坑：**上 CDN 后源站 IP 一定要藏好**，泄漏源 IP 攻击者直接绕 CDN 打
- WAF 日志**运营化**：WAF 日志入 OpenSearch 两条路——**直落 S3**（便宜，5 分钟或 75MB 滚一次延迟）或 **Kinesis Firehose**（实时但贵）；可参考 **Log Hub** 方案把 S3 Put → SQS → Lambda(LogProcessor) → OpenSearch 全部自动化

### Q22a. 云上安全的服务拼图

**主问**：客户只听过 WAF、Shield、GuardDuty，分不清一堆带 "Security/Protection" 的服务，你怎么给他一张图？

**追问**：
- 客户在云上的核心安全责任分几块？
- 这些服务之间的数据怎么流？谁是"统一视图"？

**要点**：
- 客户 5 大安全责任：**IAM / 基础设施保护 / 数据保护 / 安全检测 / 事件响应**
- 对应的 AWS 服务拼图：
  - **Security Hub**：统一视图，聚合其他服务的 findings，按 CIS/PCI/AWS Foundational 评分
  - **GuardDuty**：威胁检测，吃 **CloudTrail、VPC Flow Logs、DNS 日志**（可选 EKS Audit、S3、Lambda、RDS Protection）
  - **Config**：配置合规，Rule 持续评估资源 drift
  - **Macie**：S3 敏感数据扫描（PII、密钥）
  - **Inspector**：EC2/ECR/Lambda 漏洞扫描
  - **Detective**：事件调查，把 GuardDuty finding 展开成图形化 timeline
  - **IAM Access Analyzer**：发现资源级的意外公开和跨账号访问
- 关键依赖：GuardDuty 必须先开 CloudTrail、VPC Flow Logs；Security Hub 要先 enable 对应标准

**AWS 映射**：Security Hub、GuardDuty、Config、Macie、Inspector、Detective、IAM Access Analyzer、CloudTrail、VPC Flow Logs

### Q23. 合规

**主问**：客户问我们在 AWS 上能做到哪些合规认证？

**追问**：
- AWS 的责任共担模型是什么？
- 中国区的等保 2.0 和海外的合规有什么不同？
- 数据主权（Data Sovereignty）是什么？客户数据会不会出境？

**要点**：
- **责任共担模型**：**AWS 负责 "Security OF the cloud"**（基础设施、物理、虚拟化层），**客户负责 "Security IN the cloud"**（数据、应用、IAM、加密）
- AWS 全球有：ISO 27001/27017/27018、SOC 1/2/3、PCI DSS、HIPAA、GDPR 合规能力
- **ISO 22301:2019（业务连续性 BCMS）**：由第三方（EY CertifyPoint）审计，客户问"AWS 真断电断网了怎么办"时的直接凭据
- 中国区（宁夏 + 北京）：等保 2.0 三级（AWS 底座做了二级+，客户应用层自己做到三级）
- 数据主权：中国区由光环新网（北京）和西云数据（宁夏）运营，**数据和账单都在国内**；海外 Region 可选
- 中国区 S3 vs 国际 S3 的 4 个坑：
  1. **URL 必须带 Region**（`{bucket}.s3.cn-north-1.amazonaws.com.cn`，不能用无 Region 短 URL）
  2. **签名必须用 SigV4 / SHA256**（国际还兼容 SHA1）
  3. **公网 80/443 对象访问需要备案**（SDK/CLI 不受影响）
  4. **Bucket 命名空间与国际完全独立**，可以重名，但 `aws s3 sync` **不能直接跨区同步**，要走 DataSync / S3 Replication（且中国 ↔ 海外要走申请流程）
- 中国区常见"缺失"：**Amplify 只有前端库可用**，后端部分（Cognito 托管自动化部署）缺失，替代方案是 Serverless Framework 自己拼 AppSync + DynamoDB + Lambda；**CloudFront 中国区不能用 ACM**，证书必须自己买第三方上传

---

## 五、应用集成与分布式架构

### Q24. MSK / SQS / Kinesis 选型

**主问**：MSK、SQS、Kinesis 都是消息相关，怎么选？

**追问**：
- SQS Standard 和 FIFO 区别？
- Kinesis Data Streams 和 Firehose 区别？
- 每秒 10 万条消息、保留 7 天、多个消费组各自独立消费，选哪个？

**要点**：
- **MSK**：高吞吐 + Kafka 生态 + 需要有序 + 保留时间长 + **多消费组回放**
- **SQS**：简单队列 + 解耦 + 无运维；Standard **吞吐无限**但可能乱序和重复；FIFO 保证顺序但 **300 TPS/API**
- **Kinesis Data Streams**：流式分析 + 多消费者 fan-out + 实时性要求高
- **Kinesis Firehose**：**无代码落地**到 S3/Redshift/OpenSearch

### Q25. Kafka 消息丢失

**主问**：Kafka 可能在哪些环节丢消息？分别怎么防？

**追问**：
- Producer 的 `acks=0/1/all` 分别什么语义？
- Consumer 自动提交 offset 为什么会丢消息？
- `min.insync.replicas` 和 `acks=all` 怎么配合？

**要点**：
- 三个环节：**Producer → Broker → Consumer**
- Producer：异步 send 不管结果 → 回调 or 同步 get() + 重试
- Consumer：自动提交 offset 可能"已提交但没真消费完就挂" → **手动提交**
- Broker：Leader 挂了 Follower 没同步 → `acks=all` + `replication.factor ≥ 3` + `min.insync.replicas ≥ 2`

**AWS 映射**：MSK 支持所有原生 Kafka 配置；MSK Serverless 自动管理副本和分区数。

### Q26. 分布式事务选型

**主问**：订单成功要同时扣钱 + 加积分，三个服务三个库，用什么方案？

**追问**：
- 基于消息和 TCC 本质区别？
- TCC 为什么业务侵入性大？
- SAGA 适合什么场景？
- 2PC 为什么互联网很少用？

**要点**：
- 选型顺序：**单机 > 消息 > 补偿 > TCC > SAGA > 2PC**（优先选简单）
- **消息**：发起方说了算、跟随方异步（订单 → 加积分）
- **TCC**：Try 冻结资源 → Confirm / Cancel，适合"中间态不能被用户看到"
- **SAGA**：长事务异步补偿，不保证中间态隔离

**AWS 映射**：
- **Step Functions** 实现 Saga 是经典模式：每步 Lambda，失败触发 Cancel 分支
- DynamoDB Transactions 单 Region 跨表 ACID
- SQS + DLQ 做消息最终一致性

### Q26a. ACM 证书与 TLS 卸载

**主问**：客户要在 ALB / CloudFront / API Gateway 上统一做 HTTPS，证书怎么管？

**追问**：
- ACM 公有证书免费吗？能自动续期吗？
- ACM 证书绑到 ALB、CloudFront 分别有什么 Region 要求？
- 中国区 CloudFront 可以用 ACM 吗？
- 根域名 `example.com` 怎么指到 CloudFront？

**要点**：
- ACM 公有证书：**免费、自动续期**（前提 DNS 验证通过且域名 Alias 在 AWS 资源上）
- 绑定 Region 规则：
  - **ALB / API Gateway**：要用**同 Region** 的 ACM 证书
  - **CloudFront**：**必须用 us-east-1 (N. Virginia)** 签发的证书
  - 中国区 **CloudFront 不能用 ACM**，必须自己买第三方证书上传到 **IAM**；Route 53 Alias **不能跨区**
- 根域名指 CloudFront / ALB / S3：用 **Route 53 Alias 记录**（CNAME 顶级域名不允许）

**AWS 映射**：ACM、Route 53 Alias、CloudFront、ALB、API Gateway、IAM（上传第三方证书）

### Q26b. EKS 网络与 Pod 隔离

**主问**：客户用 EKS 跑微服务，想做"Pod 级"的网络隔离，不只是 Security Group，怎么做？

**追问**：
- EKS 默认 CNI 和 overlay 网络（Calico IPIP、Flannel）有什么本质差异？
- EKS 一个节点能跑多少 Pod？被什么限制？
- NetworkPolicy 在 EKS 的现状？Fargate 支持吗？
- 想要"Pod 到 RDS/S3 的细粒度放行"用什么？

**要点**：
- EKS 默认 CNI (`amazon-vpc-cni-k8s`) 给每个 Pod 一个**真实 VPC IP**（多 ENI + 二级 IP），**零 overlay**，路由就是 VPC 路由
- **代价**：每节点 Pod 数被 **ENI 数 × 每 ENI 二级 IP 数**封顶，小实例（如 c1.medium）只能跑 10 个 Pod；大实例要配 **Prefix Delegation** 提升密度
- NetworkPolicy：EKS 原生支持（VPC CNI 1.21+），也可用 **Calico 以 daemonset 形式**只跑 NetworkPolicy 不负责 IP 分配
- 限制：**Fargate 和 Windows 节点不支持 NetworkPolicy**；一个策略只能针对 **IPv4 或 IPv6**，不能同时
- Pod 到 AWS 服务（RDS、ElastiCache 等）细粒度隔离：**Security Group for Pod**，每个 Pod 可挂独立 SG

**AWS 映射**：EKS、VPC CNI、Security Group for Pod、Calico、NetworkPolicy

---

## 六、GenAI

### Q27. Bedrock vs SageMaker

**主问**：客户想做一个大模型应用，选 Bedrock 还是 SageMaker？

**追问**：
- Bedrock 的核心定位是什么？
- SageMaker 适合哪些 GenAI 场景？
- 如果客户要微调一个开源模型，用哪个？
- Bedrock Custom Model 和 SageMaker JumpStart 区别？

**要点**：
- **Bedrock**：**Serverless 的 Foundation Model API**，不管底层算力，按 token 计费；主流 FM 都有（Claude、Nova、Llama、Mistral、Titan 等）
- **SageMaker**：端到端 ML 平台，从训练到部署全栈，适合**自己训模型 / 深度微调 / 需要 GPU 实例控制**
- 微调开源模型：
  - 轻量 LoRA → **Bedrock Custom Model**（托管）
  - 全参数微调 / 大规模数据 → **SageMaker Training Job**
- SageMaker JumpStart：预训练模型市场，可以一键部署开源模型到自己账号的 Endpoint
- 深度自训工程要点：SageMaker 训练任务可以把 **FSx for Lustre** 挂进训练容器（代替 S3），FSx 支持从 S3 导入/导出，训练任务复用避免重复下载 TB 级数据集；自定义 GPU 训练镜像要装 **`sagemaker-training` 包**才能响应 SageMaker 的 training 入口

### Q28. Foundation Model 选型

**主问**：客户在 Bedrock 上有一堆模型选，Claude、Nova、Llama、Titan 怎么选？

**追问**：
- 怎么评估模型效果？benchmark 可信吗？
- 延迟敏感和成本敏感场景分别怎么选？
- 多模态（图像 / 视频 / 语音）场景？
- 中文场景有什么特别考虑？

**要点**：
- 评估方法：**自己的业务数据集跑一轮**，公开 benchmark 只做初筛
- 延迟敏感：Claude Haiku / Nova Micro（小模型）
- 质量优先：Claude Opus / Claude Sonnet 4
- 成本敏感：Nova（AWS 自研，便宜）、Llama（开源，可以自托管）
- 多模态：Claude（图像）、Nova（图像 + 视频）、Stable Diffusion（图像生成）
- 中文：Claude 中文能力强；国内客户可以考虑 Bedrock 中国区支持的模型（受地域限制）

### Q29. RAG 架构

**主问**：客户要做一个企业知识问答，RAG 架构怎么设计？

**追问**：
- RAG 的核心流程？
- 向量数据库怎么选？OpenSearch、Aurora pgvector、Kendra？
- Chunking 策略对效果影响大吗？
- 怎么评估 RAG 的效果？
- Bedrock Knowledge Base 怎么用？

**要点**：
- RAG 流程：文档切片（Chunking）→ Embedding → 存向量库 → 用户问题 Embedding → 向量检索 Top K → 拼 Prompt → LLM 生成
- 向量库选型：
  - **Bedrock Knowledge Base**：托管一站式，适合不想自建的客户
  - **OpenSearch Serverless**：灵活 + 可控 + 高性能
  - **Aurora PostgreSQL + pgvector**：已经用 Aurora 的客户、数据量不太大
  - **Kendra**：更接近企业搜索，但贵
- Chunking：固定长度 vs 语义切片，重叠（overlap）防止上下文丢失
- 评估：**Faithfulness**（忠实度）+ **Relevance**（相关性）+ **Context Precision**（上下文精度），工具用 RAGAS

### Q30. Agent 与 Tool Use

**主问**：Agent 和 RAG 有什么区别？Bedrock Agent 能做什么？

**追问**：
- Agent 的工作原理？
- 怎么保证 Agent 调用工具不出错？
- 多步 Agent 的失败重试怎么做？
- Agent 的成本控制？

**要点**：
- RAG = 知识检索 + 生成；Agent = **规划 + 工具调用 + 多步推理**
- Bedrock Agent：定义 Action Group（API 调用）+ Knowledge Base，LLM 自主决定调用哪个
- 工具调用准确率：**Function Calling 模式** + 清晰的 Tool Schema 描述 + Few-shot 示例
- 多步失败：Step Functions 做编排 + 幂等 + 补偿；或在 Agent 层加 retry policy
- 成本：**每一步都是一次 LLM 调用**，多步 Agent 可能很贵；建议**先做 PoC 看成本模型再决定上生产**

### Q31. 多租户 GenAI 架构

**主问**：客户要给他的 SaaS 产品加 AI 功能，多租户怎么设计？

**追问**：
- 不同租户的数据怎么隔离？
- 不同租户的用量怎么限制？
- 账单怎么分摊到租户？
- 不同租户要用不同模型怎么办？

**要点**：
- 数据隔离：
  - 向量库：**按 tenant_id 做 metadata filter**（Pool 模式）或**每租户一个 index**（Silo 模式）
  - Prompt：每次调用带 tenant context，防止跨租户污染
- 用量限制：
  - 应用层：**API Gateway Usage Plan** + Lambda 内做 rate limit
  - Bedrock 层：**Application Inference Profile**（每租户一个 profile，分开限流和计费）
- 账单分摊：**Application Inference Profile + Cost Allocation Tags**，每个 tenant 独立 tag
- 多模型：Bedrock 支持运行时切换 modelId；Cross-Region Inference 可提升可用性

### Q32. Guardrails 与安全

**主问**：客户担心大模型会"胡说八道"或泄露敏感信息，怎么防？

**追问**：
- Bedrock Guardrails 能防什么？
- 怎么防 Prompt Injection？
- 怎么保证模型不输出 PII（个人隐私）？
- 怎么评估模型"幻觉"程度？

**要点**：
- **Bedrock Guardrails** 四大能力：
  1. **Content Filter**：拦截暴力、仇恨、性相关内容
  2. **Denied Topics**：客户自定义禁止话题（"不许聊竞品"）
  3. **PII Redaction**：自动检测并打码 PII（手机号、邮箱、身份证）
  4. **Contextual Grounding**：**检查生成内容是否基于提供的上下文**，防幻觉
- Prompt Injection 防护：
  - System Prompt 和 User Prompt 分离
  - 对用户输入做 **Sanitization**
  - 用小模型做**意图识别**，可疑请求拦截
- PII：Guardrails + 应用层 Macie 扫描日志
- 幻觉评估：**离线用 RAGAS**，**在线用 Guardrails Contextual Grounding**

### Q33. GenAI 成本控制

**主问**：客户上了 Bedrock 后账单爆了，怎么优化？

**追问**：
- Bedrock 的计费模型？On-Demand 和 Provisioned Throughput 区别？
- Prompt Caching 是什么？能省多少？
- 怎么监控哪个租户 / 哪个场景烧钱最多？
- Batch Inference 什么场景用？

**要点**：
- 按 **input token + output token** 计费，不同模型价格差 10 倍以上
- **On-Demand**：按量计费，灵活但有并发限制
- **Provisioned Throughput**：买独立容量，适合稳定高并发，有 1 个月或 6 个月承诺
- **Prompt Caching**（2024 推出）：**重复的 System Prompt / Context 可缓存**，命中后 input token 价格降 90%
- 监控：**CloudWatch** 看 token 消耗 + **Cost Allocation Tags**（配合 Inference Profile）分租户
- **Batch Inference**：**离线场景**（历史数据分析、文档批量总结），**价格打 5 折**，但有延迟

---

## 七、架构白板题

> 必问一道，候选人在白板画 + 讲思路，面试官抛挑战。

### 题 1：高并发秒杀系统
10 万 QPS，库存 1000 件，不超卖、响应 < 500ms、5 分钟未支付自动释放库存。

**观察点**：接入层限流（CloudFront + WAF Rate-based）、库存预扣（Redis Lua 原子操作）、异步下单（SQS）、延迟释放（Step Functions 或 SQS 延迟队列）、幂等防重

### 题 2：出海直播平台
用户在东南亚和中东，源站国内。延迟 < 3 秒、日 PV 1 亿、带宽 500 Gbps、合规。

**观察点**：
- 推流：源站 MediaLive 就近接入
- 分发：CloudFront 全球边缘
- 转码：MediaConvert
- 合规：数据主权、本地化 Region 部署
- 成本：CloudFront 不同区域价差大

### 题 3：企业 RAG 知识问答
客户要给内部员工做知识问答，文档 10 万份，用户 1 万，要支持权限控制（HR 不能看财务文档）。

**观察点**：
- 向量库选型（Bedrock KB vs OpenSearch vs pgvector）
- 权限控制：**向量 metadata filter + 调用时带用户角色**
- Chunking 策略
- Guardrails 防止泄露敏感
- 用量和成本控制
- Fallback：模型答不出时怎么办

### 题 4：SaaS 多租户后台
数据隔离方案？大小客户资源怎么分？支持自定义域名和 HTTPS？

**观察点**：
- Silo（独立资源）vs Pool（共享）vs Bridge（混合）
- 大客户 Silo（独立 RDS + 独立 Cluster），小客户 Pool（共享 Aurora Serverless + 行级隔离）
- 自定义域名：Route 53 + ACM + CloudFront SNI
- 租户隔离：ABAC（IAM 策略 + 租户 tag）

### 挑战清单（必抛至少 2 个）
- 客户预算砍一半，你砍什么？
- 整个 Region 挂了会怎样？
- 客户架构师说这个方案过度设计
- 3 年后扩 10 倍还撑得住吗？

---

## 八、软技能与异议处理

### 场景 1：客户 DBA 不信任 Aurora
> "团队都是 MySQL DBA，Aurora 出问题排不了，还是用自建 MySQL on EC2。"

**好的回答**：
- 先共情（"您担心的是 troubleshooting 的能力建设对吗"）
- 客户视角价值：Aurora 95% 兼容 MySQL、运维 90% 托管、Support 兜底、长期 TCO 更低
- 折中方案：先用 Aurora 跑非核心业务，建立信心后再迁核心

**不好的回答**：
- "Aurora 比 MySQL 强多了"（技术优越感）
- "那好吧用自建"（直接认输）

### 场景 2：客户只想用 CDN 不想上云
> "我们只是想用 CloudFront 加速，不想迁其他服务。"

**好的回答**：
- 尊重客户边界，先把 CloudFront 做好
- 自然引入：日志分析用 Athena、WAF 防护加 AWS WAF、证书用 ACM 免费签发
- 不强推全栈，让客户在使用中自然发现其他服务的价值

### 场景 3：方案被挑战过度设计
> "你这个方案太复杂了，一台 EC2 + RDS 就够了。"

**好的回答**：
- 问背后担忧（预算？运维能力？业务规模？）
- 分层方案：核心必需（高可用）vs 加分项（自动扩缩）vs 未来再加（跨 Region 容灾）
- 给"精简版"和"完整版"两套，让客户选

### 场景 4：销售 Over Promise
> 销售给客户承诺了技术上做不到的 feature，客户按合同节点验收，怎么办？

**观察点**：
- 不甩锅销售 → 稳住客户 → 内部对齐 → 替代方案
- 事后机制避免再发生（SOW 评审流程）

### 场景 5：POC 失败
> 带团队做 POC，关键演示 demo 挂了，当着客户 CTO 的面。

**观察点**：
- 当场怎么救（Plan B？讲故事转移焦点？）
- 事后怎么复盘、挽回客户信任

### 场景 6：客户坚持错误技术选型
> 客户坚持用一个你认为不合理的技术栈（如用 MongoDB 存事务数据），怎么处理？

**观察点**：
- 理解客户为什么坚持（惯性？团队能力？KPI 绑定？）
- "小规模试点"或"数据驱动"让客户自己改主意
- 客户还是不改能接受吗？

---

## 用法说明

- **按候选人简历挑题**，不用全问。1 小时建议：4~6 道原理题 + 1 道白板 + 1~2 个软技能场景
- **每题 AWS 映射部分是加分内容**，候选人能从原理讲到 AWS 服务是 SA 核心素养
- **GenAI 栏目**适合考察这块经验的候选人，没经验的别硬问
- **架构白板必问 1 道**，是 SA 面试最重要的信号来源
