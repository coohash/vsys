# ==============================================================================
# FILE_START: vsys_volume_booster.py
# ROLE: VSYS 公链生态流动性多层级全自动激活与成交量（Volume）深度模拟
# SYSTEM_ARCH: 本引擎采用 L0总金库 -> 中转大户站 -> 散户独立地址的三层递进式资金拓扑流。
#              1. 分发阶段：中转站随机抽取独立地址，执行 2-8 位随机精度的分散式资金划拨。
#              2. 自愈阶段：当中转站水位干涸，自动向上触发 L0 总金库的差额整型补给，直至金库耗尽。
#              3. 归集阶段：当独立散户地址的资产超出水位线，自动触发随机长尾残留回收至中转大户。
#              4. 永续阶段：总金库枯竭后，中转站与独立地址群自动进入内循环闭环“分发-归集-再分发”。
# ==============================================================================
# 📊 [生态网络规模建议 & 配置区参数精细化调优（以 100 万 VSYS 为基准）]
# 1. 规模配比：总金库初始配配 1,000,000 VSYS 资产时，建议中转站地址 < 500 个，独立地址 < 10000 个。
#     使用前请先参照10000_VSYS_Address.txt 里的方法批量生成1万的VSYS地址和私钥，并确保addresses.csv已经保存到离线U盘后再继续。
#     用记事本编辑中转站 translate_midd.csv文件，放入500个地址+私钥，格式一行一个，地址,私钥，没有标题，注意中间用逗号隔开
#     用记事本编辑独立地址 add_priv.csv文件放入10000个地址+私钥
#     
# 2. 参数微调建议 (根据 Config 类字段对齐修改)：
#    * TX_MIN & TX_MAX (中转分发散户)：建议设为 30.0 至 1500.0 之间。
#    * REFILL_MIN & REFILL_CAP (金库给中转站补给)：建议设为 500 至 6000。保证中转大户有充足资金。
#    * COLLECT_THRESHOLD (散户归集起征点)：必须严格大于“随机残留上限(500) + 矿工费(0.1)”，建议设为 600.0+。
#    * 速率微调 (run 函数内 sleep)：每次转账需消耗0.1VSYS，若想减少频率，可将 `await asyncio.sleep(random.randint(2, 13))`
#      缩短为 `await asyncio.sleep(random.uniform(20, 130))`（提示：2-13秒，每天约进行1万次转账，消耗1000VSYS）。
#
# 🛡️ [私钥安全与长效归集隔离红线]
# 1. 物理隔离：translate_midd.csv(中转站) 与 add_priv.csv(独立地址) 内包含明文地址与私钥。
# 2. 善后锁死：脚本不运行时，必须将上述两个 CSV 文件彻底剪切移动至离线安全 U 盘中，并在联网服务器上粉碎删除。
# 3. 永续价值：由于散户地址内会随机残留 “设定的” VSYS 沉淀资产，上述私钥账本(包含addresses.csv)是未来收回这笔沉淀的唯一凭证！
#
# 💻 [前台高亮长效运行方案（本地 PC 临时测试）]
# 提示：本代码需 7×24 小时长时间不间断轮询，本地前台运行时绝对不可关闭终端窗口，不可让电脑进入休眠或断网状态。
# cd /www/wwwroot/vsys_volume_booster
# python vsys_volume_booster.py
#
# 🐧 [Linux 服务器/VPS 后台静默长效长跑部署指南（推荐）]
# 建议将脚本部署于纯净、无第三方插件污染的 Linux VPS 或者是安全的宝塔环境隔离目录下静默永续运行。
#
# 1. 进入生产工作目录
#    cd /www/wwwroot/vsys_volume_booster
# 2. 启动后台静默守护进程（屏蔽挂断信号，输出重定向至 vsys_run.log）
#    nohup python3.9 vsys_volume_booster.py > vsys_run.log 2>&1 &
# 3. 实时追踪链上广播流水日志
#    tail -f vsys_run.log
#
# 🛑 [静默守护进程安全切断与关闭指令]
# 1. 查看守护进程的真实 PID 序列号与具体启动时间
#    ps -ef | grep vsys_volume_booster.py
# 2. 强行终止该进程（假设查出来的 PID 进程号是 2661514）
#    kill -9 2661514
# 3. 再次复检进程是否彻底被物理清除
#    ps -ef | grep vsys_volume_booster.py
#
# 🧹 [Linux 磁盘文件系统维护（日志清理与 Crontab 零点自动截断）]
# 1. 手动瞬间排空并清零当前日志
#    > /www/wwwroot/vsys_monitor/vsys_run.log
# 2. 挂载系统级自动化定时任务（每隔 3 天的凌晨 0 点，自动触发一次物理截断清空）
#    执行下面这条组合指令，可自动在系统的 crontab 表中追加并注入清理计划：
#    (crontab -l 2>/dev/null; echo "0 0 */3 * * > /www/wwwroot/vsys_monitor/vsys_run.log") | crontab -
# ==============================================================================
# -*- coding: utf-8 -*-
"""
文件名称: vsys_volume_booster.py
功能描述: VSYS 100万量级链上活跃度引擎 (平衡版)
更新说明:
1. 分发随机性：分发金额的小数点位数为 2 至 8 位随机。
2. 归集残留优化：归集不会“全额扫尾”，而是随机在地址留下配置的数量 VSYS。
3. 精度处理：引入 Decimal 确保 8 位小数下的 Satoshi 转换零误差。
"""

import asyncio
import time
import struct
import base58
import random
import datetime
import sys
import traceback
import requests
import pandas as pd
from decimal import Decimal, getcontext

# 设置高精度计算环境：全局锁死 20 位有效数字精度，全面阻断金融级算力中产生的任何微小浮点数溢出
getcontext().prec = 20

# ==========================================
# 1. 基础依赖与签名兼容
# ==========================================
try:
    # 动态向下兼容：首选导入官方顶层空间的加密模块实例
    from py_vsys import curve
except ImportError:
    try:
        # 兜底探测：若顶层命名空间缺失，强行穿透至底层底层相对路径加载核心 Curve25519 组件
        import py_vsys.utils.crypto.curve_25519 as curve
    except ImportError:
        print("❌ 错误：未检测到 py_vsys 库。请执行：pip3.9 install py_vsys")
        sys.exit(1)

# 【核心签名函数自适应】：动态扫描当前环境中导入的库，自动绑定正确的私钥签名导出句柄名称
sign_f = next((getattr(curve, m) for m in ['sign', 'sign_data', 'signature'] if hasattr(curve, m)), None)

# ==========================================
# 2. 核心配置区（包含可深度调优的风控参数）
# ==========================================
class Config:
    """
    [全自动化链上模拟环境控制器]
    通过调节以下各阈值，可完美模拟不同规模的散户链上交互生态网络。
    """
    # 目标链上数据通信节点：可切换为自建高速 RPC 超级节点以应对百万级并发压力
    NODE_URL = "http://wallet-node.v.systems:9922"
    
    # --- 资金账户 (L0 级别：总金库) ---
    # 作用：整个生态圈的源头水库。当“中转站”内资金耗尽时，以此钱包作为燃料发起自动化弹药补给。
    # --- 使用地址ARRfwY4cJNJBBHjHxKm5YVbuUSPvvV2WdMR私钥3kFxJqep9y4qcBLuaSTRqLgqzQZwVZ9mCxCp5FwCyn6Z演示 ---
    L0_ADDRESS = "ARRfwY4cJNJBBHjHxKm5YVbuUSPvvV2WdMR" 
    L0_PRIV = "3kFxJqep9y4qcBLuaSTRqLgqzQZwVZ9mCxCp5FwCyn6Z"
    
    # --- 金额配置 (中转站 -> 普通用户) ---
    # 作用：模拟单笔正常用户链上转账的金额区间。
    # 调优建议：区间拉大、非整数组合，可以让链上浏览器中的 Tx 历史流水显得极其真实。
    TX_MIN = 600.0      # 【可调】单笔转账的最小下限（单位：VSYS）
    TX_MAX = 3600.0     # 【可调】单笔转账的最大上限（单位：VSYS）
    
    # --- 补给配置 (L0 金库 -> 中转站) ---
    # 作用：用于防止中转站干涸的熔断防守线。
    # 触发时机：当中转站余额低于 `TX_MIN + 0.1` 时，L0 总金库会自动向该中转站发起整型补给。
    REFILL_MIN = 3600   # 【可调】单次自动补给的最小下限（单位：VSYS，必须是整数型）
    REFILL_CAP = 6000   # 【可调】单次自动补给的最大上限限制（单位：VSYS，必须是整数型）
    
    # --- 归集配置 (普通用户 -> 中转站) ---
    # 作用：回收散落在普通用户（add_priv.csv）口袋里的流动性资产。
    # 触发红线：只有普通用户的钱包可用余额超过此阈值，系统才会摇号选中它并执行“归集回收”。
    # 调优注意：该数值必须大于下方“随机残留(300.0-500.0)”的最大上限加上手续费，否则计算出的转账金额会小于等于零。
    COLLECT_THRESHOLD = 600.0 
    
    # 协议级摩擦成本：当前 VSYS 区块链上基础转账（Type 2）的标准矿工费（固定为 10,000,000 Satoshi，即 0.1 VSYS）
    FEE_SAT = 10_000_000 # 0.1 VSYS 手续费

# ==========================================
# 3. 核心引擎
# ==========================================
class VsysEngine:
    def __init__(self):
        # 初始化持久化 HTTP 连接池，复用 TCP 通道，极大提升高并发扫描节点的速度
        self.session = requests.Session()
        self.session.trust_env = False # 屏蔽系统局部代理干扰，防止因科学上网环境导致报错崩溃
        
        print(f"🛰️  VSYS 100万量级引擎启动 (随机残留)...")
        try:
            # 自动加载外部静态账户数据池
            # 用户池：用来充当接收资金和存放残留资金的大量“独立持币散户”角色
            df_u = pd.read_csv('add_priv.csv', header=None)
            self.users = {str(r[0]): str(r[1]) for _, r in df_u.iterrows()}
            
            # 中转站池：用来充当流动性中盘的大户，主要负责接收大宗补给并高频向下拆分分发
            df_t = pd.read_csv('translate_midd.csv', header=None)
            self.transits = {str(r[0]): str(r[1]) for _, r in df_t.iterrows()}
            
            print(f"📊 已加载用户: {len(self.users)} | 中转站: {len(self.transits)}")
        except Exception as e:
            print(f"❌ 数据文件加载失败: {e}")
            sys.exit(1)

        # 全局计数看板状态机：实时统计自脚本运行以来，成功的 Tx 链上交互和失败的异常频次
        self.stats = {"ok": 0, "err": 0}

    def get_bal_sat(self, addr):
        """[RPC 链上可用余额实时穿透获取] 返回原始无缩放的最小颗粒度 Satoshi 整数余额"""
        try:
            r = self.session.get(f"{Config.NODE_URL}/addresses/balance/{addr}", timeout=5)
            return r.json().get('balance', 0)
        except: 
            return 0

    def broadcast_payment(self, from_addr, to_addr, amt_sat, priv_str):
        """
        [Type 2 原生基础交易拼接、本地签名与远程广播闭环]
        严格遵守官方规范的大端序（>）二进制序列化，私钥离线运算生成密文并推送。
        """
        try:
            ts = int(time.time() * 1_000_000_000) # 生成强制对齐的 19 位纳秒级全网时间戳
            pri_bytes = base58.b58decode(priv_str)
            # 大端序拼接：类型(2)+时间戳(8B)+转账量(8B)+手续费(8B)+费率比(2H)+地址解密流(26B)+附件长度(2H,0代表空)
            tx_bytes = struct.pack(">B", 2) + struct.pack(">Q", ts) + \
                       struct.pack(">Q", amt_sat) + struct.pack(">Q", Config.FEE_SAT) + \
                       struct.pack(">H", 100) + base58.b58decode(to_addr) + struct.pack(">H", 0)
            
            # 盲刺算法：自适应对齐底包的入参物理拓扑，完美算出密文签名流
            sig = sign_f(tx_bytes, pri_bytes) if sign_f.__name__ == 'signature' else sign_f(pri_bytes, tx_bytes)
            pub_key = base58.b58encode(curve.gen_pub_key(pri_bytes)).decode()
            
            # 拼装成符合超级节点接收格式的标准 JSON 载荷
            payload = {
                "senderPublicKey": pub_key, "recipient": to_addr, "amount": amt_sat,
                "fee": Config.FEE_SAT, "feeScale": 100, "timestamp": ts, "signature": base58.b58encode(sig).decode()
            }
            res = self.session.post(f"{Config.NODE_URL}/vsys/broadcast/payment", json=payload, timeout=5).json()
            return res.get('id') # 如果成功，将返回独一无二的 32 字节哈希 TxID；否则返回 None
        except: 
            return None

    def display_log(self, tag, msg, success=True):
        """[终端可视化日志流水审计台] 采用标准单行无损缓冲覆写，并实时动态累计任务状态数"""
        t = datetime.datetime.now().strftime('%H:%M:%S')
        status = "✅ 成功" if success else "❌ 失败"
        if success: self.stats["ok"] += 1
        else: self.stats["err"] += 1
        print(f"[{t}] | {tag:4} | {msg:<45} | {status}")

    async def step(self):
        """
        [生态多层级动态行为状态机决策环]
        使用概率学随机数，实现 80% 概率进行随机多精度资金拆分分发（包含自愈补给逻辑），
        20% 概率进行长尾保留式资金归集。在链上完美伪装成多散户群体的复杂博弈形态。
        """
        action = random.random()

        if action < 0.8:
            # ==========================================
            # 核心分支 A: 模拟日常交易大面积拆分子项分发 (中转站 -> 散户)
            # ==========================================
            src_addr = random.choice(list(self.transits.keys()))
            src_bal_vsys = self.get_bal_sat(src_addr) / 1e8 # 当前中转大户的资产总计（个）
            
            # 判断中转站弹药是否充沛
            if src_bal_vsys > (Config.TX_MIN + 0.1):
                dst_addr = random.choice(list(self.users.keys()))
                max_allow = min(Config.TX_MAX, src_bal_vsys - 0.1)
                
                # 【专业随机优化 1】：金额精度不再固定，在 2 到 8 位小数之间进行极具欺骗性的无序漂移
                precision = random.randint(2, 8) 
                amt_val = round(random.uniform(Config.TX_MIN, max_allow), precision)
                # 使用 Decimal 高精算子将其乘以 10^8 转换为链上可读的 Satoshi 整型数
                amt_sat = int(Decimal(str(amt_val)) * Decimal('100000000'))
                
                tx_id = self.broadcast_payment(src_addr, dst_addr, amt_sat, self.transits[src_addr])
                if tx_id:
                    self.display_log("分发", f"{src_addr[:4]}... -> {dst_addr[:4]}... | {amt_val} VSYS", True)
                    return True
            else:
                # ==========================================
                # 核心分支 A-2: 弹药告急，自动激活上层水源自愈（L0总金库 -> 中转站）
                # ==========================================
                l0_bal_vsys = self.get_bal_sat(Config.L0_ADDRESS) / 1e8
                if l0_bal_vsys > Config.REFILL_MIN:
                    fill_limit = min(Config.REFILL_CAP, int(l0_bal_vsys - 1))
                    amt_val = random.randint(Config.REFILL_MIN, fill_limit) # 产生整数型资产补给量
                    tx_id = self.broadcast_payment(Config.L0_ADDRESS, src_addr, int(amt_val * 1e8), Config.L0_PRIV)
                    if tx_id:
                        self.display_log("补给", f"L0 -> {src_addr[:4]}... | {amt_val} VSYS", True)
                        return True
            return False

        else:
            # ==========================================
            # 核心分支 B: 散户钱包长尾资金随机残留回收 (散户 -> 中转站)
            # ==========================================
            u_addr = random.choice(list(self.users.keys()))
            u_bal_sat = self.get_bal_sat(u_addr)
            u_bal_vsys = u_bal_sat / 1e8

            # 判断当前散户兜里的钱是否达到了起征回收的警戒线
            if u_bal_vsys >= Config.COLLECT_THRESHOLD:
                target_transit = random.choice(list(self.transits.keys()))
                
                # 【专业随机优化 2】：彻底规避“全额扫尾归零”引发的链上风控监控。
                # 随机决定在当前普通用户的钱包里留下 300.0 至 500.0 枚不等的 VSYS 作为持币沉淀，
                # 同时残留量的小数位数也采用 2 到 6 位随机，完美贴合真实持币用户的钱包余额生态现状。
                keep_precision = random.randint(2, 6) 
                keep_val = round(random.uniform(300.0, 500.0), keep_precision)
                keep_sat = int(Decimal(str(keep_val)) * Decimal('100000000'))
                
                # 严格扣减财务公式：实际提走归集的资金 = 总额 - 长尾故意残留数 - 矿工费
                collect_amt_sat = u_bal_sat - keep_sat - Config.FEE_SAT
                
                if collect_amt_sat > 0:
                    tx_id = self.broadcast_payment(u_addr, target_transit, collect_amt_sat, self.users[u_addr])
                    if tx_id:
                        actual_vsys = collect_amt_sat / 1e8
                        self.display_log("归集", f"{u_addr[:4]}... -> {target_transit[:4]}... | {actual_vsys:.8f} VSYS (保留{keep_val})", True)
                        return True
            return False

    async def run(self):
        """[全自动化无限循环异步运转引擎]"""
        print("-" * 90)
        print(f"{'时间':^8} | {'动作':^4} | {'详细描述':^45} | {'结果':^10}")
        print("-" * 90)
        while True:
            try:
                action_taken = await self.step()
                # 【可配置延迟调整点】：当成功向公链成功广播了一笔交易流水之后
                # 在这里（2到13秒之间随机休眠）控制你的整体流水刷新步调。
                # 调优建议：如果节点性能好且想冲量，可将此行改为 `await asyncio.sleep(random.uniform(0.1, 1.0))`
                if action_taken:
                    await asyncio.sleep(random.randint(2, 13)) 
                else:
                    # 如果本轮由于判定余额不够而未触发任何转账，极速休眠 0.8 秒后快速切换至下一个随机账户检测
                    await asyncio.sleep(0.8) 
            except Exception as e:
                # 遇到非致命的外部物理异常（如临时断网、节点接口报错拒绝连接），拦截报错并退防 5 秒，防止程序死亡
                self.display_log("异常", f"系统错误: {str(e)[:40]}", False)
                await asyncio.sleep(5)

if __name__ == "__main__":
    engine = VsysEngine()
    try:
        # 激活顶级异步循环守护线程
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        # 当用户在控制台按下 Ctrl+C 强制叫停引擎时，精准结算并输出本轮会话的完整财务流水账单审计报告
        print(f"\n👋 [停止] 成功: {engine.stats['ok']} | 失败: {engine.stats['err']}")
