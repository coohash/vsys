<p align="right">
  📌 <a href="./README.md">简体中文</a> | <b>English Version</b>
</p>
# ⚡ VSYS Blockchain Python Code

> **VSYS (V Systems) Blockchain Python Script Repository** > Sample scripts (such as balance reading, fund collection, batch processing of various on-chain actions, etc.). Developers can provide this repository as a reference for AI tools (such as Gemini) to modify the Python code according to their own requirements.

---

## 💡 Technical Modules

| Module (Python) | Role | Highlights |
| :--- | :--- | :--- | 
| [📂 vsys_supernode_install](#1-vsys_supernode_install) | **VSYS Node One-Click Deployment** | Used for self-hosted nodes, includes mainnet data snapshots, etc. |
| [📂 Vanity_Address_Generator](#2-vanity_address_generator) | **VSYS Vanity Address Generation** | Search for addresses containing pure numbers, specific words, etc. |
| [📂 vsys_mass_transfer](#3-vsys_mass_transfer) | **VSYS Batch Transfer** | Distribute amounts in batches to multiple wallets according to requirements | 
| [📂 vsys_balance_checker](#4-vsys_balance_checker) | **VSYS Batch Balance Query** | Scan balances of massive addresses on the VSYS blockchain | 
| [📂 vsys_lease_manager](#5-vsys_lease_manager) | **VSYS Batch Lease/Cancel Lease** | One-click batch leasing and cancellation of leasing on VSYS | 
| [📂 vsys_volume_booster](#6-vsys_volume_booster) | **VSYS On-Chain Activity Activation** | Used to simulate VSYS ecosystem liquidity | 

---

## 🚀 Deep Dive

### 1. `vsys_supernode_install` 
* **Function**: VSYS blockchain node installation (used for self-hosted nodes, includes mainnet data snapshots, etc.)

### 2. `Vanity_Address_Generator`
* **Function**: Search for addresses containing pure numbers, specific words, etc., configurable, auto-exports addresses and private keys

### 3. `vsys_mass_transfer`
* **Function**: Use private key to access the master wallet, distribute amounts in batches to multiple wallets according to requirements

### 4. `vsys_balance_checker`
* **Function**: Scan balances of massive addresses on the VSYS blockchain, can be paired with Excel to record historical balance statuses

### 5. `vsys_lease_manager`
* **Function**: One-click batch leasing (Lease) and transactional withdrawal (Cancel) of VSYS assets

### 6. `vsys_volume_booster`
* **Function**: Used to simulate VSYS ecosystem liquidity, multi-tiered + 24-hour fully automated, transfer-collection self-looping

---

## 📜 Disclaimer
1. All batch operation scripts involved in this repository execute offline signatures within local memory; private keys are absolutely never transmitted to any network nodes.
2. Since the scripts require reading plaintext private keys, it is strongly recommended to run them on a completely clean computer/server. Please delete files containing private keys immediately after use.

## 🌐 VSYS Node Interface (API) 

When running the finalized Python code, it must connect to the VSYS "Node Interface (API)" to retrieve on-chain data. Depending on whether you use a "free public node" or a "self-hosted node", the running speed and configuration methods differ significantly:

--------------------------------------------------------------------------------
![Node](https://img.shields.io/badge/VSYS%20node-%E4%BD%BF%E7%94%A8VSYS%E5%85%AC%E5%BC%80%E8%8A%82%E7%82%B9-blue?style=for-the-badge&logo=linux&logoColor=white)
--------------------------------------------------------------------------------
* 🚀 Rate Limit: Public nodes are shared resources. To prevent server crashes, it is recommended that the code request rate does not exceed 200 requests/second.

* 📋 Common Public Node Addresses List:

  ```text
  [https://vnode.vcoin.systems](https://vnode.vcoin.systems)
  [http://13.238.187.118:9922](http://13.238.187.118:9922)
  [http://13.55.174.115:9922](http://13.55.174.115:9922)
  [http://gabija.vos.systems:9922](http://gabija.vos.systems:9922)
  [http://vakarine.vos.systems:9922](http://vakarine.vos.systems:9922)
  [http://wallet-node.v.systems:9922](http://wallet-node.v.systems:9922)

  Public nodes are not permanently stable and may become inaccessible or experience latency freezes at any time. Before using a specific node, please perform the following two manual check steps:

🔍 Check if the interface is alive: Copy the node address directly into your browser to open it. If it successfully displays a green-and-white Swagger debugging page, the node is online.

🔍 Check if data is synchronized: Append /blocks/height to the node address and press Enter in the browser. Check if the returned number (current block height) matches the height on the homepage of the official VSYS blockchain explorer (explorer.v.systems). If the values are identical, the node data is up to date and safe to use.

🚀 Speed Advantage: If you set up an independent private node on your own computer or server (refer to the vsys_supernode_install.txt documentation file in the project for specific setup methods), because there are no external local area network restrictions, the code invocation speed can soar up to over 8000 requests/second!

📍 Local Node Default Address: 127.0.0.1:9922

# 📂 Repository Directory Structure

VSYS-Blockchain-Python-Code/
├── .gitignore                       # Git ignore file configuration
├── README.md                        # This documentation file
├── requirements.txt                 # Dependencies package list (py-vsys, base58, aiohttp, etc.)
├── vsys_supernode_install.txt       # VSYS blockchain node installation (used for self-hosted nodes, includes mainnet data snapshots, etc.)
├── vsys_ai_context.txt              # Algorithmic logic (used for AI feeding)
├── vsys_combined_docs.md            # Consolidated Python user manual (used for AI feeding)
├── VSYS_node_List.txt               # VSYS node list, please test if online before use
│
├── Vanity_Address_Generator/        # VSYS blockchain vanity address generation
│   ├── vanity_generator.py          # Search for addresses containing pure numbers, specific words, etc., configurable, auto-exports addresses and private keys
│   ├── walletgenerator_v0.1.0.jar   # V Systems wallet generation and recovery tool
│   ├── 10000_VSYS_Address.txt       # Methodology for generating 10,000 VSYS addresses and private keys in batches
│   └── Run_the_example.png          # Execution example screenshot
│
├── vsys_mass_transfer/              # VSYS batch transfer
│   ├── vsys_mass_transfer.py        # Use private key to access the master wallet, distribute amounts in batches to multiple wallets according to requirements
│   └── recipients.csv               # Format example: List of receiving wallet addresses and amounts
│
├── vsys_balance_checker/            # VSYS batch balance query
│   ├── vsys_balance_checker.py      # Scan balances of massive addresses on the VSYS blockchain, can be paired with Excel to record historical balance statuses
│   └── list_address.csv             # Format example: VSYS wallet addresses
│
├── vsys_lease_manager/              # VSYS batch lease/cancel lease
│   ├── vsys_lease_manager.py        # One-click batch leasing (Lease) and transactional withdrawal (Cancel) of VSYS assets
│   ├── node.csv                     # Format example: Supernode addresses
│   ├── lease_add.csv                # Format example: List of addresses + private keys requiring leasing
│   └── cancel_lease.csv             # Format example: List of addresses + private keys requiring leasing cancellation
│
├── vsys_volume_booster/             # VSYS on-chain activity activation
│   ├── vsys_volume_booster.py       # Used to simulate VSYS ecosystem liquidity, multi-tiered + 24-hour fully automated, transfer-collection self-looping
│   ├── translate_midd.csv           # Format example: Transit stations, address + private key list
│   └── add_priv.csv                 # Format example: Independent, collection address + private key list
│
└── vsys_mainnet_data/               # VSYS mainnet node data snapshot
    ├── data_20260420.tar.gz         # Mainnet node data compressed package as of April 20, 2026 (VSYS block height 58062043)
    └── data_20260420.tar.gz         # Archive size is approx. 27G, unable to upload, please refer to vsys_supernode_install.txt to acquire
