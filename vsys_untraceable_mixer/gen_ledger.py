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
import csv, json, random, os
from decimal import Decimal, ROUND_UP

# ====================================================================================
# ⚙️ 【SYSTEM TOPOLOGY CONFIGURATION MATRIX / 全局核心拓扑配置区】
# ====================================================================================
# 提示：本区域定义了整个资金分发网络的结构、混淆程度、安全边界以及核心 I/O 路径。
# 调整这里的参数会直接改变生成的 task_ledger.json 拓扑形态。
# ------------------------------------------------------------------------------------
CONFIG = {
    # --- 📂 文件/数据库输入输出路径 (I/O Path Settings) ---
    # [PRIVATE_CSV]: 离线原始密钥储备池。格式须为: 地址,私钥 (每行一个)。脚本会从中提取干净地址进行任务绑定。
    "PRIVATE_CSV": "private.csv",       
    # [USED_CSV]: 历史地址去重归档库。被用过的中间层地址会被物理移动到这里，防范地址复用攻击（Address Reuse）。
    "USED_CSV": "used.csv",             
    # [RECIPIENTS_CSV]: 最终接收资金的目标钱包名单。即长效任务链的最终汇聚终点（L6层）。
    "RECIPIENTS_CSV": "recipients.csv", 
    
    # --- 🏦 主金库根节点配置 (Root Treasury Configuration) ---
    # [L0_PRI_KEY] & [L0_ADDR]: 整个分发链路的最初始资金源头（Root 节点）。
    # 💡 运维提示：请务必保证该 L0 地址在链上有充足的 VSYS 余额，否则下游执行引擎会因为源头缺油而中断。
    "L0_PRI_KEY": "3kFxJqep9y4qcBLuaSTRqLgqzQZwVZ9mCxCp5FwCyn6Z", 
    "L0_ADDR": "ARRfwY4cJNJBBHjHxKm5YVbuUSPvvV2WdMR",             
    
    # --- 🗂️ 树状拓扑结构设计 (Multi-Layer Topology Architecture) ---
    # [LAYER_COUNTS]: 定义从 L0 层到 L5 层，每一层级在网络中分布的独立钱包数量。
    # 📊 当前架构解析:
    #     L0 (1个总金库) ➔ L1 (120个分发大户) ➔ L2 (9个中转) ➔ L3 (27个中转) ➔ L4 (9个中转) ➔ L5 (27个直接汇聚源)，请依据自己的需求设置，例如[1, 5, 100, 500, 2000, 100]等。
    "LAYER_COUNTS": [1, 120, 9, 27, 9, 27],  
    # [INFLOW_SOURCES]: 最终收款端（L6）的入账多样性配置。
    # 💡 机制说明: 每个 L6 目标地址在接收资产时，会随机从 L5 层中挑选 1 到 2 个节点作为其直接上游，
    #            从空间维度打乱固定配对，阻断统计学关联（Heuristic Linkage）。
    "INFLOW_SOURCES": (1, 2),               

    # --- 🌪️ 高级混淆与干扰因子 (Obfuscation & Noise Parameters) ---
    # [HORIZONTAL_DRIFT_PROB]: 同层平移概率。控制同一层级内的钱包之间互转资金的概率（0.0=关闭，1.0=100%触发）。
    # 💡 混淆原理: 在垂直下拨的过程中，加入同层横向交叉流动（Drift），使链上追踪流呈现网状混沌状态。
    "HORIZONTAL_DRIFT_PROB": 1.0,       
    # [DUMMY_SINK_PROB]: 诱导黑洞概率。控制节点向非目标池（垃圾地址）丢弃小额资产的概率，用以制造链上噪音（Noise Injection）。
    "DUMMY_SINK_PROB": 1.0,             
    
    # --- 🛡️ 资金链安全红线系数 (Financial Safety Margins - 防卡死核心) ---
    # [FEE]: VSYS 链上标准常规转账交易所消耗的法定矿工费（0.1 VSYS）。
    "FEE": Decimal("0.1"),              
    # [SAFETY_MARGIN]: 全层级防干涸备用金（单位：VSYS）。
    # 🌟 核心机制: 这是整个系统长效稳定运行的关键！每一层回溯计算时，都会强制给子节点多打 6.0 枚 VSYS。
    #            这批备用金将在下游执行引擎中，自动抵扣由于混淆任务激增、网络抖动重试等带来的全部矿工费消耗，绝对闭环防卡死。
    "SAFETY_MARGIN": Decimal("6.0"),    
    # [PRECISION_COMP]: 浮点数/高精十进制精度截断微小补位补丁，消灭由于多层级除法产生的微小精度微差（Dust）。
    "PRECISION_COMP": Decimal("0.01"),  
    # [MIN_TRANSFER]: 最小物理转账阈值。如果某个混淆任务计算出的金额低于 0.2 VSYS，则强行拉高至 0.2，防止由于低于手续费导致废单。
    "MIN_TRANSFER": Decimal("0.2"),     
    
    # --- 🎲 随机动态金额衰减矩阵 (Dynamic Random Amount Ranges) ---
    # [L6_AMOUNT_RANGE]: 规定最终到达 L6 目标钱包的单笔清算金额在 3.0 到 5.0 VSYS 之间随机浮动。
    "L6_AMOUNT_RANGE": (3.0, 5.0),     
    # [DRIFT_AMOUNT_RANGE]: 横向平移混淆任务的单笔随机交易金额区间。
    "DRIFT_AMOUNT_RANGE": (2.0, 5.0),   
    # [DUMMY_AMOUNT_RANGE]: 扔往黑洞/诱导地址的垃圾噪音交易单笔随机金额区间。
    "DUMMY_AMOUNT_RANGE": (2.0, 5.0)    
}

def build_mixed_topology_ledger():
    # --------------------------------------------------------------------------------
    # --- 阶段 1. 环境审计、密钥池提取与多层级容器初始化 ---
    # --------------------------------------------------------------------------------
    mid_needed = sum(CONFIG["LAYER_COUNTS"][1:6])    # 计算中间层（L1-L5）总共需要的独立钱包数量
    dummy_reserve = int(mid_needed * 0.9)            # 动态富余预留：计算黑洞/干扰噪声所需的独立外部地址数量
    total_needed = mid_needed + dummy_reserve        # 本次任务拓扑所需的绝对物理地址总需求量

    if not os.path.exists(CONFIG["PRIVATE_CSV"]): 
        print("❌ 错误: 找不到 private.csv")
        return
        
    with open(CONFIG["PRIVATE_CSV"], 'r', encoding='utf-8-sig') as f:
        all_pool_rows = [row for row in csv.reader(f) if len(row) >= 2]
    
    # 红线拦截：如果池子里的干净地址数量少于总需求，拒绝生成账本，防止中间层地址坍塌或交叉污染
    if len(all_pool_rows) < total_needed:
        print(f"❌ 错误: 地址不足！需 {total_needed}，剩 {len(all_pool_rows)}")
        return

    # 进行物理切片：提取当前批次所需的地址数量，并将剩余的地址切分保留
    current_use_rows = all_pool_rows[:total_needed]
    remaining_rows = all_pool_rows[total_needed:]

    mid_rows = current_use_rows[:mid_needed]
    dummy_sinks = [r[0].strip() for r in current_use_rows[mid_needed:]] # 成功剥离出干扰黑洞地址池
    
    mid_key_map = {r[0].strip(): r[1].strip() for r in mid_rows}       # 构建内存高质私钥查找矩阵
    all_addrs = list(mid_key_map.keys())
    
    # 初始化树状结构容器，将切片好的干净地址按 CONFIG 规定的数量规整地填充到 L1~L5 容器中
    layers = {i: [] for i in range(6)}
    layers[0] = [CONFIG["L0_ADDR"]]
    curr = 0
    for L in range(1, 6):
        count = CONFIG["LAYER_COUNTS"][L]
        layers[L] = all_addrs[curr : curr + count]
        curr += count

    # 读取最终接收清算的终端目标地址
    with open(CONFIG["RECIPIENTS_CSV"], 'r', encoding='utf-8-sig') as f:
        l6_targets = [row[0].strip() for row in csv.reader(f) if row]

    # 初始化全网总需求记账大盘 needs，所有初始账户额度归 0
    needs = {addr: Decimal("0") for addr in (all_addrs + [CONFIG["L0_ADDR"]] + l6_targets + dummy_sinks)}
    raw_tasks = []

    # --------------------------------------------------------------------------------
    # --- 阶段 2. 逻辑 A: L5 -> L6 终端主线汇聚演推 ---
    # --------------------------------------------------------------------------------
    # 算法逻辑：采用多源汇聚模式。对于每一个 L6 目标，随机指定上游父节点，并按照随机权重（Weight）
    #         切分总金额，通过高精度八位小数（Satoshi 级）进行截断取整，确保账目平衡。
    print("🔄 1. 规划 L5->L6 汇聚路径...")
    for target in l6_targets:
        total_amt = Decimal(str(random.uniform(*CONFIG["L6_AMOUNT_RANGE"]))).quantize(Decimal("0.00000000"), ROUND_UP)
        num_sources = random.randint(*CONFIG["INFLOW_SOURCES"])
        parents = random.sample(layers[5], num_sources) # 从 L5 容器中随机抽签选择上游
        
        weights = [random.uniform(0.6, 1.4) for _ in range(num_sources)]
        total_weight = sum(weights)
        curr_sum = Decimal("0")
        
        for i, parent in enumerate(parents):
            if i == num_sources-1:
                share = total_amt - curr_sum # 最后一笔通过减法完全闭合，绝对杜绝由于多位除法产生的小数点精度丢失
            else:
                share = (total_amt * (Decimal(str(weights[i]))/Decimal(str(total_weight)))).quantize(Decimal("0.00000000"), ROUND_UP)
            
            if share < CONFIG["MIN_TRANSFER"]: share = CONFIG["MIN_TRANSFER"]

            curr_sum += share
            raw_tasks.append({"from": parent, "to": target, "amount": share, "layer": "5"})
            # 【核心公式一】: L5 父节点对该任务所需支撑的最小资金 = 划拨额 + 单笔转账手续费 + 核心备用金
            needs[parent] += share + CONFIG["FEE"] + CONFIG["SAFETY_MARGIN"]

    # --------------------------------------------------------------------------------
    # --- 阶段 3. 逻辑 B & C: 反向回溯网络流计算与双重噪声侵入 ---
    # --------------------------------------------------------------------------------
    # 算法逻辑：从 L4 层开始逆向回溯直至根节点 L0。在每一层垂直资金流生成的前后，
    #         强行注入横向平移（Drift）以及垃圾伪装（Dummy Sink）等干扰任务，并将产生的新开销动态累加到父层中。
    print("🔄 2. 全层级回溯计算并注入安全冗余...")
    
    for L in range(4, -1, -1):
        current_layer_nodes = layers[L+1] # 当前正在接受回溯审计的子层节点集合
        
        for node in current_layer_nodes:
            # 【🌪️ 干扰一：同层横向平移混淆逻辑 / Horizontal Drift】
            if random.random() < CONFIG["HORIZONTAL_DRIFT_PROB"] and needs[node] > Decimal("0.5"):
                sibling = random.choice(current_layer_nodes)
                if sibling != node:
                    drift_val = random.uniform(*CONFIG["DRIFT_AMOUNT_RANGE"])
                    amt = Decimal(str(drift_val)).quantize(Decimal("0.00000000"), ROUND_UP)
                    raw_tasks.append({"from": sibling, "to": node, "amount": amt, "layer": f"{L+1}_drift"})
                    # 开销轧差转移：提供资金的同层节点物理负债增加，接收资金的节点负债减少
                    needs[sibling] += amt + CONFIG["FEE"]
                    needs[node] -= amt 

            # 【🌪️ 干扰二：黑洞丢弃垃圾混淆逻辑 / Dummy Noise Sink】
            if random.random() < CONFIG["DUMMY_SINK_PROB"]:
                sink = random.choice(dummy_sinks) # 扔往完全无关的纯外部混淆诱导池
                dummy_val = random.uniform(*CONFIG["DUMMY_AMOUNT_RANGE"])
                amt = Decimal(str(dummy_val)).quantize(Decimal("0.00000000"), ROUND_UP)
                raw_tasks.append({"from": node, "to": sink, "amount": amt, "layer": f"{L+1}_dummy"})
                # 制造噪音导致该中间节点产生额外资金消耗，开销强制追加
                needs[node] += amt + CONFIG["FEE"]

        # 【🔗 核心垂直递推：子层整体总负债向上清算归集至父层】
        for i, child in enumerate(layers[L+1]):
            # 通过取模（%）算法，将子层的大批钱包均匀、散列地绑定到上层较少数量的父节点钱包上（M对N映射）
            parent = layers[L][i % len(layers[L])] 
            base_need = needs[child]
            
            if base_need > 0 or L < 5: 
                # 制造轻微的链上残留碎屑（Dust），使每一个中间层钱包在分发完成后，账面留有不规则的极少余额，伪装成真实活跃钱包
                dust = Decimal(str(random.uniform(0.05, 0.2))).quantize(Decimal("0.00000000"), ROUND_UP)
                
                # 【核心公式二】：上层父节点向下层子节点进行大宗下拨的单笔金额推演
                # 父转子的单笔金额 = 子节点当前层全部任务总支出 + 精度补偿 + 残留碎屑 + 全层级安全冗余金
                child_total = base_need + CONFIG["PRECISION_COMP"] + dust + CONFIG["SAFETY_MARGIN"]
                
                if child_total < CONFIG["MIN_TRANSFER"]:
                    child_total = CONFIG["MIN_TRANSFER"]

                raw_tasks.append({"from": parent, "to": child, "amount": child_total, "layer": str(L)})
                # 父节点累加该笔下拨开销及对应的手续费，继续向其更上层传递负债，直至收敛到 L0 产生总准备金需求
                needs[parent] += child_total + CONFIG["FEE"]

    # --------------------------------------------------------------------------------
    # --- 阶段 4. 地址状态持久化隔离与任务时序定型归盘 ---
    # --------------------------------------------------------------------------------
    # 将本次提取出来的珍贵中间层地址写入已使用库，并在原始密钥池中剔除，保障地址单次生命周期（Isolate State）
    with open(CONFIG["USED_CSV"], 'a', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows(current_use_rows)

    with open(CONFIG["PRIVATE_CSV"], 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows(remaining_rows)

    # 格式化所有的十进制金额为标准字符串，准备输出为标准 JSON 账本
    final_tasks = [{"from": t['from'], "to": t['to'], "amount": str(t['amount'].quantize(Decimal("0.00000000"))), "layer": t['layer']} for t in raw_tasks]
    
    # 📊 关键排序算法：保证下拨任务严格按照 [L0->L1->L1混淆->L2->L2混淆...->L5->L6] 的拓扑顺序分层定型
    def sort_key(task):
        l = task['layer']
        if '_' in l:
            base, type_ = l.split('_')
            return float(base) + 0.5 # 混淆层紧随对应的正向层级之后执行
        return float(l)

    final_tasks.sort(key=sort_key)

    # 将高度精密的拓扑任务流与全量中间层私钥内存快照，打包封装写入最终的 task_ledger.json
    with open("task_ledger.json", "w") as f:
        json.dump({"tasks": final_tasks, "keys": {**mid_key_map, CONFIG["L0_ADDR"]: CONFIG["L0_PRI_KEY"]}}, f, indent=4)

    # 打印可视化总控风控报告，供架构师在点火执行前进行人工对账审核
    print(f"\n{'='*55}\n✅ 账本生成完毕 | 高安全冗余模式已开启\n{'-'*55}")
    print(f"🏦 L0 总准备金需求: {needs[CONFIG['L0_ADDR']]:.4f} VSYS")
    print(f"🛡️  全层级(L0-L5)已注入 SAFETY_MARGIN: {CONFIG['SAFETY_MARGIN']} VSYS")
    print(f"⛽ 任务总数: {len(raw_tasks)}\n{'='*55}\n")

if __name__ == "__main__": 
    build_mixed_topology_ledger()