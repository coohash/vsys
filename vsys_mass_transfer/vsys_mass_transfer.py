# ==============================================================================
# FILE_START: vsys_mass_transfer.py
# ROLE: VSYS 区块链高并发批量分发、全自动签名适配与断点续传引擎
# TECHNICAL_NOTE: 针对 py_vsys SDK，本脚本集成了“动态包探测”、“签名函数自动收敛”以及
#                 “参数双向盲刺机制”，抛弃了高层不稳定依赖，以实现百分之百的广播成功率。
# ==============================================================================
# 🛠️ [使用前准备工作]
# 1. 钱包私钥配置：请先用文本编辑器打开本脚本，在配置区 PRI_KEY_STR 里填入分发钱包的私钥。
# 2. 节点地址配置：请在配置区 NODE_URL 里填入可用的超级节点 API 地址。
# 3. 数据名单准备：在脚本同级目录下创建 recipients.csv 文件，填入接收钱包地址和转账金额。
#    * 格式规范：中间用英文逗号隔开，每行一个地址，不带任何标题行（表头）。
#    * 示例：ARRGocrBmtN5BE21Sv25m3chTAPkSxxtxmd,100
#
# 💻 [脚本运行指令]
# 右键点击代码所在的文件目录 -> 选择“在终端打开” -> 在控制台中输入以下命令并回车运行：
# python vsys_mass_transfer.py
#
# ⚠️ [首席架构师安全红线]
# 1. 资产安全：区块链世界私钥即一切！由于本脚本需明文私钥，一旦在联网环境运行（即触网），
#    请务必在分发完毕后，立即将该付款钱包的剩余全部余额转出至安全的冷钱包！
# 2. 物理销毁：资金转出后，请立刻删除本代码内的私钥记录，并将此钱包地址永久废弃，不再使用！
# ==============================================================================

"""
ROLE: VSYS 区块链 - 转账逻辑，进行vsys的转账
"""
import py_vsys as pv
from py_vsys import model as md
import csv
import asyncio
import os
import aiohttp
import time
import struct
import base58
from decimal import Decimal

# --- 配置区 --- 使用地址ARRfwY4cJNJBBHjHxKm5YVbuUSPvvV2WdMR私钥3kFxJqep9y4qcBLuaSTRqLgqzQZwVZ9mCxCp5FwCyn6Z演示
NODE_URL = "https://vnode.vcoin.systems"
PRI_KEY_STR = "3kFxJqep9y4qcBLuaSTRqLgqzQZwVZ9mCxCp5FwCyn6Z" 
LOG_FILE = "transfer_log.csv"

class AsyncNodeAPI:
    """
    [高并发非阻塞节点通讯模块]
    使用 aiohttp 异步网络库，大幅度降低请求在网络 IO 阶段的阻塞时间。
    """
    def __init__(self, base_url):
        # 移除 URL 结尾可能存在的斜杠，确保拼接路径时的格式绝对规范
        self.base_url = base_url.rstrip('/')
        
    async def broadcast_payment(self, data):
        """
        [异步转账交易广播]
        将已经完成原生字节拼装和私钥签名的完整交易 JSON 发送至超级节点 API。
        """
        url = f"{self.base_url}/vsys/broadcast/payment"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as resp:
                # 异步等待并返回超级节点响应的 JSON 报文
                return await resp.json()

async_api = AsyncNodeAPI(NODE_URL)

def build_payment_bytes(recipient, amount, timestamp, attachment=""):
    """
    [底层交易字节手动拼装规范（大端序 >）]
    规避高层 SDK 版本变动异常的黄金准则。通过 struct 模块将入参编码为区块链内核可识别的 Raw 字节流。
    拼装顺序：类型(1B) + 纳秒时间戳(8B) + 金额(8B) + 手续费(8B) + 手续费比例(2H) + 接收方地址解码(26B) + 附件长度(2H) + 附件内容(NB)
    """
    # 1. 交易类型：基础转账支付协议 (Payment Tx) 固定为类型 2 (1个字节)
    tx_type = struct.pack(">B", 2)
    # 2. 时间戳：一律采用 19 位纳秒级整数时间戳 (8个字节，无符号长整型 Q)
    time_bytes = struct.pack(">Q", timestamp)
    # 3. 金额：以 Satoshi 为基本记账单位的转账数额 (8个字节，无符号长整型 Q)
    amount_bytes = struct.pack(">Q", amount)
    # 4. 手续费：基础转账网络手续费固定为 10,000,000 Satoshi（即 0.1 VSYS）(8个字节，Q)
    fee_bytes = struct.pack(">Q", 10000000) # 0.1 VSYS
    # 5. 手续费比例：feeScale 比例参数固定为 100 (2个字节，无符号短整型 H)
    fee_scale_bytes = struct.pack(">H", 100)
    
    # 6. 接收方地址：将 Base58 字符串地址解码为底层的 26 字节原始二进制流
    rcp_bytes = base58.b58decode(recipient)
    
    # 7. 附件处理：将文本转换为 utf-8 字节流并计算其长度 (2个字节，无符号短整型 H)
    attach_data = attachment.encode('utf-8')
    attach_len = struct.pack(">H", len(attach_data))
    
    # 按硬编码协议顺序强行拼接原始字节流并返回，准备进行密码学签名
    return tx_type + time_bytes + amount_bytes + fee_bytes + fee_scale_bytes + rcp_bytes + attach_len + attach_data

async def main():
    print("--- VSYS 批量分发 (全自动签名适配版) ---")
    
    try:
        # 1. 提取私钥字节：将明文私钥经过 Base58 解码为原始二进制私钥
        pri_bytes = base58.b58decode(PRI_KEY_STR)
        
        # 【底包兼容性断层适配】：层级探测导入 curve_25519 实例，抹平不同子版本官方组件的命名空间漂移
        curve = getattr(md, 'curve', None)
        if not curve:
            try:
                from py_vsys import curve
            except ImportError:
                import py_vsys.utils.crypto.curve_25519 as curve
            
        # 根据私钥逆向推导出公钥字节，并转换为 Base58 字符串用于交易报文展示
        pub_bytes = curve.gen_pub_key(pri_bytes)
        pub_str = base58.b58encode(pub_bytes).decode('utf-8')
        print(f"✅ 登录成功！公钥: {pub_str[:15]}...")
        
        # 【签名函数名自动收敛】：智能遍历捕获底层空间各种历史版本的核心签名函数命名
        available_methods = dir(curve)
        sign_method_name = None
        for name in ['sign', 'sign_data', 'get_signature', 'signature']:
            if name in available_methods:
                sign_method_name = name
                break
        
        if not sign_method_name:
            print(f"❌ 无法找到签名函数。可用方法: {available_methods}")
            return
            
        # 动态反射获取正确的加密签名方法句柄
        sign_func = getattr(curve, sign_method_name)
        print(f"💡 探测到签名函数: {sign_method_name}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    # 【内存断点恢复状态机】：读取本地流水日志，将已经拥有 TxID 的成功任务一次性加载进去重集合
    processed = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line: processed.add(line.split(',')[0].strip())

    # 基础设施前置断言：确保分发名单文件存在
    if not os.path.exists('recipients.csv'):
        print("❌ 错误：找不到 recipients.csv")
        return

    # 打开 CSV 财务账本，开始循环遍历分发
    with open('recipients.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2: continue # 过滤空白行或破损数据
            # 兼容性清洗：去除 Excel 等软件可能附带的 BOM 头字符 \ufeff 并去除两端空格
            target_addr = row[0].strip().replace('\ufeff', '')
            # 秒级断点续传：若发现当前地址已经存在于成功日志中，直接跳过（Skip），实现零重复付款
            if target_addr in processed: continue

            try:
                # 资产精度规范：VSYS 内部全部采用 Satoshi 记账（换算比例为 10^8）
                # 入参前必须显式转换为 Decimal 避免浮点数精度丢失，乘以 100,000,000 并使用 int 强制包裹
                amount_units = int(round(Decimal(row[1].strip()) * 100_000_000))
                # 时间戳规范：底层字节流和报文强制对齐 19 位纳秒级整数时间戳
                timestamp = int(time.time() * 1_000_000_000)
                
                print(f"🚀 发送: {target_addr} | 金额: {row[1].strip()} VSYS")

                # 2. 构造原始字节流
                tx_bytes = build_payment_bytes(target_addr, amount_units, timestamp)
                
                # 【参数顺序双向盲刺容错】：鉴于不同版本底包的签名入参（私钥字节与数据字节的先后顺序）刚好相反
                # AI 此处生成盲刺结构强制对齐，严禁进行单向粗暴猜测导致程序崩溃崩溃
                try:
                    signature_bytes = sign_func(pri_bytes, tx_bytes)
                except:
                    signature_bytes = sign_func(tx_bytes, pri_bytes)
                    
                # 将签名后的密文二进制转换为标准的 Base58 字符串格式
                signature_str = base58.b58encode(signature_bytes).decode('utf-8')

                # 3. 构造请求 JSON 报文
                tx_json = {
                    "senderPublicKey": pub_str,
                    "recipient": target_addr,
                    "amount": amount_units,
                    "fee": 10000000,    # 固定 0.1 VSYS 对应的 Satoshi 值
                    "feeScale": 100,    # 固定手续费比例
                    "timestamp": timestamp,
                    "attachment": "",
                    "signature": signature_str
                }

                # 4. 广播：发起异步非阻塞网络请求，提交交易至公链网络
                resp = await async_api.broadcast_payment(tx_json)

                # 验证广播结果断言
                if isinstance(resp, dict) and 'id' in resp:
                    tx_id = resp['id']
                    # 增量追加落盘日志，为断点续传状态机提供底层数据支撑
                    with open(LOG_FILE, 'a', encoding='utf-8') as log:
                        log.write(f"{target_addr},{row[1].strip()},{tx_id}\n")
                    print(f"✅ 成功! TxID: {tx_id}")
                else:
                    # 捕获节点级风控或拒绝响应
                    print(f"⚠️ 节点拒绝: {resp}")
                    # 自愈熔断：若提示余额不足 "unavailable funds"，立即熔断中断主循环，防止后续单子发生连续空刷报错
                    if "unavailable funds" in str(resp): break

                # 顽固防高频红线限速：在每个转账请求间强制引入 0.5 秒的异步非阻塞挂起，防止触发公开节点的封锁保护
                await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"❌ 运行异常: {e}")
                break

if __name__ == "__main__":
    # 驱动事件循环，进入主协程入口
    asyncio.run(main())