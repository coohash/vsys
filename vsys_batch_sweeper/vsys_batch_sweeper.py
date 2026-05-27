# ====================================================
# FILE_START: vsys_batch_sweeper.py
#
# 【知识库归档说明 / 模块作用】
# 模块名称：VSYS 批量归集 (Sweep Engine)
# 核心作用：读取包含海量“地址+私钥”的 CSV 文件，自动查询所有钱包的链上实时余额。
#         若余额满足最低转账条件（>0.1 VSYS），将自动扣除固定的网络手续费，
#         将剩余的所有 VSYS 资金“一分不剩”地打包、签名，并汇聚转账至指定的【主钱包地址】。
# 架构特性：
#   1. 脱离 SDK 高层依赖，采用底层 Type 2 Payment Tx (大端序) 字节直接拼装，执行效率极高。
#   2. 内置 VsysCryptoEngine 模块，通过反射机制动态探测加密包路径，并使用双向盲刺签名，
#      完美免疫由于 py_vsys 官方库版本漂移导致的命名空间报错或参数倒置异常。
#   3. 包含“顽固重试”网络防卡死机制与并发信号量 (Semaphore) 限流，防止被节点拉黑。
#   4. 针对 Windows 系统具备日志死锁突破机制 (PermissionError 捕获)，确保资产数据零丢失。
# ====================================================

import asyncio
import aiohttp
import csv
import os
import time
import struct
import base58
from py_vsys import model as md

# =================================================================
# ⚙️ 全局配置参数 (核心配置区，可根据实际生产环境随时调整)
# =================================================================
CONFIG = {
    # 【节点配置】
    # VSYS 节点 API 地址 (当前为主网官方节点)。
    # 如果遇到该节点请求频率受限，可更换为自己搭建的全节点 IP 或其他公共节点 (如: http://wallet-node.v.systems:9922)。
    "NODE_URL": "https://vnode.vcoin.systems", 
    
    # 【资金流向配置】
    # 归集目标主钱包地址。所有从小号里面抽出来的钱，最终都会流入这个地址。
    # 架构师提醒：上线前务必再三核对该地址，一旦填错，资金无法追回。
    "TARGET_MAIN_ADDRESS": "ARRfwY4cJNJBBHjHxKm5YVbuUSPvvV2WdMR", 
    
    # 【文件与路径配置】
    # 输入文件：必须与脚本在同一目录下。
    # 文件格式要求：标准的 CSV 文本，每行格式为 "钱包地址,钱包私钥"，中间用英文逗号隔开，不要包含表头。
    "INPUT_FILE": "to-be-collected.csv",          
    
    # 输出日志文件：只有归集成功的记录才会写入这里。
    # 格式为 "来源地址,实际归集金额,交易哈希TxID"，方便后续对账。
    "LOG_FILE": "sweep_success_log.csv",      
    
    # 【性能与并发控制】
    # 异步并发限制：决定了系统同时向节点发起多少个查询/广播请求。
    # 调整建议：当前设置为 1（最保守、最稳定，不会被节点防御系统封禁 IP）。
    # 若在自建节点或内网节点上运行，且追求极限速度，可调高至 2-15。
    "CONCURRENCY_LIMIT": 1,                   
    
    # 【协议常量参数】(请勿改动)
    # 基础手续费：VSYS 网络一笔普通转账固定消耗 0.1 VSYS。
    # 系统底层精度为 Satoshi (1 VSYS = 10^8 Satoshi)，因此这里固定为 10,000,000。
    "FEE_SATOSHI": 10_000_000,
    
    # 手续费比例参数：VSYS 链底层协议固定要求传入 100。
    "FEE_SCALE": 100
}

# 🎨 赛博风格颜色控制终端 UI (用于输出带有颜色和进度条的直观日志)
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_RESET = "\033[0m"

# =================================================================
# 🛡️ 核心协议层与底包兼容适配引擎
# =================================================================
class VsysCryptoEngine:
    """
    处理 SDK 版本碎片化，动态映射加密算法。
    彻底解决在不同服务器、不同 Python 环境下 pip install py_vsys 后，
    因底层 curve_25519 模块路径不一致导致的 ImportError 崩溃。
    """
    def __init__(self):
        self.curve = None
        self.sign_func = None
        self._initialize()

    def _initialize(self):
        # 1. 动态包路径探测：使用反射(getattr)与异常捕获，逐级向下寻找加密模块
        try:
            curve_mod = getattr(md, 'curve', None)
            if not curve_mod:
                raise ImportError
            self.curve = curve_mod
        except Exception:
            try: 
                from py_vsys import curve
                self.curve = curve
            except ImportError: 
                import py_vsys.utils.crypto.curve_25519 as curve
                self.curve = curve
        
        # 2. 签名函数名自动收敛：不同版本的底层签名函数名不同，在此通过 dir() 遍历捕获
        available_methods = dir(self.curve)
        for name in ['sign', 'sign_data', 'get_signature', 'signature']:
            if name in available_methods:
                self.sign_func = getattr(self.curve, name)
                break
                
        if not self.sign_func:
            raise RuntimeError("无法在当前 SDK 版本中找到受支持的签名函数。")

    def safe_sign(self, pri_bytes, tx_bytes):
        """
        3. 签名参数顺序双向盲刺（核心防错）
        不同版本的 SDK，签名函数要求的入参顺序相反。
        不判断版本号，直接通过 try-except 试错，确保 100% 签名成功。
        """
        try:
            return self.sign_func(pri_bytes, tx_bytes)
        except Exception:
            return self.sign_func(tx_bytes, pri_bytes)

def build_sweep_payment_bytes(recipient, amount_sat, timestamp):
    """
    手动拼装 Type 2 支付协议底层字节序列。
    严格按照 VSYS 官方协议的大端序 (> 代表大端序) 拼接，抛弃高层 SDK 封装以提高稳定性。
    
    参数说明:
      recipient: 收款方地址 (String)
      amount_sat: 转账金额 (整型，Satoshi单位)
      timestamp: 19位纳秒级时间戳 (整型)
    """
    tx_type = struct.pack(">B", 2)                                 # 类型: 1字节
    time_bytes = struct.pack(">Q", timestamp)                      # 时间戳: 8字节
    amount_bytes = struct.pack(">Q", amount_sat)                   # 金额: 8字节
    fee_bytes = struct.pack(">Q", CONFIG["FEE_SATOSHI"])           # 手续费: 8字节
    scale_bytes = struct.pack(">H", CONFIG["FEE_SCALE"])           # 比例: 2字节
    rcp_bytes = base58.b58decode(recipient)                        # 接收方地址: 26字节(解码后)
    attach_len = struct.pack(">H", 0)                              # 附件长度: 归集无附件，固定 0
    
    return tx_type + time_bytes + amount_bytes + fee_bytes + scale_bytes + rcp_bytes + attach_len

# =================================================================
# 🏃 异步并发归集逻辑
# =================================================================
async def process_account_sweep(session, engine, source_addr, pri_key_str, semaphore):
    """
    处理单一地址的余额查询与全额归集核心逻辑。
    被包裹在异步信号量 (semaphore) 中以限制最大并发数。
    """
    async with semaphore:
        # 1. 顽固查询余额：使用 while True，遇到 502/超时 会无限等待 0.5 秒后重试
        balance_url = f"{CONFIG['NODE_URL']}/addresses/balance/{source_addr}"
        balance_sat = 0
        while True:
            try:
                async with session.get(balance_url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        balance_sat = data.get('balance', 0)
                        break
            except Exception:
                await asyncio.sleep(0.5) # 超时重试防拦截
                
        # 2. 判断是否有钱可归集：如果总余额连 0.1 的手续费都付不起，则直接跳过
        transfer_amount_sat = balance_sat - CONFIG["FEE_SATOSHI"]
        if transfer_amount_sat <= 0:
            return (source_addr, 0, "余额不足", None)

        # 3. 密码学准备：生成时间戳，解析公私钥，构建底层交易字节
        timestamp_nano = int(time.time() * 1_000_000_000)
        pri_bytes = base58.b58decode(pri_key_str)
        pub_bytes = engine.curve.gen_pub_key(pri_bytes)
        pub_str = base58.b58encode(pub_bytes).decode('utf-8')
        
        tx_bytes = build_sweep_payment_bytes(CONFIG["TARGET_MAIN_ADDRESS"], transfer_amount_sat, timestamp_nano)
        
        # 4. 执行双向盲刺签名 (将字节序列转为 Base58 字符串用于 JSON 提交)
        sig_bytes = engine.safe_sign(pri_bytes, tx_bytes)
        signature_str = base58.b58encode(sig_bytes).decode('utf-8')

        # 5. 拼装符合 VSYS 节点 API 规范的 JSON 广播报文
        payload = {
            "senderPublicKey": pub_str,
            "recipient": CONFIG["TARGET_MAIN_ADDRESS"],
            "amount": transfer_amount_sat,
            "fee": CONFIG["FEE_SATOSHI"],
            "feeScale": CONFIG["FEE_SCALE"],
            "timestamp": timestamp_nano,
            "attachment": "",
            "signature": signature_str
        }

        # 6. 广播交易并顽固重试：同样处理网络波动，直到节点给出明确回应
        broadcast_url = f"{CONFIG['NODE_URL']}/vsys/broadcast/payment"
        while True:
            try:
                async with session.post(broadcast_url, json=payload, timeout=5) as resp:
                    res_data = await resp.json()
                    if 'id' in res_data:
                        # 归集成功，返回转账量 (换算回 VSYS) 和 TxID
                        return (source_addr, transfer_amount_sat / 1e8, "成功", res_data['id'])
                    else:
                        # 节点明确拒绝 (例如签名错误等)
                        return (source_addr, 0, f"拒绝: {res_data.get('message', '未知')}", None)
            except Exception:
                await asyncio.sleep(0.5)

async def main():
    # 启动前检查配置文件是否存在
    if not os.path.exists(CONFIG["INPUT_FILE"]):
        print(f"{C_RED}❌ 错误: 找不到输入文件 {CONFIG['INPUT_FILE']}{C_RESET}")
        return

    print(f"\n{C_CYAN}🚀 VSYS 极限批量归集引擎启动 | 目标钱包: {CONFIG['TARGET_MAIN_ADDRESS']}{C_RESET}")
    print(f"{C_CYAN}{'='*70}{C_RESET}")

    # 实例化加密底层引擎，开始适配当前机器的 Python 环境
    crypto_engine = VsysCryptoEngine()

    # 内存加载任务文件，剔除空行和格式错误的数据
    tasks_data = []
    with open(CONFIG["INPUT_FILE"], 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                tasks_data.append((row[0].strip(), row[1].strip()))

    total = len(tasks_data)
    semaphore = asyncio.Semaphore(CONFIG["CONCURRENCY_LIMIT"])
    completed = 0
    success_records = []

    start_time = time.time()

    # 建立持久化 TCP 连接 (ClientSession) 以提高海量请求效率
    async with aiohttp.ClientSession() as session:
        # 并发派发所有归集任务
        tasks = [process_account_sweep(session, crypto_engine, addr, pri, semaphore) for addr, pri in tasks_data]
        
        # 实时监听完成的任务并更新 UI
        for future in asyncio.as_completed(tasks):
            addr, amount_vsys, status, tx_id = await future
            completed += 1
            
            # UI 实时 Cyber 进度反馈 (渲染进度条)
            percent = (completed / total) * 100
            bar = "█" * int(percent / 5) + "-" * (20 - int(percent / 5))
            
            color = C_GREEN if "成功" in status else C_MAGENTA
            print(f"\r{C_CYAN}[{bar}] {percent:>5.1f}% | {completed}/{total} | {addr[:6]}...{addr[-4:]} | {color}{status} {amount_vsys if amount_vsys > 0 else ''}{C_RESET}", end="", flush=True)
            
            # 记录成功上链的数据
            if tx_id:
                success_records.append((addr, amount_vsys, tx_id))

    print(f"\n\n{C_YELLOW}📦 正在执行日志安全落盘...{C_RESET}")
    
    # 核心特性：安全写文件机制。
    # 防止在 Windows 机器上用户用 Excel 强行打开了日志文件导致 Python 写入触发 PermissionError 崩溃。
    target_log_path = CONFIG["LOG_FILE"]
    if success_records:
        while True:
            try:
                # 使用追加模式 ('a')，防止覆盖之前的归集记录
                with open(target_log_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    for rec in success_records:
                        writer.writerow(rec)
                break # 写入成功则跳出死锁循环
            except PermissionError:
                # 若被占用，自动追加时间戳创建新文件，保全资金数据
                target_log_path = f"sweep_success_log_{int(time.time())}.csv"
                print(f"{C_RED}⚠️ 文件被占用，自动切换写入路径: {target_log_path}{C_RESET}")

    # 最终报告统计
    duration = time.time() - start_time
    print(f"{C_CYAN}{'='*70}{C_RESET}")
    print(f"{C_GREEN}✅ 归集任务完成！共成功处理: {len(success_records)} 笔交易。{C_RESET}")
    print(f"📊 扫描耗时: {duration:.2f} 秒 | 成功记录已追加至: {target_log_path}")
    print(f"{C_CYAN}{'='*70}{C_RESET}\n")

if __name__ == "__main__":
    # 配置底层系统异步兼容性处理
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 捕获 Ctrl+C，优雅退出而不抛出红字报错
        print(f"\n{C_RED}🛑 用户手动强行停止{C_RESET}")

# ====================================================
# FILE_END: vsys_batch_sweeper.py
# ====================================================
