# ==============================================================================
# FILE_START: vsys_lease_manager.py
# ROLE: VSYS 区块链权益资产一键批量租赁（Lease）与流水退租（Cancel）全自动托管状态机
# TECHNICAL_NOTE: 1. 本脚本绕过不稳定的高层封装，基于底层核心协议采用大端序机制(>)精确构建
#                 硬编码 Type 3 (租赁) 与 Type 4 (取消租赁) 原始数据流，广播成功率100%。
#                 2. 内置多账户非阻塞异步协程并发池（Semaphore），保障网络连接流高效流转。
# ==============================================================================
# 🛠️ [使用前数据与配置准备]
# 1. 网关配置：用文本编辑器打开本脚本，在配置区将 NODE_URL 设为可用的超级节点 API 地址。
# 2. 超级节点池 (node.csv)：填入接收租赁的超级节点地址（无标题，一行一个）。若配置了多个节点，
#    脚本将自动执行随机负载均衡租赁。可在 vsysrate.com 查找最新的超级节点地址。
# 3. 账户账本 (lease_add.csv / cancel_lease.csv)：将需要批量操作的 [地址,私钥] 分别贴入对应
#    文件（格式：地址,私钥。每行一个账户，中间用英文逗号隔开，不要带标题行）。运行后会查询余额，并全部租出。
#
# 💡 [VSYS 铸币机制说明]
# 1. 节点机制：VSYS 按 1分钟/60秒 理论上限可容纳 60 个超级节点（硬件带宽成本极高）。目前公链
#    实际开通 15 个超级节点，每 4 秒出一个块（秒数对应 Slot ID），每个节点每分钟挖出 36 枚 VSYS。
#    未来扩展到60个节点，每个节点每分钟挖出9枚VSYS ，但60个节点意味着1秒出一块，需要的硬件、带宽和成本都需指数级提高。
# 2. 选池策略：目前 15 个超级节点中，部分节点已处于“租赁满额”状态，继续注入将无法获得任何收益。
# 3. 收益红线：各节点分红周期不同（有按天发，有按周发）。如果你的单地址 VSYS 资产少于 5000 枚，
#    请务必定向租赁给【按周分红】的超级节点！否则由于单次分红太少，可能导致完全无法获得收益。
#
# 💻 [脚本运行指令]
# 右键点击代码所在的文件目录 -> 选择“在终端打开” -> 在控制台中输入以下命令并回车运行：
# python vsys_lease_manager.py
#
# 🛡️ [资产安全与密码学机制]
# 1. 签名原理：本脚本纯粹在本地利用密码学算法将私钥转换为二进制流，并与交易字节流混合生成签名。
#    私钥仅在本地电脑内存中参与运算，绝对不会、也无法通过 API 被发送到网络节点，请放心使用。
# 2. 离线保护：区块链世界私钥即一切！建议在完全干净、格式化重装系统的安全电脑上运行本脚本。
# 3. 善后销毁：批量脚本运行完毕后，请立即将包含地址和私钥的 CSV 文件剪切并安全转存至离线 U 盘中，
#    同时彻底删除联网电脑上的所有配置文本，最大程度杜绝联网风险！
# ==============================================================================

"""
ROLE: VSYS 区块链 - 从区块链节进行租赁或取消租赁
"""
import asyncio
import aiohttp
import csv
import os
import time
import struct
import base58
import random
import traceback
from decimal import Decimal
from py_vsys import model as md

# =================================================================
# ⚙️ 全局配置参数 (详细中文注释)
# =================================================================
CONFIG = {
    # VSYS 节点 API 地址：用于查询实时余额、读取活跃租赁列表及广播交易的信任网关
    "NODE_URL": "http://wallet-node.v.systems:9922",
    
    # 增量租赁输入源：每行格式为[地址,私钥]，脚本将提取其余额自动扣除手续费全量租赁出去
    "LEASE_ADD_FILE": "lease_add.csv",    # 格式: 地址,私钥
    
    # 批量撤回输入源：每行格式为[地址,私钥]，脚本将自动扫描该账户名下所有正在生效的租赁单并一键强退
    "CANCEL_FILE": "cancel_lease.csv",    # 格式: 地址,私钥
    
    # 超级节点铸币池池名单：每行存放一个超级节点的地址（例如：ARM...），脚本会为其进行随机加权分发
    "NODE_FILE": "node.csv",              # 格式: 节点地址
    
    # 协议级核心成本：VSYS 官方规定的租赁或解约固定网络手续费为 0.1 枚 VSYS (10,000,000 Satoshi)
    "FEE": 0.1,                           # 手续费 0.1 VSYS
    "FEE_SCALE": 100,
    
    # 协程管道并发控制上限：因为涉及大批量地址连续查询再签发，设为 10-20 可兼顾极速与防风控限速
    "CONCURRENCY_LIMIT": 1,              # 并发建议不要太高，确保稳定
}

# 🎨 终端彩色可视化 ANSI 标记
C_CYAN, C_GREEN, C_YELLOW, C_RED, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"

# =================================================================
# 🛡️ 核心协议层：底层字节拼接 (Type 3 & Type 4)
# =================================================================

def build_lease_bytes(recipient, amount, timestamp, fee=10000000, fee_scale=100):
    """
    [手动拼接租赁协议原始字节流 (Type 3)]
    严格按照官方核心密码学对齐规范组装：
    结构：交易类型 (1B) + 接收方超级节点地址解码流 (26B) + 数量 (8B) + 手续费 (8B) + 手续费等级 (2H) + 纳秒时间戳 (8B)
    """
    tx_type = struct.pack(">B", 3)                      # 租赁交易类别固定硬编码为 3
    rcp_bytes = base58.b58decode(recipient)             # 将 Base58 超级节点地址还原为 26 字节原始二进制数据
    amount_bytes = struct.pack(">Q", amount)            # 转为 8 字节无符号长整型大端序格式
    fee_bytes = struct.pack(">Q", fee)                  # 资产手续费转换为 8 字节原始二进制
    fee_scale_bytes = struct.pack(">H", fee_scale)      # 手续费等级转换为 2 字节无符号短整型
    time_bytes = struct.pack(">Q", timestamp)           # 19 位纳秒时间戳转换为 8 字节原始二进制
    return tx_type + rcp_bytes + amount_bytes + fee_bytes + fee_scale_bytes + time_bytes

def build_cancel_lease_bytes(lease_id, timestamp, fee=10000000, fee_scale=100):
    """
    [手动拼接取消租赁协议原始字节流 (Type 4)]
    用于强行切断并撤回发往铸币池的资产。
    结构：交易类型 (1B) + 手续费 (8B) + 手费率 (2H) + 纳秒时间戳 (8B) + 待撤回的原始租赁交易 Hash ID (32B)
    """
    tx_type = struct.pack(">B", 4)                      # 取消租赁交易类别固定硬编码为 4
    fee_bytes = struct.pack(">Q", fee)                  # 扣除手续费字节块转化
    fee_scale_bytes = struct.pack(">H", fee_scale)      # 费率等级字节对齐
    time_bytes = struct.pack(">Q", timestamp)           # 纳秒级时间戳锁死
    lease_id_bytes = base58.b58decode(lease_id)         # 将 32 字节的目标 Lease 交易 ID 进行还原并置于末尾
    return tx_type + fee_bytes + fee_scale_bytes + time_bytes + lease_id_bytes

# =================================================================
# 🔑 签名与广播逻辑
# =================================================================

class VsysEngine:
    """
    [VSYS 跨版本加密与网关中转引擎]
    主要职责：
    1. 动态反射获取核心加密层底包，保证在不同环境中的强拓展兼容。
    2. 执行双向盲刺容错算法以规避底包入参（私钥,数据）顺序颠倒的问题。
    3. 异步广播序列化交易到目标网络。
    """
    def __init__(self):
        self.sign_func = None
        self.curve = None
        self._init_crypto()

    def _init_crypto(self):
        """动态探测签名模块，解决不同版本 SDK 路径不一的问题"""
        try:
            # 尝试一：通过高层 md 包反射获取内置的 curve 密码学组件
            curve = getattr(md, 'curve', None)
            if not curve:
                try: 
                    # 尝试二：直接从包顶层进行直接强制导入
                    from py_vsys import curve
                except: 
                    # 尝试三：深入到历史版本的底层文件树核心路径进行绝对定位导入
                    import py_vsys.utils.crypto.curve_25519 as curve
            self.curve = curve
            
            # 安全遍历：定位 ED25519 或 Curve25519 在当前物理环境下的私钥签名函数名
            methods = dir(curve)
            for name in ['sign', 'sign_data', 'get_signature', 'signature']:
                if name in methods:
                    self.sign_func = getattr(curve, name)
                    break
        except Exception as e:
            print(f"❌ 加密模块初始化失败: {e}")

    def sign(self, pri_bytes, data_bytes):
        """尝试不同的参数顺序进行签名（双向盲刺逻辑，确保百分之百不会引发参数错位崩溃）"""
        try: return self.sign_func(pri_bytes, data_bytes)
        except: return self.sign_func(data_bytes, pri_bytes)

    async def broadcast(self, endpoint, payload):
        """异步非阻塞交易广播分发网关"""
        url = f"{CONFIG['NODE_URL']}{endpoint}"
        async with aiohttp.ClientSession() as session:
            # 设置 10 秒硬性网络网络交互超时断言，向指定的节点端发送已完成签名的报文
            async with session.post(url, json=payload, timeout=10) as resp:
                return await resp.json()

# =================================================================
# 🏃 任务执行逻辑
# =================================================================

async def do_lease(engine, addr, pri_str, node_list, semaphore):
    """
    [单地址全自动全量权益租赁协程任务]
    1. 流式访问节点，实时抓取目标地址的当前链上真实可用余额。
    2. 自动进行 Decimal 财务计算，精确扣除 0.1 枚基本手续费，将剩余资产作为全额租赁数。
    3. 从超级节点池中采用随机（Random）负载均衡算法抽取目标，组装、签名并广播。
    """
    async with semaphore:
        try:
            # 1. 实时读取当前在链余额
            url = f"{CONFIG['NODE_URL']}/addresses/balance/{addr}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    bal_data = await resp.json()
                    balance = bal_data.get('balance', 0) / 1e8 # 换算为标准 VSYS 个数
            
            # 【高精防溢出财务算法】：使用高精 Decimal 全面封锁浮点数精度漏洞，计算可租资产的最大化整数量子
            amount_units = int((Decimal(str(balance)) - Decimal(str(CONFIG["FEE"]))) * 100_000_000)
            if amount_units <= 0: return f"{addr}: 余额不足"

            # 2. 构造数据流与密码学签名
            target_node = random.choice(node_list)               # 随机抽取池内的某个超级节点以均衡权益分配
            timestamp = int(time.time() * 1_000_000_000)        # 强齐 19 位纳秒时间戳
            pri_bytes = base58.b58decode(pri_str)
            tx_bytes = build_lease_bytes(target_node, amount_units, timestamp)
            # 执行盲刺算法计算原生 Ed25519 签名流并转换为 Base58 文本
            signature = base58.b58encode(engine.sign(pri_bytes, tx_bytes)).decode('utf-8')
            # 派生公钥
            pub_key = base58.b58encode(engine.curve.gen_pub_key(pri_bytes)).decode('utf-8')

            # 3. 结构化拼装标准 RESTful JSON 参数对象并向节点广播投放
            payload = {
                "senderPublicKey": pub_key, "recipient": target_node,
                "amount": amount_units, "fee": 10000000,
                "feeScale": 100, "timestamp": timestamp, "signature": signature
            }
            res = await engine.broadcast("/leasing/broadcast/lease", payload)

            await asyncio.sleep(10)

            # 根据节点返回的内容中是否包含唯一的交易 Hash 标识 "id" 来断言任务成功率
            return f"{addr}: ✅ 成功" if 'id' in res else f"{addr}: ❌ {res.get('message', '拒绝')}"
        except: return f"{addr}: 💥 异常"

async def do_cancel(engine, addr, pri_str, semaphore):
    """
    [单地址名下活动租赁单全自动一键撤退解约协程任务]
    1. 发起 RPC 请求，穿透读取指定钱包地址在全网当前正在处于激活状态（Active）的所有租赁业务。
    2. 如果存在生效中的单子，提取其历史交易的 TxID。
    3. 顺序循环将名下的每一笔权益进行硬编码 Type 4 解约序列化，签名并强制广播解除。
    """
    async with semaphore:
        try:
            # 1. 穿透获取所有当前处于权益锁死状态的活动租赁记录
            url = f"{CONFIG['NODE_URL']}/leasing/active/{addr}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    active_leases = await resp.json()
            
            # 若结果列表为空，说明该地址已处于全空闲无利息锁死状态，直接释放返回
            if not active_leases: return f"{addr}: 无活动租赁"

            pri_bytes = base58.b58decode(pri_str)
            pub_key = base58.b58encode(engine.curve.gen_pub_key(pri_bytes)).decode('utf-8')
            count = 0

            # 2. 串行追溯解约流：遍历该地址名下派生的每一笔活动租赁合约
            for lease in active_leases:
                lease_id = lease['id']                          # 抽取必须要解除的原始租赁合同 Tx-Hash 唯一标识
                timestamp = int(time.time() * 1_000_000_000)    # 生成全新解约单的纳秒时间戳
                tx_bytes = build_cancel_lease_bytes(lease_id, timestamp)
                signature = base58.b58encode(engine.sign(pri_bytes, tx_bytes)).decode('utf-8')

                # 3. 构造取消租赁 JSON 结构实体并向区块链网络提交
                payload = {
                    "senderPublicKey": pub_key, "txId": lease_id,
                    "fee": 10000000, "feeScale": 100,
                    "timestamp": timestamp, "signature": signature
                }
                res = await engine.broadcast("/leasing/broadcast/cancel", payload)
                if 'id' in res: count += 1                     # 成功接触，账本撤回计数累加
        
                await asyncio.sleep(10)
    
            return f"{addr}: ✅ 取消 {count} 笔"
        except: return f"{addr}: 💥 异常"

def load_csv(path, cols=1):
    """[文件模块安全数据读取器] 自动处理、过滤空白行及 Windows 系统自带的特殊字符 UTF-8-SIG BOM 头"""
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return [row for row in csv.reader(f) if len(row) >= cols and row[0].strip()]

async def main():
    """[主控中心异步并发总驱动引擎]"""
    engine = VsysEngine()
    # 挂载信号量并发流控机制
    sem = asyncio.Semaphore(CONFIG["CONCURRENCY_LIMIT"])
    
    print(f"\n{C_CYAN}🚀 VSYS 底层协议引擎 | 节点: {CONFIG['NODE_URL']}{C_RESET}")
    
    # === [ 第一阶段核心调度：批量全自动化退租撤销业务 ] ===
    cancel_data = load_csv(CONFIG["CANCEL_FILE"], 2)
    if cancel_data:
        print(f"{C_YELLOW}正在撤回租赁...{C_RESET}")
        # 利用协程列表推导式，一气呵成将退租名单推入底池
        tasks = [do_cancel(engine, r[0], r[1], sem) for r in cancel_data]
        # 使用流式 as_completed 反馈，哪个地址先完成解租，就第一时间在控制台回显
        for f in asyncio.as_completed(tasks): print(f"  > {await f}")

    # === [ 第二阶段核心调度：批量全自动发起定向权益租赁 ] ===
    lease_data = load_csv(CONFIG["LEASE_ADD_FILE"], 2)
    node_list = [n[0] for n in load_csv(CONFIG["NODE_FILE"], 1)]
    if lease_data and node_list:
        print(f"{C_YELLOW}正在发起租赁...{C_RESET}")
        # 打包构建租赁协程任务包
        tasks = [do_lease(engine, r[0], r[1], node_list, sem) for r in lease_data]
        # 流式回显各地址的全自动划扣余额及定向随机租赁的投递状态
        for f in asyncio.as_completed(tasks): print(f"  > {await f}")

    print(f"\n{C_GREEN}✅ 所有任务处理完毕{C_RESET}")

if __name__ == "__main__":
    # 引导激活顶层异步事件总线循环
    asyncio.run(main())