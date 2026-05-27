# ====================================================
# FILE_START: vsys_batch_sweeper.py
# DESCRIPTION: VSYS 批量归集引擎。从指定 CSV 文件中读取海量钱包（地址,私钥），
# 检测其余额，并扣除固定手续费后将剩余金额全额打包、底层签名并广播至目标主钱包。
# 包含自动规避 SDK 断层、网络防卡死以及并发限流机制。
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
# ⚙️ 全局配置参数 (详细中文注释)
# =================================================================
CONFIG = {
    # VSYS 节点 API 地址 (主网)
    "NODE_URL": "https://vnode.vcoin.systems", 
    
    # 【请在此处填写你的归集目标主钱包地址】
    "TARGET_MAIN_ADDRESS": "AR2gQJnRkCasj8vanJH2KZj9ZZU3i93ydU9", 
    
    # 输入文件：格式为 "地址,私钥"，无表头
    "INPUT_FILE": "to-be-collected.csv",          
    
    # 输出日志文件：记录成功归集的源地址、归集金额和 TxID
    "LOG_FILE": "sweep_success_log.csv",      
    
    # 并发限制：建议设置在 1-15 之间
    "CONCURRENCY_LIMIT": 1,                   
    
    # 基础手续费：VSYS 网络固定 0.1 VSYS (精度 10^8)
    "FEE_SATOSHI": 10_000_000,
    
    # 手续费比例参数
    "FEE_SCALE": 100
}

# 🎨 赛博风格颜色控制终端 UI
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
    """处理 SDK 版本碎片化，动态映射加密算法"""
    def __init__(self):
        self.curve = None
        self.sign_func = None
        self._initialize()

    def _initialize(self):
        # 1. 动态包路径探测
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
        
        # 2. 签名函数名自动收敛
        available_methods = dir(self.curve)
        for name in ['sign', 'sign_data', 'get_signature', 'signature']:
            if name in available_methods:
                self.sign_func = getattr(self.curve, name)
                break
                
        if not self.sign_func:
            raise RuntimeError("无法在当前 SDK 版本中找到受支持的签名函数。")

    def safe_sign(self, pri_bytes, tx_bytes):
        """3. 签名参数顺序双向盲刺（核心防错）"""
        try:
            return self.sign_func(pri_bytes, tx_bytes)
        except Exception:
            return self.sign_func(tx_bytes, pri_bytes)

def build_sweep_payment_bytes(recipient, amount_sat, timestamp):
    """
    手动拼装 Type 2 支付协议底层字节序列 (大端序)
    拼装规则: 类型(1B) + 时间戳(8B) + 金额(8B) + 手续费(8B) + 比例(2H) + 地址解码(26B) + 附件长度(2H)
    """
    tx_type = struct.pack(">B", 2)
    time_bytes = struct.pack(">Q", timestamp)
    amount_bytes = struct.pack(">Q", amount_sat)
    fee_bytes = struct.pack(">Q", CONFIG["FEE_SATOSHI"])
    scale_bytes = struct.pack(">H", CONFIG["FEE_SCALE"])
    rcp_bytes = base58.b58decode(recipient)
    attach_len = struct.pack(">H", 0) # 归集无需附加信息，填 0
    
    return tx_type + time_bytes + amount_bytes + fee_bytes + scale_bytes + rcp_bytes + attach_len

# =================================================================
# 🏃 异步并发归集逻辑
# =================================================================
async def process_account_sweep(session, engine, source_addr, pri_key_str, semaphore):
    """处理单一地址的余额查询与全额归集"""
    async with semaphore:
        # 1. 顽固查询余额
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
                
        # 2. 判断是否有钱可归集 (余额需大于固定手续费)
        transfer_amount_sat = balance_sat - CONFIG["FEE_SATOSHI"]
        if transfer_amount_sat <= 0:
            return (source_addr, 0, "余额不足", None)

        # 3. 构建底层交易字节与公私钥解码
        timestamp_nano = int(time.time() * 1_000_000_000)
        pri_bytes = base58.b58decode(pri_key_str)
        pub_bytes = engine.curve.gen_pub_key(pri_bytes)
        pub_str = base58.b58encode(pub_bytes).decode('utf-8')
        
        tx_bytes = build_sweep_payment_bytes(CONFIG["TARGET_MAIN_ADDRESS"], transfer_amount_sat, timestamp_nano)
        
        # 4. 执行双向盲刺签名
        sig_bytes = engine.safe_sign(pri_bytes, tx_bytes)
        signature_str = base58.b58encode(sig_bytes).decode('utf-8')

        # 5. 拼装广播报文
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

        # 6. 广播交易并顽固重试
        broadcast_url = f"{CONFIG['NODE_URL']}/vsys/broadcast/payment"
        while True:
            try:
                async with session.post(broadcast_url, json=payload, timeout=5) as resp:
                    res_data = await resp.json()
                    if 'id' in res_data:
                        # 归集成功，返回 TxID
                        return (source_addr, transfer_amount_sat / 1e8, "成功", res_data['id'])
                    else:
                        # 节点明确拒绝
                        return (source_addr, 0, f"拒绝: {res_data.get('message', '未知')}", None)
            except Exception:
                await asyncio.sleep(0.5)


async def main():
    if not os.path.exists(CONFIG["INPUT_FILE"]):
        print(f"{C_RED}❌ 错误: 找不到输入文件 {CONFIG['INPUT_FILE']}{C_RESET}")
        return

    print(f"\n{C_CYAN}🚀 VSYS 极限批量归集引擎启动 | 目标钱包: {CONFIG['TARGET_MAIN_ADDRESS']}{C_RESET}")
    print(f"{C_CYAN}{'='*70}{C_RESET}")

    # 初始化加密底层引擎
    crypto_engine = VsysCryptoEngine()

    # 加载任务文件
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

    async with aiohttp.ClientSession() as session:
        tasks = [process_account_sweep(session, crypto_engine, addr, pri, semaphore) for addr, pri in tasks_data]
        
        for future in asyncio.as_completed(tasks):
            addr, amount_vsys, status, tx_id = await future
            completed += 1
            
            # UI 实时 Cyber 进度反馈
            percent = (completed / total) * 100
            bar = "█" * int(percent / 5) + "-" * (20 - int(percent / 5))
            
            color = C_GREEN if "成功" in status else C_MAGENTA
            print(f"\r{C_CYAN}[{bar}] {percent:>5.1f}% | {completed}/{total} | {addr[:6]}...{addr[-4:]} | {color}{status} {amount_vsys if amount_vsys > 0 else ''}{C_RESET}", end="", flush=True)
            
            if tx_id:
                success_records.append((addr, amount_vsys, tx_id))

    print(f"\n\n{C_YELLOW}📦 正在执行日志安全落盘...{C_RESET}")
    
    # 安全写文件机制（防 Windows 文件占用导致的 PermissionError 崩溃）
    target_log_path = CONFIG["LOG_FILE"]
    if success_records:
        while True:
            try:
                with open(target_log_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    for rec in success_records:
                        writer.writerow(rec)
                break
            except PermissionError:
                target_log_path = f"sweep_success_log_{int(time.time())}.csv"
                print(f"{C_RED}⚠️ 文件被占用，自动切换写入路径: {target_log_path}{C_RESET}")

    duration = time.time() - start_time
    print(f"{C_CYAN}{'='*70}{C_RESET}")
    print(f"{C_GREEN}✅ 归集任务完成！共成功处理: {len(success_records)} 笔交易。{C_RESET}")
    print(f"📊 扫描耗时: {duration:.2f} 秒 | 成功记录已追加至: {target_log_path}")
    print(f"{C_CYAN}{'='*70}{C_RESET}\n")


if __name__ == "__main__":
    # 配置底层系统兼容性处理
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C_RED}🛑 用户手动强行停止{C_RESET}")

# ====================================================
# FILE_END: vsys_batch_sweeper.py
# ====================================================