> **VSYS (V Systems) 区块链底层开发与 Python 脚本仓库**
VSYS Blockchain Python Code
VSYS 区块链的Python代码示例，定位生产级、防卡死、具备底层 struct 拼装能力的 Python 代码库。示例脚本（如余额读取、资金归集、批量处理各种链上动作等）及快照文件进行标准归类。开发者可喂给AI，让AI（例如Gemini）按自己的需求修改Python代码。

# 🌐 VSYS 节点接口 (API) 使用与测速指南

写好的 Python 代码在运行时，必须连接 VSYS 的“节点接口（API）”才能获取链上数据。根据使用的是“免费公开节点”还是“自己搭建的节点”，其运行速度和配置方法大不相同：

--------------------------------------------------------------------------------
📌 1. 使用免费公开节点（轻度使用）
--------------------------------------------------------------------------------
*  🚀 速度限制：公开节点是公共资源，为了防止服务器崩溃，建议代码请求速度不要超过 200次/秒。

* 📋 常用公开节点地址一览：

  ```text
  https://vnode.vcoin.systems
  http://13.238.187.118:9922
  http://13.55.174.115:9922
  http://gabija.vos.systems:9922
  http://vakarine.vos.systems:9922
  http://wallet-node.v.systems:9922
* 公共节点不是永久稳定的，随时可能打不开或产生延迟卡死。在使用某个节点前，请务必进行以下两步人工检查：
  
  1. 🔍 检查接口是否活着：直接把节点地址复制到浏览器里打开。如果能顺利弹出一个绿白相间的 Swagger 调试页面，说明节点在线。
  2. 📊 检查数据是否同步：在节点地址后面加上 /blocks/height 在浏览器里回车。看它返回的数字（当前区块高度），是否和 VSYS 官方区块链浏览器首页（explorer.v.systems）上的高度一致。如果数值一样，说明该节点数据是最新的，可以放心使用。

--------------------------------------------------------------------------------
⚡ 2. 使用自建本地节点
--------------------------------------------------------------------------------
* 🚀 速度优势：如果是你在电脑或服务器上独立搭建的私有节点（具体搭建方式可参考项目内的 vsys_supernode_install.txt 说明文件），由于没有任何局域网外层网络限制，代码调用速度最高可飙升至 8000次/秒 以上！

* 📍 本地节点默认地址：https://127.0.0.1:9922

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
├── VSYS_node_List.txt               # VSYS节点列表，使用前请先测试是否在线
│
├── Vanity_Address_Generator/        # VSYS区块链靓号地址生成
│   ├── vanity_generator.py          # 寻找纯数字、特定单词等地址，可配置，自动导出地址和私钥
│   ├── walletgenerator_v0.1.0.jar   # V Systems 钱包生成与恢复工具
│   └── 10000_VSYS_Address.txt       # 批量生成1万的VSYS地址和私钥的方法
│   └── Run_the_example.png          # 运行示例
│
├── vsys_mass_transfer/              # VSYS批量转账
│   ├── vsys_mass_transfer.py        # 使用私钥登录主钱包，按要求将金额批量分发到多个钱包
│   └── recipients.csv               # 格式示例：接收钱包地址和金额列表
│
├── vsys_balance_checker/            # VSYS余额批量查询
│   ├── vsys_balance_checker.py      # VSYS区块链海量地址余额扫描，可配合用Excel记录历史余额情况
│   └── list_address.csv             # 格式示例：VSYS钱包地址
│
├── vsys_lease_manager/              # VSYS批量租赁/取消租赁
│   ├── vsys_lease_manager.py        # VSYS资产一键批量租赁（Lease）与流水退租（Cancel）
│   ├── node.csv                     # 格式示例：超级节点地址
│   ├── lease_add.csv                # 格式示例：需进行租赁的地址+私钥列表
│   └── cancel_lease.csv             # 格式示例：需取消租赁的地址+私钥列表
│
├── vsys_volume_booster/             # VSYS链上活跃度激活
│   ├── vsys_volume_booster.py       # 用于模拟VSYS生态流动性，多层级+24小时全自动，转账归集自循环
│   ├── translate_midd.csv           # 格式示例：中转站，地址+私钥列表
│   └── add_priv.csv                 # 格式示例：独立，归集地址+私钥列表
│
└── data/                            # VSYS主网节点数据快照
    ├── data_20260420.tar.gz         # 主网节点2026年4月20日数据压缩包（VSYS区块高度58062043）
    └── data_20260420.tar.gz         # 压缩包大小约27G，无法上传，请参考vsys_supernode_install.txt获取
