# ==============================================================================
# FILE_START: vanity_generator.py
# 配置区在代码最后，请按需求配置后运行 `python vanity_generator.py` 启动。
# 
# DESCRIPTION: VSYS 区块链靓号地址（Vanity Address）高性能全自动碰撞与生成引擎
# TECHNICAL_NOTE: 脚本通过 Subprocess 动态管道驱动底层的 Java 密算包，结合预编译正则表达式，
# 在 CPU 物理层实施大规模地址过滤与清洗，支持自定义前后缀及尾部纯数字锁定。
# 
# 💡 靓号碰撞预估耗时与多进程多开极速榨干指南
# 在单台常规 8 核电脑（单进程速度约 20 K/s）下，靓号碰撞的预估耗时如下：
# * 【6位数字尾号】（如：...123456）：约需 15 分钟 至 1 小时。
# * 【8位数字尾号】（如：...88888888）：约需 12 至 36 小时。
# * 【10位数字尾号】（如：...9999999999）：难度呈几何级飙升，单窗口通常需要数月。
# * 【4位英文单词】（如：...news...）：约需 1 至 3 小时。
# * 【6位英文单词】（如：...digital...）：约需 48 小时 至数周。
# 
# 🔥 【极速调优】：
# 由于本脚本采用了基于进程隔离（PID）的物理错峰架构，你完全可以利用“多开窗口”来实现多核心并发爆发！
# 只需连续双击打开 10 到 15 个全新的终端或 PowerShell 窗口，并在每个窗口内同时输入 `python vanity_generator.py` 启动。
# 这能瞬间将整体碰撞速度堆叠至 200 K/s ~ 300 K/s 以上，全量榨干你电脑的所有 CPU 核心与物理算力。
# ==============================================================================

import subprocess
import os
import time
import re

def pro_collision(target_prefix, target_suffix, mode="mixed", last_n_digits=0):
    """
    [靓号碰撞核心函数]
    :param target_prefix: 目标地址前缀（VSYS 规定主网地址必须以 'AR' 开头）
    :param target_suffix: 目标地址后缀（若不限制，则传入空字符串 ""）
    :param mode: 主体字符集筛选模式："mixed"(不限制), "letters"(主体纯字母), "digits"(主体纯数字)
    :param last_n_digits: 强制限制地址最后 N 位必须为纯数字 (0 代表不启用此限制)
    """
    # 物理定位官方或底层的加密包钱包生成器程序
    jar_path = "walletgenerator_v0.1.0.jar"
    # 使用当前进程的 PID (Process ID) 动态命名临时文件，防止多开脚本时发生 IO 冲突或覆盖崩溃
    temp_file = f"temp_batch_{os.getpid()}.txt"
    # 定义碰撞成功后的结构化资产导出文件路径
    output_file = "titan_pro_collection.csv"
    
    # 基础设施前置检查：若找不到核心密算组件，直接安全拦截并退出
    if not os.path.exists(jar_path):
        print(f"❌ 找不到 {jar_path}")
        return

    # 资产归档文件初始化：如果文件不存在，则创建并写入带 BOM 头 (utf-8-sig) 的标准 CSV 标题行
    if not os.path.exists(output_file):
        with open(output_file, "w", encoding='utf-8-sig') as out:
            out.write("Address,PrivateKey,Type,Rule\n")

    # 打印系统启动时的拓扑参数回显
    print(f"🚀 [Pro 模式] 启动成功")
    print(f"📍 匹配: {target_prefix}...{target_suffix}")
    print(f"🔢 模式: {mode} | 尾部锁定: {last_n_digits}位数字")
    print("-" * 50)
    
    # 初始化统计计数器：全网碰撞总数、成功命中总数、启动绝对时间
    total_count = 0
    found_count = 0
    start_time = time.time()
    
    # 【性能优化点】：在循环外部预编译正则表达式，避免在每秒数万次的循环内部重复编译导致 CPU 耗尽
    has_digit = re.compile(r'[1-9]')        # 匹配 Base58 编码字符集中的数字（排除0）
    has_letter = re.compile(r'[a-zA-Z]')    # 匹配大小写英文字母
    only_digit = re.compile(r'^[1-9]+$')     # 严格校验是否全为数字（用于尾部特定锁定位数）

    try:
        # 进入无限物理循环进行大规模暴力碰撞，直到用户手动触发 Ctrl+C 中断
        while True:
            batch_size = 5000  # 设置单次调用 Java 密算组件批量生成的临时地址规模（5000是一个兼顾内存与IO的平衡点）
            
            # 以覆盖写入模式 ("w") 打开临时文件，将 Java 进程的标准输出直接重定向落盘
            with open(temp_file, "w") as f:
                # 调用系统底层的 Java 环境执行密算，通过命令参数 -c 指定批量生成规模
                # stdout 绑定至文件句柄 f，stderr 丢弃至 DEVNULL 垃圾桶，防止报错刷屏破坏控制台 UI
                subprocess.run(["java", "-jar", jar_path, "-c", str(batch_size)], 
                               stdout=f, stderr=subprocess.DEVNULL)
            
            # 若由于 IO 延迟或系统异常导致临时文件未生成，直接跳过本次循环，进入下一轮
            if not os.path.exists(temp_file): continue

            # 以安全模式读取刚才生成的临时批量地址块文件，忽略编码异常（errors='ignore'）防止进程卡断
            with open(temp_file, "r", encoding='utf-8', errors='ignore') as f:
                # 按照 Java 工具标准的分隔符破折号对文件进行分块切片，获取包含地址与私钥的独立数据块
                blocks = f.read().split("-------------------------")
                batch_hits = [] # 初始化当前批次的成功命中缓存列表
                
                # 遍历当前批次切分出的每一个账户文本块
                for block in blocks:
                    # 双重断言：只有同时包含地址关键字和私钥关键字的文本块才是合法的账户数据
                    if "address  " in block and "private key" in block:
                        # 提取包含冒号 ":" 的有效行，去除两端空格，清洗出结构化键值对
                        lines = [line.strip() for line in block.strip().split('\n') if ":" in line]
                        # 通过字典推导式将原本松散的文本转化为 Python 原生字典类型
                        data = {l.split(":")[0].strip(): l.split(":")[1].strip() for l in lines}
                        
                        # 提取清洗出的 VSYS 地址与对应的明文私钥
                        addr = data.get("address", "")
                        priv = data.get("private key", "")
                        if not addr: continue # 防御性编程：若地址为空则放弃

                        # ---- 规则过滤阶段 1. 前后缀基本校验 ----
                        # 校验地址是否以指定前缀开头（如 "AR"）
                        if not addr.startswith(target_prefix): continue
                        # 校验地址是否以指定后缀结尾
                        if target_suffix and not addr.endswith(target_suffix): continue

                        # ---- 规则过滤阶段 2. 尾部 N 位数字校验 ----
                        if last_n_digits > 0:
                            # 逆向切片，提取出地址末尾指定位数的字符串片段
                            suffix_to_check = addr[-last_n_digits:]
                            # 利用预编译的正则进行全数字比对，只要含有字母，立即熔断放弃
                            if not only_digit.match(suffix_to_check):
                                continue

                        # ---- 规则过滤阶段 3. 字符集模式校验 (排除开头 AR 和 尾部锁定位) ----
                        # 动态切片截取地址的主体躯干部分（Body），剥离前2位特定的 'AR' 和尾部已经锁定的纯数字区
                        body = addr[2:-last_n_digits] if last_n_digits > 0 else addr[2:]
                        
                        # 如果用户要求主体是纯字母，但主体内发现了数字，则淘汰
                        if mode == "letters":
                            if has_digit.search(body): continue
                        # 如果用户要求主体是纯数字，但主体内发现了字母，则淘汰
                        elif mode == "digits":
                            if has_letter.search(body): continue
                        
                        # 突破所有过滤关卡后，判定为完美命中“靓号”，组装成标准 CSV 行存入缓冲区
                        batch_hits.append(f"{addr},{priv},{mode},{last_n_digits}digits")

                # 如果当前批次内发现了靓号资产，立即启动物理落盘与控制台高亮回显
                if batch_hits:
                    # 以增量追加模式 ("a") 写入主归集文件中
                    with open(output_file, "a", encoding='utf-8-sig') as out:
                        for hit in batch_hits:
                            out.write(hit + "\n")
                    found_count += len(batch_hits) # 更新总命中计数
                    # 高亮复显当前批次命中的第一个靓号地址
                    print(f"\n💎 命中! 地址: {batch_hits[0].split(',')[0]} (已导出)")
            
            # ---- 统计、速率计算与单行视觉刷新 ----
            total_count += batch_size # 累加全网碰撞总流水
            elapsed = time.time() - start_time # 计算项目总耗时（秒）
            # 计算每秒碰撞并发速率 (速度指标：K/s = 每秒千次碰撞)
            speed = int(total_count / elapsed) if elapsed > 0 else 0
            # 配合 end="\r" 实现终端单行无闪烁无缝重叠刷新，维持赛博朋克极客风 UI
            print(f"📊 扫描: {total_count} | 发现: {found_count} | 速度: {speed} K/s", end="\r")

    except KeyboardInterrupt:
        # 捕捉用户按下的 Ctrl + C 组合键，实现优雅的生产级安全退出
        print(f"\n🛑 已停止。")
    finally:
        # 【收尾垃圾回收】：不论程序是正常运行还是遭遇异常中断，物理清空残留的临时批量文本，释放磁盘空间
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass

if __name__ == "__main__":
    # --- 配置中心 ---
    MY_PREFIX = "AR"         # 核心前缀：VSYS 主网协议硬性规定必须以大写字母 AR 开头
    MY_SUFFIX = ""           # 核心后缀：后缀匹配规则（注意：当同时开启尾部纯数字锁定时，若后缀含有字母会发生逻辑冲突淘汰所有结果，所以二者需谨慎共存）
    
    # 筛选字符集：
    # "mixed"   -> 混合型地址（前缀+尾部数字满足即可，中间无所谓）
    # "letters" -> 极品纯字母（除AR和尾数字外，中间躯干绝不允许出现任何数字）
    # "digits"  -> 极品纯数字（除AR外，整条地址全面由1-9的纯数字铺满）
    MY_MODE = "mixed"        
    
    # 关键设置：限制当前靓号地址的最后多少位必须完全是纯数字（当前设置为 6 位数字）
    REQUIRED_LAST_DIGITS = 6 
    
    # 启动碰撞引擎
    pro_collision(MY_PREFIX, MY_SUFFIX, MY_MODE, REQUIRED_LAST_DIGITS)