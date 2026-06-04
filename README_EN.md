<p align="right">
  <a href="./README.md"><img src="https://img.shields.io/badge/✅ 中文版-FF7A00?style=for-the-badge&logo=translate&logoColor=white" alt="ZH"/></a>
  <a href="./README_EN.md"><img src="https://img.shields.io/badge/✨ English Version-7CB342?style=for-the-badge&logo=translate&logoColor=white" alt="EN"/></a>
</p>

# ⚡ VSYS Blockchain Python Code

<p align="left">
 <img src="https://img.shields.io/badge/vsys--network-Mainnet-orange?style=flat-square" alt="VSYS"/>
 <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="VSYS"/>
 <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11-darkgreen.svg" alt="VSYS"/>
 <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS-orange.svg" alt="VSYS"/>
 <img src="https://img.shields.io/badge/Engine-Asynchronous%20State--Machine-blueviolet.svg" alt="VSYS"/>
</p>

> **VSYS (V Systems) Blockchain Python for Beginners**
> 
> This project is extremely friendly to users with zero programming background. By following the detailed environment configuration guide provided in `requirements.txt`, you can quickly run all the Python code. It is highly recommended to use AI (e.g., Gemini) for debugging or modifying the Python code to suit your specific needs during use.

---

## 💡 Feature Directory / (vsystems)

| Code (Python) | Target (Role) | Highlights | Tag |
| :--- | :--- | :--- | :--- | 
| [📂 `vsys_supernode_install`](#1-vsys_supernode_install) | **VSYS Node Deployment** | Self-hosted node method, mainnet data snapshot | Supernode |
| [📂 `Vanity_Address_Generator`](#2-vanity_address_generator) | **VSYS Vanity Address Generation** | Find pure numeric, specific word addresses, etc. | Vanity Collision, Mass Addresses |
| [📂 `vsys_mass_transfer`](#3-vsys_mass_transfer) | **VSYS Mass Transfer** | Batch distribute funds to multiple wallets | Batch Transfer, Asset Distribution |
| [📂 `vsys_balance_checker`](#4-vsys_balance_checker) | **VSYS Batch Balance Checker** | Mass address balance scanning on VSYS blockchain | Mass Scan, Balance Query |
| [📂 `vsys_lease_manager`](#5-vsys_lease_manager) | **VSYS Batch Lease/Cancel Lease** | Batch leasing and canceling leases on VSYS | Batch Lease, Pipeline Unlease |
| [📂 `vsys_volume_booster`](#6-vsys_volume_booster) | **VSYS On-chain Activity Booster** | Simulate VSYS ecosystem liquidity | Ecosystem Activity, Add Liquidity |
| [📂 `vsys_untraceable_mixer`](#7-vsys_untraceable_mixer) | **VSYS Multi-layer Privacy Transfer** | Untraceable asset distribution on VSYS chain | Multi-layer Transfer, Cross-Transfer |
| [📂 `vsys_batch_sweeper`](#8-vsys_batch_sweeper) | **VSYS Batch Balance Sweeper** | Batch aggregate balances from multiple VSYS addresses | Fund Aggregation, Balance Sweeping |

---

## 🚀 Python Code Features Detailed (V Systems)

This project contains a series of Python automation and ecosystem tools developed for the VSYS (V Systems) blockchain. Below is an overview of the core functional modules:

| # | Script/Module Name |  Category  | Core Feature Description |
| :-: | :--- | :--- | :--- |
| 1 | `vsys_supernode_install` | <sub>⛓️ Private Node</sub> | <sub>One-click installation of VSYS blockchain supernode (for self-hosted nodes, includes mainnet data snapshots, etc.).</sub> |
| 2 | `Vanity_Address_Generator` | <sub>💎 Vanity Generation</sub> | <sub>Find personalized addresses such as pure numbers or specific words, supports custom configuration, and automatically exports addresses and private keys.</sub> |
| 3 | `vsys_mass_transfer` | <sub>💸 Asset Distribution</sub> | <sub>Log into the main wallet using a private key, and batch distribute funds to multiple target wallets according to custom requirements.</sub> |
| 4 | `vsys_balance_checker` | <sub>💳 Data Audit</sub> | <sub>Mass address balance scanning on the VSYS blockchain, supports using Excel to record and track historical balances.</sub> |
| 5 | `vsys_lease_manager` | <sub>💰 Staking Lease</sub> | <sub>One-click batch leasing (Lease) and streamlined canceling (Cancel) of VSYS assets.</sub> |
| 6 | `vsys_volume_booster` | <sub>🔄 Boost Activity</sub> | <sub>Used to simulate VSYS ecosystem liquidity, supports multi-tier + 24-hour fully automatic transfer and sweeping self-circulation.</sub> |
| 7 | `vsys_untraceable_mixer` | <sub>🔀 Multi-layer Transfer</sub> | <sub>VSYS untraceable asset distribution, supports asset fragmentation, mixing, cross-transferring, and re-aggregation.</sub> |
| 8 | `vsys_batch_sweeper` | <sub>📥 Asset Sweeping</sub> | <sub>Automatically batch aggregate the available balances of multiple VSYS wallet accounts to a specified single target address.</sub> |

---

## 🌐 VSYS Node Interface (API) 

When running the provided Python code, it must connect to the VSYS Node API to fetch on-chain data. The execution speed varies greatly depending on whether a "Public Node" or a "Self-hosted Node" is used:

![Node](https://img.shields.io/badge/VSYS%20node-Using_VSYS_Public_Node-blue?style=for-the-badge&logo=linux&logoColor=white)
* 🚀 Speed Limit: Public nodes are public resources. To prevent excessive occupation, it is recommended that the code request rate does not exceed 100 times/second.
* 📋 List of common public node addresses:
 ```text
  [https://vnode.vcoin.systems](https://vnode.vcoin.systems)
  [http://13.238.187.118:9922](http://13.238.187.118:9922)
  [http://13.55.174.115:9922](http://13.55.174.115:9922)
  [http://gabija.vos.systems:9922](http://gabija.vos.systems:9922)
  [http://vakarine.vos.systems:9922](http://vakarine.vos.systems:9922)
  [http://wallet-node.v.systems:9922](http://wallet-node.v.systems:9922)
```
Public nodes are not permanently stable. Before using them, please be sure to perform the following two manual checks:
1. 🔍 Check if the API is alive: Copy the node address directly into your browser. If the Swagger page opens, the node is online.
2. 🔍 Check if the data is synced: Append "/blocks/height" to the node address to get the block height. If it matches the VSYS official explorer (explorer.v.systems), it is up to date and safe to use.
3. 
![Security](https://img.shields.io/badge/VSYS%20node-%E4%BD%BF%E7%94%A8%E6%9C%AC%E5%9C%B0%E8%87%AA%E5%BB%BAVSYS%E8%8A%82%E7%82%B9-success?style=for-the-badge&logo=githubactions&logoColor=white)
🚀 Speed Advantage: If you are using a private node independently set up on your computer or server (refer to vsys_supernode_install.txt for setup instructions), the code calling speed can exceed 8000 times/second since there are no external network restrictions.

📍 Default local node address: 127.0.0.1:9922

📂 Repository Directory Structure
 ```text
VSYS-Blockchain-Python-Code/
├── .gitignore                       # Git ignore file configuration
├── README.md                        # This readme file
├── requirements.txt                 # List of dependency packages (py-vsys, base58, aiohttp, etc.)
├── vsys_supernode_install.txt       # VSYS blockchain node installation (for self-hosted nodes, includes mainnet data snapshots)
├── vsys_ai_context.txt              # Algorithmic thinking (for AI context feeding)
├── vsys_combined_docs.md            # Integrated Python user manual (for AI context feeding)
├── VSYS_node_List.txt               # VSYS node list, please test if online before use
│
├── Vanity_Address_Generator/        # VSYS blockchain vanity address generation
│   ├── vanity_generator.py          # Find pure numeric, specific word addresses, configurable, auto-exports addresses and private keys
│   ├── walletgenerator_v0.1.0.jar   # V Systems wallet generation and recovery tool
│   └── 10000_VSYS_Address.txt       # Method to batch generate 10,000 VSYS addresses and private keys
│   └── Run_the_example.png          # Run example
│
├── vsys_mass_transfer/              # VSYS mass transfer
│   ├── vsys_mass_transfer.py        # Log into main wallet with private key, batch distribute amounts to multiple wallets as required
│   └── recipients.csv               # Format example: List of receiving wallet addresses and amounts
│
├── vsys_balance_checker/            # VSYS batch balance checker
│   ├── vsys_balance_checker.py      # Mass address balance scanning on VSYS blockchain, can be used with Excel to record historical balances
│   └── list_address.csv             # Format example: VSYS wallet addresses
│
├── vsys_batch_sweeper/              # Batch VSYS balance one-click sweeping
│   ├── vsys_batch_sweeper.py        # Consolidate funds scattered across multiple VSYS wallets and safely aggregate them into a specified wallet
│   └── to-be-collected.csv          # Format example: VSYS wallet addresses + private keys waiting to be aggregated
│
├── vsys_lease_manager/              # VSYS batch lease / cancel lease
│   ├── vsys_lease_manager.py        # One-click batch lease and pipeline unlease of VSYS assets
│   ├── node.csv                     # Format example: Supernode address
│   ├── lease_add.csv                # Format example: List of addresses + private keys for leasing
│   └── cancel_lease.csv             # Format example: List of addresses + private keys for canceling leases
│
├── vsys_volume_booster/             # VSYS on-chain activity booster
│   ├── vsys_volume_booster.py       # Simulate VSYS ecosystem liquidity, multi-tier + 24-hour fully automatic transfer and sweep self-circulation
│   ├── translate_midd.csv           # Format example: Transit station, list of addresses + private keys
│   └── add_priv.csv                 # Format example: Independent, aggregated addresses + private keys list
│
├── vsys_untraceable_mixer/          # VSYS multi-layer privacy transfer
│   ├── start.py                     # Startup + interactive interface
│   ├── gen_ledger.py                # Parameter configuration, generate task list (please set up before starting)
│   ├── vsys_untraceable_mixer.py    # VSYS untraceable asset distribution, asset fragmentation, mixing, cross-transfer, re-aggregation
│   ├── sendlist.csv                 # Format example: Final receiving target address list (your final asset beneficiary pool L6)
│   ├── private.csv                  # Format example: Waiting to be used, address + private key reserve pool, addresses will be auto-deleted after use
│   ├── recipients.csv               # Format example: Pending list for the current running batch
│   ├── complete-send.csv            # Format example: Historical address archive of completed transfers
│   └── used.csv                     # Format example: Deduplicated historical address archive library
│
└── vsys_mainnet_data/               # VSYS mainnet node data snapshot
    ├── data_20260420.tar.gz         # Mainnet node April 20, 2026 data archive (VSYS block height 58062043)
    ├── data_20260420.tar.gz         # Archive size is about 27G, cannot be uploaded, please refer to vsys_supernode_install.txt to obtain
    └── vsys_address_snapshot        # Traverse and scan blocks, offline evolution tracking, and parse interactions
```
📜 Disclaimer
[!IMPORTANT]
Blockchain Security Warning
1. All batch operation scripts in this repository perform offline signing in local memory. Private keys will absolutely never be transmitted to any network node.
2. Since the scripts need to read plaintext private keys, please run them on a clean computer/server. It is recommended to immediately delete files containing private keys after use.

[![Buy me a coffee](https://img.shields.io/badge/Buy_me_a_coffee-AR4j2MginGAS9zZzG1Y2rxZz43555592517-blueviolet?labelColor=555555)](https://explorer.v.systems/address/AR4j2MginGAS9zZzG1Y2rxZz43555592517)
