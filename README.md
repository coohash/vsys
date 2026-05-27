<p align="right">
  <a href="./README.md"><img src="https://img.shields.io/badge/📌%20中文版-4F7CAC?style=for-the-badge" alt="ZH"/></a>
  <a href="./README_EN.md"><img src="https://img.shields.io/badge/🌐%20English-6C757D?style=for-the-badge" alt="EN"/></a>
</p>

# ⚡ VSYS Blockchain Python Code

<p align="left">
  <img src="https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/vsys--network-Mainnet-orange?style=flat-square" alt="VSYS"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
</p>

> **VSYS (V Systems) 区块链 Python 脚本仓库**
> 
> 示例脚本（如余额读取、资金归集、批量处理各种链上动作等）开发者可让AI参考（例如Gemini）按自己的需求修改Python代码。

---

## 💡 功能目录 / Technical Modules

| 代码 (Python) | 实现目标 (Role) | 特性说明 (Highlights) |
| :--- | :--- | :--- | 
| [📂 `vsys_supernode_install`](#1-vsys_supernode_install) | **VSYS节点一键部署** | 自建节点使用，包含主网数据快照等 |
| [📂 `Vanity_Address_Generator`](#2-vanity_address_generator) | **VSYS靓号地址生成** | 寻找纯数字、特定单词等地址 |
| [📂 `vsys_mass_transfer`](#3-vsys_mass_transfer) | **VSYS批量转账** | 按要求将金额批量分发 to 多个钱包 | 
| [📂 `vsys_balance_checker`](#4-vsys_balance_checker) | **VSYS余额批量查询** | VSYS区块链海量地址余额扫描 | 
| [📂 `vsys_lease_manager`](#5-vsys_lease_manager) | **VSYS批量租赁/取消租赁** | VSYS一键批量租赁与取消租赁 | 
| [📂 `vsys_volume_booster`](#6-vsys_volume_booster) | **VSYS链上活跃度激活** | 用于模拟VSYS生态流动性 | 
| [📂 `vsys_untraceable_mixer`](#7-vsys_untraceable_mixer) | **VSYS隐私混币器** | VSYS链上防追踪资产分发 | 

---

## 🚀 Python代码功能详解 / Deep Dive

### 1. `vsys_supernode_install` 
* **功能**：VSYS区块链节点安装（自建节点使用，包含主网数据快照等）

### 2. `Vanity_Address_Generator`
* **功能**：寻找纯数字、特定单词等地址，可配置，自动导出地址和私钥

### 3. `vsys_mass_transfer`
* **功能**：使用私钥登录主钱包，按要求将金额批量分发到多个钱包

### 4. `vsys_balance_checker`
* **功能**：VSYS区块链海量地址余额扫描，可配合用Excel记录历史余额情况

### 5. `vsys_lease_manager`
* **功能**：VSYS资产一键批量租赁（Lease）与流水退租（Cancel）

### 6. `vsys_volume_booster`
* **功能**：用于模拟VSYS生态流动性，多层级+24小时全自动，转账归集自循环
  
### 7. `vsys_untraceable_mixer`
* **功能**：VSYS防追踪资产分发，资产打碎、混合、交叉互转、重新聚合

---

## 📜 Disclaimer

> [!IMPORTANT]
> **资产安全红线说明**
> 1. 本仓库中涉及的所有批量操作脚本，均在本地内存中执行离线签名，私钥绝对不会向任何网络节点传输。
> 2. 由于脚本需要读取明文私钥，强烈建议在完全干净的电脑/服务器上运行。使用后请立即删除包含私钥的文件。

---

## 📜 Disclaimer
1. 本仓库中涉及的所有批量操作脚本，均在本地内存中执行离线签名，私钥绝对不会向任何网络节点传输。
2. 由于脚本需要读取明文私钥，强烈建议在完全干净的电脑/服务器上运行。使用后请立即删除包含私钥的文件。

## 🌐 VSYS 节点接口 (API) 

写好的 Python 代码在运行时，必须连接 VSYS 的“节点接口（API）”才能获取链上数据。根据使用的是“免费公开节点”还是“自己搭建的节点”，其运行速度和配置方法大不相同：

--------------------------------------------------------------------------------
![Node](https://img.shields.io/badge/VSYS%20node-%E4%BD%BF%E7%94%A8VSYS%E5%85%AC%E5%BC%80%E8%8A%82%E7%82%B9-blue?style=for-the-badge&logo=linux&logoColor=white)
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
  ```
* 公共节点不是永久稳定的，随时可能打不开或产生延迟卡死。在使用某个节点前，请务必进行以下两步人工检查：
  
  1. 🔍 检查接口是否活着：直接把节点地址复制到浏览器里打开。如果能顺利弹出一个绿白相间的 Swagger 调试页面，说明节点在线。
  2. 🔍 检查数据是否同步：在节点地址后面加上 /blocks/height 在浏览器里回车。看它返回的数字（当前区块高度），是否和 VSYS 官方区块链浏览器首页（explorer.v.systems）上的高度一致。如果数值一样，说明该节点数据是最新的，可以放心使用。

--------------------------------------------------------------------------------
![Security](https://img.shields.io/badge/VSYS%20node-%E4%BD%BF%E7%94%A8%E6%9C%AC%E5%9C%B0%E8%87%AA%E5%BB%BAVSYS%E8%8A%82%E7%82%B9-success?style=for-the-badge&logo=githubactions&logoColor=white)
--------------------------------------------------------------------------------
* 🚀 速度优势：如果是你在电脑或服务器上独立搭建的私有节点（具体搭建方式可参考项目内的 vsys_supernode_install.txt 说明文件），由于没有任何局域网外层网络限制，代码调用速度最高可飙升至 8000次/秒 以上！

* 📍 本地节点默认地址：127.0.0.1:9922

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
├── vsys_untraceable_mixer/          # VSYS隐私混币器
│   ├── start.py                     # 启动+交互界面
│   ├── gen_ledger.py                # 参数配置，生成任务清单（启动前请先进行设置）
│   ├── vsys_untraceable_mixer.py    # VSYS防追踪资产分发，资产打碎、混合、交叉互转、重新聚合
│   ├── sendlist.csv                 # 格式示例：最终收款目标地址列表，这是您的最终资产受益池L6。
│   ├── private.csv                  # 格式示例：等待使用的，地址+私钥储备池，使用后的地址会自动删除
│   ├── recipients.csv               # 格式示例：当前运行批次待处理名单
│   ├── complete-send.csv            # 格式示例：已完成转账的历史地址归档
│   └── used.csv                     # 格式示例：历史地址去重归档库
│
└── vsys_mainnet_data/               # VSYS主网节点数据快照
    ├── data_20260420.tar.gz         # 主网节点2026年4月20日数据压缩包（VSYS区块高度58062043）
    └── data_20260420.tar.gz         # 压缩包大小约27G，无法上传，请参考vsys_supernode_install.txt获取
  ```
