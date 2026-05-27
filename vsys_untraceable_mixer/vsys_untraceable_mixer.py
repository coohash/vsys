# ==============================================================================
# 🛰️ SYSTEM ARCHITECTURE & OPERATIONAL SPECIFICATION / 系统架构与全流程运行说明书
# ==============================================================================
# 【核心宗旨】：本系统为 VSYS (V Systems) 区块链打造的高并发、高防追踪、自愈型自动化资金分发矩阵。
# 【设计原理】：采用“深度拓扑预推演 + 离线异步密码签名 + 链上资产水位自愈 + 混沌噪声注入”架构，
#               通过多层级网状级联转账，物理阻断统计学关联（Heuristic Linkage），确保资金分发合规安全。
# ==============================================================================

# ==============================================================================
# ⚙️ SECTION 1: GLOBAL CONFIGURATION MATRIX & OPTIMIZATION / 核心参数配置及调优建议
# ==============================================================================
# 提示：在正式启动前，请务必使用文本编辑器（如 VS Code、Notepad++）打开并检查各模块的 CONFIG 字典。
#
# 1. 节点网络流配置 (Node RPC Endpoint)
#    - 参数项: "NODE_URL": "http://wallet-node.v.systems:9922"
#    - 调优建议: 默认官方公开节点存在并发频率限制（Rate Limit，通常为 200次/秒）。在高频批量广播时，
#                极易触发 Connection Timeout 或 423 频率风控。若追求绝对稳定与无延迟分发，
#                强烈建议将其修改为本地自建超级/全节点的环回地址 "http://127.0.0.1:9922"。
#
# 2. 树状拓扑网络流设计 (Multi-Layer Infrastructure Design)
#    - 参数项: "LAYER_COUNTS": [1, 120, 9, 27, 9, 27]
#    - 机制说明: 定义从根节点（L0）到最终汇聚源（L5）每层独立运作的中间钱包数量。
#    - ⚠️ 避坑红线: 必须深刻理解地址消耗公式：中间钱包总需求 = sum(LAYER_COUNTS[1:6]) + 噪声黑洞预留。
#                若随意将层级拉大到 [1, 50, 500, 2500, 5000, 100]，将瞬间物理消耗掉 8000+ 个干净地址！
#                启动前必须通过 `10000_VSYS_Address.txt` 导出的离线工具生成海量地址注入 `private.csv`。
#
# 3. 混沌噪声与流向混淆 (Obfuscation & Noise Injection)
#    - 参数项: "HORIZONTAL_DRIFT_PROB": 1.0 (100%) | "DUMMY_SINK_PROB": 1.0 (100%)
#    - 参数项: "INFLOW_SOURCES": (1, 2)
#    - 机制说明: 
#      * HORIZONTAL_DRIFT：控制同层级节点之间横向交叉互转的概率。打破垂直下拨的单一流向，使链上图谱呈现网状混沌。
#      * DUMMY_SINK：控制中间节点向非目标池（垃圾黑洞地址）丢弃小额资产的概率，制造海量链上噪音，阻断AI大数据的剪枝追踪。
#      * INFLOW_SOURCES：最终收款端（L6）随机从 L5 层挑 1~2 个钱包作为直接上游，消除固定配对特征。
#
# 4. 财务风控与物理防卡死红线 (Financial Safety Margins)
#    - 参数项: "FEE": Decimal("0.1") | "MIN_TRANSFER": Decimal("0.2")
#    - 参数项: "SAFETY_MARGIN" (账本端): Decimal("6.0") | "SAFETY_MARGIN" (发射端): Decimal("2.0")
#    - 🌟 核心调优: 由于混淆漂移任务是动态随机触发的，层级回溯计算时极易产生累加精度微差或矿工费超额消耗。
#                * 账本端 6.0 VSYS：在生成账本时，强制让每一层的父节点给子节点多打 6.0 枚资产作为“防干涸备用金”。
#                * 发射端 2.0 VSYS：执行广播时，若中转站水位因意外低于单笔转账红线，L0 总金库会自动介入并自动
#                  补给“缺口 + 2.0 VSYS”的燃油费，进入 Waiting 循环直至链上到账自愈，彻底终结了传统脚本报错卡死的死穴。

# ==============================================================================
# 📦 SECTION 2: FILE DATASTREAM FLOW / 全局文件系统流转与职责矩阵
# ==============================================================================
# 本系统基于严密的 I/O 流转设计，每个文件各司其职，请勿在运行期间用 Excel 独占打开以下 CSV 文件：
#
# 1. private.csv       [输入] 离线干净地址密钥储备池。格式必须为：地址,私钥（每行一个）。
#                             由 gen_ledger.py 读取，提取后其私钥在内存中执行离线签名，绝对不通过网络传输。
# 2. used.csv          [输出] 历史地址去重归档库。一旦某批地址被提取并在 start.py 中确认锁定，
#                             会物理从 private.csv 中剥离并追加（Append）到此文件中，绝对杜绝地址复用（Address Reuse）。
# 3. sendlist.csv      [输入] 最终收款目标地址列表（L6 层）。这是您的最终资产归集受益池。
#                             请在百分之百确认已在离线 U 盘安全备份了这批地址的私钥后，再将其写入。
# 4. recipients.csv    [缓冲] 当前批次待处理名单。系统启动后，自动从 sendlist.csv 头部切割（Slice）N 个地址
#                             存入此处，作为当前批次的清算输入，实现大批量名单的“分批、分流、高吞吐”处理。
# 5. complete-send.csv [归档] 永续已完成大库。每次新批次启动，上次处理完的 recipients.csv 数据会自动归档至此。
# 6. task_ledger.json  [核心] 拓扑状态机账本。由 gen_ledger.py 倒推推演定型后生成，包含所有垂直、横向、噪声
#                             交易的时序流，以及本次运行所需的全部中间层私钥内存快照。
# 7. transfer_log.csv  [日志] 断点续传对账流。记录每笔成功广播的 Task ID 与链上 TxID。
#                             若因网络断网或重启，系统会自动加载此文件，跳过已发地址，实现无缝断点续传。

# ==============================================================================
# 🛰️ SECTION 3: STEP-BY-STEP OPERATIONAL GUIDE / 零基础点火运行四步法
# ==============================================================================
#
# 【第一步：环境依赖注入与前置准备】
# 1. 本系统底层强依赖密码学组件。如果您的 Python 环境缺失相关依赖，请打开终端执行以下命令：
#    pip install requests base58 py-vsys
# 2. 准备地址库：确保 private.csv 里有充足的干净地址（建议预先离线生成 >10 万个）。
# 3. 准备目标库：将您最终要归集的收款地址写入 sendlist.csv。
#
# 【第二步：前置参数审计与核对】
# 1. 打开 gen_ledger.py，将您的主金库根节点地址与私钥填入 CONFIG 的 "L0_ADDR" 与 "L0_PRI_KEY"。
# 2. 依据当前 L0 节点的资产总量，评估并调整 "L6_AMOUNT_RANGE"（目标到账范围）及拓扑层级。
#
# 【第三步：一键点火启动控制台】
# 1. 鼠标右键点击代码所在的文件夹空白处 ➔ 选择【在终端打开】（Open in Terminal）或打开 PowerShell。
# 2. 在控制台中键入下方命令并敲击回车：
#    python start.py
#
# 【第四步：人机交互与最终风控确认】
# 1. 系统启动后，会自动执行环境净化，并提示：`🔢 请输入本次要处理的地址数量 (N): `
# 2. 键入您本次想从分发大库里切片处理的接收地址数量（例如：10），敲回车。
# 3. 脚本会自动调用 gen_ledger.py 进行反向回溯计算，并在终端控制台打印出精密的财务报告。
# 4. ⚠️ 终极大闸门：仔细核对控制台顶部打印的【L0 总准备金需求】。
#    * 若确认账目无误，请在 `确认开始发送吗？(Y/N): ` 提示下键入大写 `Y`。
#    * 系统将激活 vsys_untraceable_mixer.py 执行发射引擎，开启赛博朋克单行高精 UI 大盘滚动监控！
#    * 若发现资金预算超限，键入 `N` 即可一键安全拦截，整个交易树将锁死在本地，绝不上链。
# ==============================================================================
import time, struct, base58, json, os, requests, random, sys
from decimal import Decimal, ROUND_UP
from datetime import datetime, timedelta

# ==============================================================================
# ⚙️ 【SYSTEM GLOBAL CONFIGURATION MATRIX / 全局核心配置区】
# ==============================================================================
CONFIG = {
    # [NODE_URL]：目标 VSYS 节点的 RPC 接口地址。
    # 💡 调优建议：高频批量广播时，如果使用公开节点易触发 200次/秒 的风控限制，导致高概率请求超时。
    #            若追求极速无延迟分发，强烈建议将其修改为本地自建节点的本地环回地址 "http://127.0.0.1:9922"。
    "NODE_URL": "http://wallet-node.v.systems:9922",
    
    # [TASK_FILE]：任务状态机账本模板文件。
    # 💡 说明：本文件是由上游脚本（如 gen_ledger.py）推演生成的层级拓扑结果。
    #          脚本会解析其中的 "tasks" 数组以获取流水，并提取 "keys" 字典在内存中进行离线私钥签名。
    "TASK_FILE": "task_ledger.json",
    
    # [LOG_FILE]：持久化断点续传流水日志文件。
    # 💡 说明：一旦某笔交易成功广播并拿到 TxID，脚本会以追加模式（'a'）向此文件写入任务唯一标识。
    #          重新点火启动脚本时，系统会自动读取此文件并构建 processed 集合，实现免重复发送的断点续传。
    "LOG_FILE": "transfer_log.csv",
    
    # [L0_ADDRESS]：生态总金库/主资金源头账户地址。
    # 💡 安全警告：当中转大户地址（task['from']）余额不足以支付分发金额与矿工费时，
    #            引擎会自动调用该 L0 地址对中转地址实施自愈性补给。请确保该地址对应的私钥已安全锁定在 TASK_FILE 的 keys 中。
    "L0_ADDRESS": "ARRfwY4cJNJBBHjHxKm5YVbuUSPvvV2WdMR", 
    
    # [FEE]：单笔链上交易的标准矿工费消耗（单位：VSYS）。
    # 💡 说明：当前 VSYS 主网标准常规转账（Payment Transaction）的默认消耗为 0.1 枚。
    "FEE": Decimal("0.1"),
    
    # [SAFETY_MARGIN]：总金库补给缓冲冗余资金（单位：VSYS）。
    # 💡 机制解密：当中转站触发自动补给时，L0 并不是卡死边缘“缺多少补多少”，
    #            而是会额外叠加发送 2.0 枚 VSYS，确保中转站始终有充裕的油耗余额来抵扣后续高频广播产生的矿工费。
    "SAFETY_MARGIN": Decimal("2.0"),
}

# [FEE_UNIT]：矿工费最小精度原子解算。将 Decimal 转换成链上底层识别的聪（Satoshi）单位。
# 💡 算力对齐：0.1 VSYS ➔ 0.1 * 100,000,000 = 10,000,000 Satoshi
FEE_UNIT = int(CONFIG["FEE"] * 100_000_000)

# 🎨 终端 UI 视觉颜色代码矩阵（ANSI Escape Codes）
C_CYAN = "\033[96m"       # 青色：用于进度条、百分比、ETA 等主轮廓提示
C_GREEN = "\033[92m"      # 绿色：用于标识交易广播成功
C_YELLOW = "\033[93m"     # 黄色：用于警告提示
C_MAGENTA = "\033[95m"    # 品红：用于标识交易失败、异常拦截或补给触发
C_RESET = "\033[0m"       # 重置：清除终端颜色渲染污染

# 🌐 初始化 HTTP 高性能持久连接会话，屏蔽系统代理环境变量，规避由于代理报错导致的连接崩塌
session = requests.Session()
session.trust_env = False

def get_balance(address):
    """
    【链上瞬态可用余额审计函数】
    直接通过 RPC 连接目标节点的 /addresses/balance/{address} 接口，秒级抓取当前的 Satoshi 级资产高度。
    """
    try:
        r = session.get(f"{CONFIG['NODE_URL']}/addresses/balance/{address}", timeout=3)
        return r.json().get('balance', 0) if r.status_code == 200 else 0
    except: return 0

def send_vsys_payment(from_addr, to_addr, amount_satoshi, keys_dict, sign_func, curve_mod):
    """
    【底层原生签名与一键交易广播引擎】
    此函数抛弃了高级封装，手动通过 struct 大端序（`>`）精确构建 VSYS Type 2（Payment）原始字节流。
    """
    try:
        # 生成纳秒级高精度全局唯一时间戳（VSYS 底层防双花/重放攻击的核心验证依据）
        ts = int(time.time() * 1_000_000_000)
        
        # Base58 逆向解码明文私钥，还原为底层密码学所需的原始 Byte 流
        pri_bytes = base58.b58decode(keys_dict[from_addr])
        
        # 🛡️ [CRYPTOGRAPHIC BYTE MATRIX / 原始交易字节流手动组装序列]
        # >B (1字节): Type=2 (转账)  | >Q (8字节): 时间戳  | >Q (8字节): 金额 (Satoshi)
        # >Q (8字节): 矿工费 (Satoshi)| >H (2字节): feeScale (固定100)
        # base58 (26字节): 接收方钱包地址字节序列 | >H (2字节): Attachment 长度 (0)
        tx_bytes = struct.pack(">B", 2) + struct.pack(">Q", ts) + struct.pack(">Q", amount_satoshi) + \
                   struct.pack(">Q", FEE_UNIT) + struct.pack(">H", 100) + \
                   base58.b58decode(to_addr) + struct.pack(">H", 0)
        
        # 兼容性动态适配：智能兼容 py-vsys 官方库中不同版本的特征签名函数
        sig = sign_func(pri_bytes, tx_bytes) if sign_func.__name__ != 'signature' else sign_func(tx_bytes, pri_bytes)
        
        # 构建符合 Swagger 规范的标准 JSON 广播载荷
        payload = {
            "senderPublicKey": base58.b58encode(curve_mod.gen_pub_key(pri_bytes)).decode(),
            "recipient": to_addr, "amount": amount_satoshi, "fee": FEE_UNIT,
            "feeScale": 100, "timestamp": ts, "signature": base58.b58encode(sig).decode()
        }
        
        # 向公链广播序列化后的交易载荷，若成功则返回 32 位 TxID 哈希，若失败则安全返回 None
        res = session.post(f"{CONFIG['NODE_URL']}/vsys/broadcast/payment", json=payload, timeout=5).json()
        return res.get('id')
    except: return None

def main():
    # --------------------------------------------------------------------------------
    # --- 阶段 1. 密码学基础依赖注入与向下兼容 ---
    # --------------------------------------------------------------------------------
    try:
        from py_vsys import curve
    except:
        import py_vsys.utils.crypto.curve_25519 as curve
    sign_f = next((getattr(curve, m) for m in ['sign', 'sign_data', 'signature'] if hasattr(curve, m)), None)

    # --------------------------------------------------------------------------------
    # --- 阶段 2. 状态机恢复与断点续传历史加载 ---
    # --------------------------------------------------------------------------------
    with open(CONFIG["TASK_FILE"], 'r') as f: ledger = json.load(f)
    processed = set()
    # 读取日志流水，解析第一列的任务唯一指纹（t_id），将其推入哈希表以跳过已发送成功的地址
    if os.path.exists(CONFIG["LOG_FILE"]):
        with open(CONFIG["LOG_FILE"], 'r') as f:
            for line in f:
                if line.strip(): processed.add(line.split(',')[0].strip())

    # --------------------------------------------------------------------------------
    # --- 阶段 3. 动态多层级拓扑调度优先权因子排序 ---
    # --------------------------------------------------------------------------------
    # 核心算法：对层级名称进行深度反向求值。如果层级名包含 "drift" 则权重赋 1，包含 "dummy" 赋 2，其余赋 0。
    # 保证整个流水严格按照 [层级数字从小到大 -> 正常任务 -> 随机漂移任务 -> 混淆伪装任务] 的严密时序推进。
    def layer_priority(ln):
        p = str(ln).split('_'); w = 1 if 'drift' in ln else (2 if 'dummy' in ln else 0)
        return (int(p[0]), w)

    sorted_layers = sorted(list(set(str(t['layer']) for t in ledger['tasks'])), key=layer_priority)
    total_tasks = len(ledger['tasks'])
    start_idx = len(processed)
    current_idx = start_idx
    start_time = time.time()

    # --------------------------------------------------------------------------------
    # --- 阶段 4. 永续主循环执行矩阵与自动资金自愈 (Refill) ---
    # --------------------------------------------------------------------------------
    for layer_id in sorted_layers:
        tasks = [t for t in ledger['tasks'] if str(t['layer']) == layer_id]
        # 判断当前层级是否属于“随机漂移”或“伪装干扰”性质的非核心流
        is_obfus = any(x in layer_id for x in ["drift", "dummy"])
        
        for task in tasks:
            # 拼装唯一的任务原子指纹校验块，用于精确比对断点续传集合
            t_id = f"{task['layer']}_{task['from']}_{task['to']}_{task['amount']}"
            if t_id in processed: continue
            
            current_idx += 1
            # ⏱️ 移动平均高精 ETA 动态剩余时间估算算法
            elapsed = time.time() - start_time
            avg_time = elapsed / (current_idx - start_idx) if (current_idx - start_idx) > 0 else 0
            eta_seconds = int(avg_time * (total_tasks - current_idx))
            eta_str = f"{eta_seconds // 3600:01}:{ (eta_seconds % 3600) // 60:02}:{eta_seconds % 60:02}" if eta_seconds > 3600 else f"{(epoch_min := (eta_seconds % 3600) // 60):01}:{eta_seconds % 60:02}"

            # 资产对齐：将读取出的常规精度 VSYS 字符串转换为底层 int64 的 Satoshi 聪大小
            amt_sat = int(round(Decimal(task['amount']) * 100_000_000))
            need_total = amt_sat + FEE_UNIT
            
            # 🎛️ 【AUTOMATED CAPITAL SELF-HEALING / 核心账户余额无感自愈内循环状态机】
            while True:
                bal = get_balance(task['from'])
                if bal >= need_total: break  # 水位达标，通过风控关卡，放行进入广播区域
                
                if not is_obfus:
                    # 💡 自愈逻辑：计算当前实际缺口，额外补给 SAFETY_MARGIN，自动呼叫 L0 总金库无线划拨补给
                    refill_sat = (need_total - bal) + int(CONFIG["SAFETY_MARGIN"] * 100_000_000)
                    if send_vsys_payment(CONFIG["L0_ADDRESS"], task['from'], refill_sat, ledger['keys'], sign_f, curve):
                        # 成功触发总金库向中转站划拨，强制非阻塞休眠 15 秒以给超级节点留足落盘打包并达成共识（Consensus）的时间
                        time.sleep(15)
                    else: 
                        time.sleep(5) # 补给广播遭遇网络抖动失败，短暂休眠 5 秒后自动重试，直至总金库资产枯竭
                else: 
                    break # 如果是伪装混淆流资产本身不足，不触发 L0 强力补给，直接退出
            
            # 双重保险防满溢：如果中转站水位在经过上述自愈后仍未达标，则跳过该次转账，保护链上广播不发生 "Negative Balance" 拒单
            if get_balance(task['from']) < need_total: continue

            # --------------------------------------------------------------------------------
            # --- 阶段 5. 最终点火广播与炫酷可视化大盘落盘 ---
            # --------------------------------------------------------------------------------
            tx_id = send_vsys_payment(task['from'], task['to'], amt_sat, ledger['keys'], sign_f, curve)
            
            # --- 📊 极客级单行等宽滚动进度条 UI 矩阵拼接区 ---
            bar_count = int((current_idx / total_tasks) * 15)
            progress_bar = f"[{'█' * bar_count}{'-' * (15 - bar_count)}]"
            percent_str = f"{(current_idx / total_tasks) * 100:>5.1f}%"
            layer_str = f"Layer: {layer_id:<8}"
            # 隐藏敏感全量明文钱包地址，仅高亮展示首尾截断脱敏后的后 3 位，方便对账
            flow_str = f"*{task['from'][-3:]} ➔ *{task['to'][-3:]}"
            amount_str = f"{task['amount']:>10} VSYS"
            
            # 状态分流染色：若链上广播成功则渲染生动的荧光绿，若失败由于 None 引发异常则渲染警告品红
            color = C_GREEN if tx_id else C_MAGENTA
            
            # 拼装标准输出流控制行
            output = f"{C_CYAN}{progress_bar} {percent_str} | {eta_str} | {layer_str} | {flow_str} | {color}{amount_str}{C_RESET}"
            print(output)

            # 状态机归盘：成功拿到 TxID 后，立刻以原子追加形式写入断点日志，锁死状态防重发
            if tx_id:
                with open(CONFIG["LOG_FILE"], 'a') as f: f.write(f"{t_id},{tx_id}\n")

            # ⚙️ 动态反追踪速率控制（Rate Limiting Matrix）：
            # 若处于深度伪装状态，采用 0.8~2.0 秒的无序长尾延迟进行混沌伪装；
            # 若处于主路线的高频流水状态，采用 0.3~0.6 秒的极速并发延迟以最大化压榨节点并发通道。
            time.sleep(random.uniform(0.8, 2.0) if is_obfus else random.uniform(0.3, 0.6))

if __name__ == "__main__":
    main()