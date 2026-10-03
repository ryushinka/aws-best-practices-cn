# SA / 售前 面试题集（AWS 相关）

> 问题按主题分类，每题包含：**主问 → 追问 → 要点 → AWS 映射**。
> 挑和候选人简历相关的问，不用全问。看重 **广度 + 选型思维 + 能把原理翻译到 AWS 服务**。

---

## 目录

1. [缓存与 Redis](#一缓存与-redis)
2. [MySQL 与关系型数据库](#二mysql-与关系型数据库)
3. [消息队列](#三消息队列)
4. [分布式事务](#四分布式事务)
5. [网络基础](#五网络基础)
6. [Web 请求链路](#六web-请求链路)
7. [存储与 IO](#七存储与-io)
8. [运维与故障](#八运维与故障)
9. [架构白板题](#九架构白板题)
10. [异议处理](#十异议处理)

---

## 一、缓存与 Redis

### Q1. 缓存三连：穿透 / 击穿 / 雪崩

**主问**：讲一下缓存穿透、击穿、雪崩的区别，分别怎么处理？

**追问**：
- 布隆过滤器怎么工作？缺点？
- 热点 key 失效瞬间除了"永不过期"还有什么办法？
- 如果 Redis 集群整个挂了怎么办？

**要点**：
- **穿透**：查一个 DB 和 Cache 都没有的 key（如 id=-1）。方案：参数校验 / 缓存空值 / 布隆过滤器 / 单 IP 限流
- **击穿**：热点 key 失效瞬间大量请求打到 DB。方案：热点 key 不过期 / **互斥锁**（第一个查 DB 回填，其他等待）
- **雪崩**：大量 key 同时失效 or Redis 挂了。方案：过期时间加随机值 / 高可用集群 / 持久化恢复 / 本地缓存 + 限流降级
- 布隆过滤器**存在误判**（说有可能真没有）、不支持删除

**AWS 映射**：
- ElastiCache for Redis 多 AZ + 自动故障转移够不够防雪崩？
- 预热 key / 过期打散策略在 Serverless 架构（Lambda + ElastiCache）里怎么做？

---

### Q2. Redis 持久化：RDB vs AOF

**主问**：RDB 和 AOF 怎么选？

**追问**：
- AOF 的 `always / everysec / no` 三种 fsync 策略分别什么风险？
- AOF 文件会越来越大怎么办？
- 如果主库挂了，从库数据有延迟，怎么办？

**要点**：
- RDB：快照，恢复快但可能丢数据；AOF：追加写，更安全但恢复慢
- `always` 每条 fsync 最安全但慢；`everysec` 默认平衡（最多丢 1 秒）；`no` 交给 OS 调度
- AOF 重写：fork 子进程重新生成最小化 AOF
- 生产常用：**RDB + AOF 一起开**，RDB 做快速恢复，AOF 兜底

**AWS 映射**：
- ElastiCache for Redis 的 backup 实际是 RDB 快照，存到 S3
- AOF 在 ElastiCache 里默认关闭（6.0 之后用 Multi-AZ 替代 AOF）
- MemoryDB for Redis 是**持久化的 Redis**，用 multi-AZ transaction log 代替 AOF，是真正做主数据库用的

---

### Q3. Redis 主从复制

**主问**：Redis 主从同步的完整过程？什么情况会触发全量同步？

**追问**：
- 全量同步时主库会阻塞吗？
- 从库连不上主库恢复后，怎么判断走增量还是全量？
- 哨兵（Sentinel）和 Cluster 的区别？

**要点**：
- 首次同步：master `bgsave` 生成 RDB → 发给 slave → slave 清空旧数据加载 RDB → master 把 RDB 期间的写命令发送给 slave
- 增量同步：master 维护 **replication backlog**（环形缓冲区），slave 带 offset 重连，offset 还在 backlog 内就走增量，否则全量
- `bgsave` fork 子进程，主进程不阻塞；但 RDB 过大会导致网络传输和 slave 加载期间卡顿
- 哨兵：主从切换，不分片；Cluster：16384 槽位分片 + 高可用

**AWS 映射**：
- ElastiCache for Redis 的 Multi-AZ 本质就是主从 + 自动故障转移（底层也是 Redis replication）
- Read Replica 用于读扩展，但有**毫秒级**延迟，不能做强一致读
- 从 ElastiCache 迁移到 MemoryDB：MemoryDB 用 transaction log 保证主从强一致，可做主数据库

---

### Q4. ElastiCache 选型与配置

**主问**：客户要上 Redis 做缓存，你会推荐 ElastiCache for Redis 还是自己在 EC2 上搭？决策依据？

**追问**：
- Cluster Mode Enabled vs Disabled 怎么选？
- `maxmemory-policy` 几种策略分别是什么？`allkeys-lru` 和 `volatile-lru` 区别？
- 单节点规格扩多大合适？什么时候该切 Cluster Mode？

**要点**：
- 自建优势：成本可控、版本自主、支持 Redis Module；劣势：运维成本高、Failover 需要自己做
- ElastiCache 优势：Multi-AZ、备份、监控、补丁、无需运维
- `maxmemory-policy`：`allkeys-lru`（任何 key 都可能被淘汰）、`volatile-lru`（只淘汰设过 TTL 的 key）、`allkeys-lfu`（按访问频率）、`noeviction`（写失败）
- 单节点上限：Redis 单实例内存超 50GB 后 `bgsave` fork 会很慢，建议切 Cluster Mode

---

## 二、MySQL 与关系型数据库

### Q5. 索引结构与原理

**主问**：MySQL 为什么用 B+ 树做索引？不用 B 树、哈希表、二叉树？

**追问**：
- 聚簇索引和二级索引的区别？什么是"回表"？
- 覆盖索引是什么？能解决什么问题？
- 联合索引 `(a, b, c)`，`where a=1 and b>10 and c=2` 哪些字段走索引？

**要点**：
- B 树节点都存数据 → 树高高、磁盘 IO 多；哈希不支持范围查询；二叉树可能退化
- B+ 树：非叶子只存索引、叶子存全部数据、叶子间有指针（范围查询友好）
- 聚簇索引叶子存整行数据；二级索引叶子存主键值 → 需要**回表**
- 覆盖索引：查询字段都在索引里，不用回表
- 范围查询之后的字段**不走**索引（上例 c 不走）

**AWS 映射**：
- RDS MySQL / Aurora MySQL 的索引实现一致
- Aurora 做了存储和计算分离，索引数据存在底层分布式存储，但 B+ 树逻辑不变
- Performance Insights 可以直接看到哪些慢查询在扫全表 / 没走索引

---

### Q6. 事务与隔离级别

**主问**：四种隔离级别分别是什么？解决了什么问题？

**追问**：
- 脏读、不可重复读、幻读分别举例
- MySQL 默认 RR，为什么大部分互联网公司改成 RC？
- RR 下 InnoDB 怎么防幻读？

**要点**：
- 读未提交 / 读已提交 / 可重复读 / 串行化
- RR 下用 **MVCC + Next-Key Lock（行锁 + 间隙锁）** 解决幻读
- RC 性能更好、锁范围小、不会 gap lock 死锁，适合高并发互联网场景
- MySQL 默认 RR 是因为早期主从复制 statement 格式必须 RR 才一致

**AWS 映射**：
- RDS / Aurora 默认都是 RR
- Aurora 的只读副本有**毫秒级**延迟，强一致读要走主库
- Aurora Global Database 跨 Region 读副本延迟通常 < 1 秒

---

### Q7. 分库分表

**主问**：客户日订单 100 万，MySQL 单库快撑不住了，你会推分库分表、读写分离，还是 Aurora？决策逻辑？

**追问**：
- 分库和分表有什么区别？什么时候分库、什么时候分表？
- 水平拆分和垂直拆分的区别？按 range 还是 hash 分片？各自优缺点？
- 分库分表后 ID 怎么生成？
- 已有系统上分库分表，怎么平滑迁移？

**要点**：
- 选型顺序：**读写分离 → 加缓存 → 分表 → 分库 → 分库分表**（能不拆就不拆）
- 单表经验值：超过 500 万~1000 万行性能明显下降，考虑分表
- 单库经验值：QPS 超过 2000 需要考虑分库
- Range 分片：扩容方便、但有**写入热点**（新数据集中）
- Hash 分片：分布均匀、但扩容需要数据迁移
- ID：雪花算法 / UUID / 号段模式（Leaf）

**AWS 映射**：
- **很多场景可以用 Aurora 代替分库分表**：Aurora 单库最大 128TB、15 个只读副本、自动扩展存储
- 真需要分片：Aurora Limitless Database（新）、Aurora + ShardingSphere、或 DynamoDB（NoSQL 原生分片）
- 迁移推荐：DMS（Database Migration Service）做在线迁移，支持双写阶段

---

### Q8. Aurora vs RDS MySQL

**主问**：Aurora 和自建 MySQL 主从相比，核心差异是什么？

**追问**：
- Aurora 为什么能做到 15 个只读副本几乎无延迟？
- Aurora 的"存储层共享"是什么意思？数据丢失风险怎么样？
- 什么场景下不该用 Aurora，还是用 RDS MySQL？

**要点**：
- **存储和计算分离**：底层是分布式存储（6 副本跨 3 AZ），所有实例共享同一份数据
- 主库只负责"写 redo log 到存储层"，不负责数据刷盘；只读副本直接从存储层读
- 只读副本和主库延迟通常 < 20ms（因为不走传统主从复制）
- 存储层自动修复：丢失任意 2 副本不影响写，丢失任意 3 副本不影响读
- 不该用 Aurora：对 MySQL 版本有特殊要求、依赖特殊插件、单纯小规模（RDS 更便宜）

---

## 三、消息队列

### Q9. Kafka 消息丢失

**主问**：Kafka 可能在哪些环节丢消息？分别怎么防？

**追问**：
- Producer 的 `acks=0/1/all` 分别什么语义？
- Consumer 自动提交 offset 为什么会丢消息？
- `min.insync.replicas` 和 `acks=all` 怎么配合？

**要点**：
- 三个环节：**Producer → Broker → Consumer**
- Producer：异步 send 不管结果 → **回调** or **同步 get()** + **重试**
- Consumer：自动提交 offset 可能"已提交但没真消费完就挂" → **手动提交**（至少一次语义）
- Broker：Leader 挂了 Follower 没同步 → `acks=all` + `replication.factor ≥ 3` + `min.insync.replicas ≥ 2`

**AWS 映射**：
- MSK（托管 Kafka）：参数一样，但 broker 和 ZooKeeper 由 AWS 托管
- MSK Serverless：无需配置 broker 数量，但 `acks / replication.factor` 等还是开发者控制
- 替代方案：SQS（简单队列、至少一次语义、无 broker 管理）、Kinesis（流式分析）

---

### Q10. Kafka Rebalance

**主问**：Kafka Consumer Rebalance 什么情况下会触发？Rebalance 期间会发生什么？

**追问**：
- Range / Round-Robin / Sticky 三种分配策略的区别？
- Rebalance 风暴怎么解决？
- Controller Broker 挂了会发生什么？

**要点**：
- 触发：消费者增减、订阅 topic 变化、topic 分区数变化
- Rebalance 期间消费**暂停**（Stop The World），对延迟敏感业务是灾难
- Range：按分区序号平均分，可能不均；Round-Robin：轮询，均匀但不保证粘性；**Sticky**：尽量保持原分配，减少迁移
- Controller 选举靠 ZooKeeper 临时节点（KRaft 模式后不再依赖 ZK）

**AWS 映射**：
- MSK 支持所有 Kafka 原生客户端配置
- MSK 2.8+ 支持 KRaft 模式，无需 ZooKeeper
- Rebalance 对客户业务有影响时，建议排查消费者心跳 / session timeout 配置

---

### Q11. MSK / SQS / Kinesis 选型

**主问**：客户问：MSK、SQS、Kinesis 都是消息相关，怎么选？

**追问**：
- SQS Standard 和 FIFO 的区别？
- Kinesis Data Streams 和 Kinesis Firehose 区别？
- 每秒 10 万条消息，保留 7 天，有多个消费组各自独立消费，选哪个？

**要点**：
- **MSK**：高吞吐 + Kafka 生态 + 需要有序 + 保留时间长 + 多消费组回放
- **SQS**：简单队列 + 解耦 + 无运维；Standard 吞吐无限但可能乱序和重复，FIFO 保证顺序但 300 TPS/API
- **Kinesis Data Streams**：流式分析 + 多消费者 fan-out + 实时性要求高（毫秒~秒）
- **Kinesis Firehose**：无代码落地到 S3/Redshift/OpenSearch，不做消费侧编程

---

## 四、分布式事务

### Q12. 分布式事务选型

**主问**：订单成功要同时扣钱 + 加积分，三个服务三个库，用什么方案？

**追问**：
- 基于消息的最终一致性和 TCC 本质区别？
- TCC 为什么业务侵入性大？
- SAGA 和 TCC 怎么选？
- 2PC 为什么互联网很少用？

**要点**：
- 选型顺序：**单机 > 消息 > 补偿 > TCC > SAGA > 2PC**（优先选简单）
- **消息**：发起方说了算，跟随方异步跟进（订单 → 加积分）
- **补偿**：发起方 + 跟随方都要能确认（订单 → 扣钱）
- **TCC**：Try 冻结资源 → Confirm 真正扣减 / Cancel 释放。适合"中间态不能被用户看到"
- **SAGA**：长事务异步补偿，不保证中间态隔离
- **2PC**：同步阻塞 + 协调者单点 + 性能差

**AWS 映射**：
- **Step Functions** 实现 Saga 是经典模式：每一步是 Lambda，失败触发 Cancel 分支
- SQS + DLQ 做消息最终一致性
- DynamoDB Transactions 支持单 Region 跨表 ACID，可以替代一部分 2PC 场景

---

## 五、网络基础

### Q13. HTTP 1.0 / 1.1 / 2.0

**主问**：HTTP 2.0 相比 1.1 的核心改进？

**追问**：
- 多路复用解决了什么问题？底层怎么实现？
- 头部压缩 HPACK 怎么工作？
- HTTP/3 又改了什么？为什么要从 TCP 换成 QUIC？

**要点**：
- 1.1 vs 1.0：长连接（keep-alive）、Host 头、Range 断点续传、更细缓存控制
- 2.0 核心：**二进制分帧 + 多路复用 + 头部压缩（HPACK）+ Server Push**
- 多路复用：一个 TCP 连接并行多个请求，每消息拆成 Frame 带 Stream ID 交错传输，解决 HTTP 1.1 队头阻塞
- HPACK：静态字典 + 动态字典 + 霍夫曼编码
- HTTP/3：基于 QUIC（UDP），彻底解决 TCP 层的队头阻塞 + 更快的握手

**AWS 映射**：
- CloudFront 支持 HTTP/2 和 HTTP/3（2022 发布）
- ALB 也支持 HTTP/2（客户端到 ALB），ALB 到后端仍然是 HTTP/1.1
- 开启 HTTP/3 对**首屏加载**和**弱网络**场景有明显改善

---

### Q14. HTTPS 握手

**主问**：HTTPS 握手过程？用了什么加密方式？

**追问**：
- 对称加密和非对称加密分别用在哪一步？
- SSL 和 TLS 什么关系？
- HTTPS 为什么比 HTTP 慢？慢在哪里？
- 证书链是什么？浏览器怎么验证证书？

**要点**：
- HTTPS = HTTP + SSL/TLS
- 握手阶段用**非对称加密**（RSA / ECDHE）协商出**对称密钥**，之后用对称加密传数据
- 慢在：多一次 TLS 握手 RTT（TLS 1.2 要 2 RTT，TLS 1.3 只要 1 RTT）、加解密 CPU 消耗
- 证书链：根 CA → 中间 CA → 服务器证书，浏览器内置根 CA 公钥，逐级验证签名

**AWS 映射**：
- **ACM（Certificate Manager）**：免费签发证书 + 自动续期，用在 CloudFront / ALB / API Gateway
- CloudFront 支持 TLS 1.3，默认开启
- 自签名场景：ACM Private CA 做企业内部证书

---

### Q15. TCP 流量控制 vs 拥塞控制

**主问**：TCP 的流量控制和拥塞控制有什么区别？

**追问**：
- 滑动窗口是什么？发送窗口大小怎么确定？
- 为什么握手要三次？挥手要四次？
- TIME_WAIT 为什么是 2MSL？服务器 TIME_WAIT 过多怎么办？

**要点**：
- **流量控制**：接收方 → 发送方反压（接收窗口 rwnd），防止**接收缓冲区溢出**，端到端
- **拥塞控制**：网络整体层面，防止把网络打爆，用拥塞窗口 cwnd
- 实际发送窗口 = **min(rwnd, cwnd)**
- 三次握手：确认双方都有收发能力；两次：服务端无法确认客户端能收
- TIME_WAIT 2MSL：确保最后的 ACK 到达 + 让旧连接的报文消散

**AWS 映射**：
- **NLB（Network Load Balancer）**：工作在 L4，直接转发 TCP 连接，不做任何七层干预
- **ALB**：工作在 L7，TCP 到 ALB 终止，ALB 再和后端建立新 TCP 连接
- EC2 大量 TIME_WAIT：调 `net.ipv4.tcp_tw_reuse`、使用连接池

---

## 六、Web 请求链路

### Q16. 浏览器输入 URL 后发生了什么（SA 必问）

**主问**：浏览器输入 URL 到页面展示，中间发生了什么？

**追问**：
- DNS 递归查询和迭代查询的区别？
- 建立 TCP 连接是三次握手，HTTPS 是加上 TLS 握手，一共几次 RTT？
- 服务器返回 304 和 200 的区别？
- 页面渲染过程中回流（reflow）和重绘（repaint）的区别？

**要点**：
- 整体 6 步：**DNS 解析 → 建立 TCP 连接 → （TLS 握手）→ 发送 HTTP 请求 → 接收响应 → 关闭 TCP → 浏览器渲染**
- DNS 多级缓存：浏览器 → 系统 → 路由器 → ISP → 根 DNS → 顶级 DNS → 权威 DNS
- 304 Not Modified：服务端判断内容没变，让浏览器用本地缓存
- 回流改变布局（位置、大小），重绘只改样式（颜色），回流必然触发重绘

**AWS 映射（SA 招牌题）**：把每一步映射到 AWS 服务：
1. DNS → **Route 53**（权威 DNS），客户可以用 Route 53 做智能路由（延迟路由、地理路由、健康检查）
2. 接入 → **CloudFront**（边缘节点就近接入，减少 RTT）
3. TLS → **ACM** 发证书，CloudFront 做 TLS termination
4. 请求 → **ALB / API Gateway**（L7 路由）or **NLB**（L4 直通）
5. 应用 → **EC2 / ECS / EKS / Lambda**
6. 缓存 → **CloudFront** 静态资源缓存 + **ElastiCache** 应用层缓存
7. 存储 → **S3 / RDS / Aurora / DynamoDB**

能从一个 URL 讲到完整 AWS 架构，是 SA 的基本功。

---

## 七、存储与 IO

### Q17. BIO / NIO / AIO

**主问**：BIO、NIO、AIO 区别？分别适合什么场景？

**追问**：
- "同步非阻塞"和"异步非阻塞"的本质区别？
- NIO 的 Selector、Channel、Buffer 三个概念
- 为什么 Netty 选择 NIO 而不是 AIO？
- Linux 下 select / poll / epoll 的区别？

**要点**：
- BIO：一连接一线程，连接多线程爆炸
- NIO：Reactor 模式，一个线程通过 Selector 轮询多 Channel，适合**连接多但活跃少**
- AIO：OS 完成 IO 后回调应用，适合**连接多且连接时间长**
- epoll 比 select 快：事件驱动不轮询、支持百万连接

**AWS 映射**：
- Lambda 底层是单线程事件驱动，和 NIO 模型一致，**不适合长时间阻塞 IO**
- API Gateway 到 Lambda 走 HTTP 短连接，和长连接 WebSocket API 场景选型不同
- AppSync（GraphQL）用 WebSocket 实现订阅，是典型 NIO 应用场景

---

### Q18. 零拷贝

**主问**：Kafka 为什么快？零拷贝是什么？

**追问**：
- 传统 IO 读文件发网络经过几次拷贝、几次上下文切换？
- mmap 和 sendfile 分别减少了哪些拷贝？
- 零拷贝一定比传统 IO 快吗？

**要点**：
- 传统 IO：4 次拷贝（磁盘 → 内核 → 用户 → Socket 缓冲 → 网卡）+ 4 次上下文切换
- **mmap**：用户空间和内核空间**共享内存**，省掉"内核 → 用户"的拷贝；但还有 4 次上下文切换
- **sendfile**：数据不进用户空间，内核直接传到 Socket，2 次上下文切换 + 1 次 CPU 拷贝
- **真正的零拷贝**（硬件支持）：DMA 直接从内核缓冲到网卡

**AWS 映射**：
- MSK（Kafka）用零拷贝实现高吞吐
- S3 内部实现、EBS → EC2 传输都用了类似优化
- Lambda / Fargate 这类抽象层已经屏蔽了底层 IO 优化，开发者不用管

---

## 八、运维与故障

### Q19. OOM 常见原因

**主问**：生产 JVM 突然 OOM 了，可能有哪些原因？怎么排查？

**追问**：
- `Java heap space` 和 `GC overhead limit exceeded` 区别？
- `Metaspace / Permgen` OOM 怎么来？
- `Unable to create new native thread` 什么情况？
- 定位到内存泄漏，但不敢重启生产，怎么办？

**要点**：
- 5 类常见 OOM：
  1. **Java heap space**：堆满了，大对象 / 流量飙升 / 内存泄漏
  2. **GC overhead limit exceeded**：GC 占用 98% CPU 但回收不到 2%
  3. **Metaspace / Permgen**：加载 class 太多（反射 / 动态代理生成大量代理类）
  4. **Unable to create new native thread**：线程数超限（OS ulimit 或 kernel.pid_max）
  5. **Direct Buffer Memory**：堆外内存耗尽（Netty / NIO）
- 排查：`-XX:+HeapDumpOnOutOfMemoryError` 自动 dump，再用 MAT 分析

**AWS 映射**：
- EC2 Java 应用：CloudWatch 配置 memory metric（需要装 CloudWatch Agent，默认不收集内存）
- Lambda：内存配置直接影响 CPU 配额，不够就调大
- ECS/EKS：Container 内存超限触发 OOMKilled，看 `kubectl describe pod` 或 CloudWatch Container Insights

---

### Q20. 生产排错场景

**场景 A**：线上接口 P99 从 50ms 变成 2 秒，怎么排查？

**要点**（在 AWS 上的排查链路）：
1. **CloudWatch** 看监控：是单实例慢还是全部慢？
2. **X-Ray / APM** 看分段链路：是应用慢还是依赖（DB / 下游服务）慢？
3. **RDS Performance Insights** 看慢 SQL
4. **VPC Flow Logs** 看网络延迟
5. **ELB access log** 看是不是流量突增

**场景 B**：Kafka（MSK）消费端堆积 1000 万条消息

**要点**：
1. 判断：消费慢还是消费挂了？（CloudWatch MSK Consumer Lag）
2. 消费慢：**加消费者**（不能超过 partition 数），批量消费，异步化
3. 临时方案：扩到新 topic + 更多 partition，老 topic 继续慢慢消化
4. 事后：检查消费逻辑是不是有同步阻塞调用

---

## 九、架构白板题

> SA 面试必问环节，候选人画图 + 讲思路，面试官抛挑战。

### 题 1：高并发秒杀系统

设计 10 万 QPS 秒杀系统，库存 1000 件，要求：不超卖、响应 < 500ms、下单 5 分钟未支付自动释放库存。

**观察点**：接入层限流（CloudFront + WAF）、库存预扣（Redis Lua 原子操作）、异步下单（SQS）、延迟释放（Step Functions 或 SQS 延迟队列）

### 题 2：出海直播平台

用户在东南亚和中东，源站国内。延迟 < 3 秒、日 PV 1 亿、带宽 500 Gbps、考虑合规。

**观察点**：
- 推流：源站用 MediaLive，就近接入
- 分发：CloudFront 全球边缘
- 转码：MediaConvert
- 合规：数据主权（数据不出区）、本地化 Region 部署
- 成本：CloudFront 按区域计价差异大，重点考虑

### 题 3：SaaS 多租户后台

数据隔离方案？大小客户资源怎么分？支持自定义域名和 HTTPS？

**观察点**：
- Silo（每租户独立资源）vs Pool（共享资源）vs Bridge（混合）
- 大客户 Silo（独立 RDS + 独立 Cluster），小客户 Pool（共享 Aurora Serverless + 行级隔离）
- 自定义域名：Route 53 + ACM + CloudFront SNI
- 租户隔离：ABAC（IAM 策略 + 租户 ID tag）

### 挑战清单（必抛至少 2 个）

- 客户预算砍一半，你砍什么？
- 如果整个 Region 挂了会怎样？
- 客户架构师说这个方案过度设计，怎么回？
- 3 年后扩 10 倍还撑得住吗？

---

## 十、异议处理

### 场景 1：客户 DBA 不信任 Aurora

> 客户说："团队都是 MySQL DBA，Aurora 出问题排不了，还是用自建 MySQL on EC2。"

**好的回答**：
- 先共情（"您担心的是 troubleshooting 的能力建设对吗"）
- 客户视角价值：Aurora 95% 兼容 MySQL、运维 90% 托管、Support 兜底、长期 TCO 更低
- 折中方案：先用 Aurora 跑非核心业务，建立团队信心后再迁核心

**不好的回答**：
- "Aurora 比 MySQL 强多了"（技术优越感）
- "那好吧用自建"（直接认输）

### 场景 2：客户只想用 CDN，不想上云

> 客户说："我们只是想用 CloudFront 加速，不想迁其他服务。"

**好的回答**：
- 尊重客户边界，先把 CloudFront 做好
- 自然引入：日志分析可以用 Athena、WAF 防护可以加 AWS WAF、证书可以用 ACM 免费签发
- 不强推全栈，让客户在使用中自然发现其他服务的价值

### 场景 3：方案被挑战过度设计

> 客户架构师说："你这个方案太复杂了，我们用一台 EC2 + RDS 就够了。"

**好的回答**：
- 问背后的担忧：是预算？运维能力？还是觉得业务规模不需要？
- 根据反馈分层：核心必需（高可用）vs 加分项（自动扩缩容）vs 未来再加（跨 Region 容灾）
- 给出"精简版"和"完整版"两套方案，让客户选

---

## 用法说明

- 本文档是**问题池**，不是面试流程。按候选人简历挑题，不用全问。
- 每题的 **AWS 映射**部分是加分内容，候选人能从原理讲到 AWS 服务是 SA 岗核心素养。
- 架构白板题（第九节）**必问 1 道**，是 SA 面试最重要的信号来源。
