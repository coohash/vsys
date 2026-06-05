import asyncio
import aiohttp
import csv
import os
import time
import struct
import base58
from py_vsys import model as md

# =================================================================
# ⚙️ 配置中心
# =================================================================
CONFIG = {
    "NODE_URL": "https://vnode.vcoin.systems",
    "CSV_FILE": "cancel_lease.csv", 
    "FETCH_LIMIT": 1000, # 增加上限以防自动化交易挤压
}

C_CYAN, C_GREEN, C_YELLOW, C_RED, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"

# =================================================================
# 🛡️ 协议层：字节码构建
# =================================================================
def build_cancel_bytes(lease_id, timestamp):
    tx_type = struct.pack(">B", 4)
    fee = struct.pack(">Q", 10000000) # 0.1 VSYS
    scale = struct.pack(">H", 100)
    time_bytes = struct.pack(">Q", timestamp)
    return tx_type + fee + scale + time_bytes + base58.b58decode(lease_id)

def get_curve():
    try:
        curve = getattr(md, 'curve', None)
        if not curve: import py_vsys.utils.crypto.curve_25519 as curve
        return curve
    except: return None

# =================================================================
# 🏃 执行逻辑：无脑提取 + 强制注销 (忽略状态)
# =================================================================
async def force_cancel_all(session, curve, addr, pri_str):
    try:
        # 1. 直接获取 Type 3 专用列表
        query_url = f"{CONFIG['NODE_URL']}/transactions/list?address={addr}&txType=3&limit={CONFIG['FETCH_LIMIT']}&offset=0"
        
        raw_ids = []
        async with session.get(query_url, timeout=20) as r:
            if r.status != 200:
                return f"{addr[:8]}... | {C_RED}链接失效 (HTTP {r.status}){C_RESET}"
            
            data = await r.json()
            # 兼容截图中的 transactions 嵌套结构
            tx_list = data.get('transactions', []) if isinstance(data, dict) else []
            
            # 提取所有 Type 3 ID，不做任何 status 或 sender 过滤
            raw_ids = [t['id'] for t in tx_list if 'id' in t]

        if not raw_ids:
            return f"{addr[:8]}... | {C_YELLOW}未返回任何 Type 3 记录{C_RESET}"

        # 2. 签名环境
        pri_b = base58.b58decode(pri_str)
        pub_s = base58.b58encode(curve.gen_pub_key(pri_b)).decode('utf-8')
        success, failed = 0, 0
        
        # 3. 强制广播所有抓到的 ID
        for lid in set(raw_ids):
            ts = int(time.time() * 1_000_000_000)
            tx_b = build_cancel_bytes(lid, ts)
            
            try: sig = curve.sign(pri_b, tx_b)
            except: sig = curve.sign(tx_b, pri_b)
            
            payload = {
                "senderPublicKey": pub_s, "txId": lid, "fee": 10000000,
                "feeScale": 100, "timestamp": ts,
                "signature": base58.b58encode(sig).decode('utf-8')
            }
            
            async with session.post(f"{CONFIG['NODE_URL']}/leasing/broadcast/cancel", json=payload) as pr:
                if pr.status == 200:
                    success += 1
                else:
                    # 已注销的会报 State check failed，这在预期内
                    failed += 1
            
            await asyncio.sleep(0.05)

        return f"{addr[:8]}... | {C_CYAN}发现 {len(raw_ids)} 条记录 | {C_GREEN}广播成功: {success}{C_RESET} | {C_YELLOW}拒绝/已注销: {failed}{C_RESET}"

    except Exception as e:
        return f"{addr[:8]}... | {C_RED}运行报错: {str(e)}{C_RESET}"

async def main():
    curve = get_curve()
    print(f"\n{C_CYAN}🚀 VSYS 全量强制撤回工具 V7.0 | 模式：忽略状态判断{C_RESET}\n")

    if not os.path.exists(CONFIG["CSV_FILE"]):
        print(f"错误: 找不到 {CONFIG['CSV_FILE']}")
        return

    async with aiohttp.ClientSession() as session:
        with open(CONFIG["CSV_FILE"], 'r', encoding='utf-8-sig') as f:
            rows = [r for r in csv.reader(f) if len(r) >= 2 and r[0].strip()]
        
        print(f"📋 待扫地址: {len(rows)} 个\n")
        for r in rows:
            print(await force_cancel_all(session, curve, r[0], r[1]))
            await asyncio.sleep(0.02)

if __name__ == "__main__":
    asyncio.run(main())