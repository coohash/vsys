# vsys
VSYS Blockchain Python Code
VSYS 区块链的Python代码示例，为了确保后续开发者能喂给AI，让AI（例如Gemini）按自己的需求修改Python代码，编写此 `README.md` 。

### 📄 README 说明文档规划如下
1. **项目定位**：生产级、防卡死、具备底层 struct 拼装能力的 Python 代码库。
2. **示例脚本**：示例脚本（如余额读取、资金归集、批量处理各种链上动作等）及快照文件进行标准归类。

> **VSYS (V Systems) 区块链底层开发与生产级 Python 脚本仓库**
> 本仓库由资深区块链架构师规划与维护，严格遵循 VSYS 官方底层协议及 `py-vsys` SDK 标准，收录了通过生产环境验证的高并发余额查询、自动化资金归集、交易字节流手工拼装等核心功能脚本。
---

## 🛰️ 核心架构与设计规范

在参与本仓库的开发或使用相关脚本时，必须严格遵守以下 **VSYS 底层数据与网络规范**，以防止链上资产损失或代码异常：

1. **数据与精度规范 (Satoshi)**
   * VSYS 内部最小精度单位为 `Satoshi`，换算比例为 $10^8$（即 `1 VSYS = 100,000,000 Satoshi`）。
   * 所有底层交易拼装或调用节点广播 API 时，金额（Amount）和手续费（Fee）必须显式乘以 `100_000_000` 并强制使用 `int` 类型包裹。
   * 网络基础转账手续费固定为 `10,000,000 Satoshi`（即 `0.1 VSYS`），`feeScale` 固定为 `100`。

2. **时间戳规范 (Timestamp)**
   * VSYS 底层协议字节流拼装必须使用 **19位纳秒级整数时间戳**：`int(time.time() * 1_000_000_000)`。

3. **底包兼容性适配 (Version Compatibility)**
   * 鉴于 `py_vsys` 库在不同环境存在版本命名与参数顺序断层，本仓库采用**动态包探测机制**与**参数顺序自动遍历适配**，确保代码在各版本 SDK 下均能稳定运行。

4. **高并发与防卡死设计**
   * 生产级脚本引入了 `asyncio` + `aiohttp` 异步高并发框架（推荐并发区间 `150 - 300`），并配置严格的超时回退与指数减速重试逻辑，防止因触发节点防火墙而导致请求卡死。

---

## 📂 仓库目录结构

```text
VSYS-Blockchain-Python-Code/
├── .gitignore                       # Git 忽略文件配置
├── README.md                        # 本说明文件
├── requirements.txt                 # 依赖软件包列表（py-vsys, base58, aiohttp等）
├── vsys_supernode_install.txt       # VSYS区块链节点安装（自建节点使用，包含主网数据快照等）
├── vsys_ai_context.txt              # 算法思维（AI 喂料使用）
├── vsys_combined_docs.md            # 整合的Py使用说明书（AI 喂料使用）
│
├── balance.py                       # 生产环境：基于 asyncio + aiohttp 高并发异步地址余额批量读取脚本
├── collect.py                       # 生产环境：全自动化多账户私钥资金归集引擎（含风控残留量控制与随机频控）
│
├── Vanity_Address_Generator/        # VSYS区块链靓号地址生成
│   ├── vanity_generator.py          # 寻找纯数字、特定单词等地址，可配置，自动导出地址和私钥
│   ├── walletgenerator_v0.1.0.jar   # V Systems 钱包生成与恢复工具
│   └── 10000_VSYS_Address.txt       # 批量生成1万的VSYS地址和私钥的方法
│   └── Run_the_example.png          # 运行示例
│
└── data/                            # 数据层定义
    ├── list_address.csv             # 输入文件示例：待处理的钱包地址列表（每行一个标准地址）
    ├── balance_address.csv          # 输出文件示例：高并发探测后自动生成的地址余额结果报表
    └── vsys_snapshot.json           # 历史快照
