# ==============================================================================
# FILE_START: vsys_balance_checker.py
# ROLE: VSYS 区块链海量地址余额扫描
# TECHNICAL_NOTE: 本脚本基于 asyncio 异步协程与 aiohttp 异步连接池技术，配合并发信号量
#                 (Semaphore) 机制，实现对公链节点（或自建超级节点）的高性能非阻塞轮询。
#                 性能指标：公共节点速度建议 100 addr/s | 本地私有节点速度可达 50000 addr/s
# ==============================================================================
# 🛠️ [使用前准备工作]
# 1. 输入数据准备：在脚本同级目录下创建或打开 list_address.csv 文件。
# 2. 贴入目标地址：将需要查询余额的 VSYS 地址复制粘贴进去，注意：一行一个地址，无需标题行。
# 3. 节点与并发配置：如卡住就编辑更换其它节点，或微调并发数，请直接修改代码下方 CONFIG 字典中的对应参数。
#
# 💻 [脚本运行指令]
# 右键点击代码所在的文件目录 -> 选择“在终端打开” -> 在控制台中输入以下命令并回车运行：
# python vsys_balance_checker.py
#
# 📦 [结果数据导出]
# 1. 任务完成后，脚本会自动在本地同级目录下生成资产结果账本：balance_address.csv
# 2. 核心特性：导出的数据已通过内存映射字典自动修复乱序，完全严格遵循你输入时的地址顺序。
# ==============================================================================


"""
ROLE:从区块链节点读取指定地址的余额。
"""
import asyncio
import aiohttp
import csv
import os
import time

# =================================================================
# ⚙️ 全局配置参数 (详细中文注释)
# =================================================================
CONFIG = {
    # VSYS 节点 API 地址：用于接收并响应 RESTful 余额查询请求的核心中转站
    "NODE_URL": "http://wallet-node.v.systems:9922", 
    
    # 输入文件：每行一个地址的 CSV 文件（脚本将从中按行清洗读取目标地址）
    "INPUT_FILE": "list_address.csv",          
    
    # 输出文件：保存地址和余额的结果文件（标准结构：地址,余额）
    "OUTPUT_FILE": "balance_address.csv",      
    
    # 并发限制：同时发起请求的数量。150-300 是比较理想的高速区间
    # 警告：公开节点请控制在 150 以内防止被封 IP；如果是自建节点，可以调大至 1000+
    "CONCURRENCY_LIMIT": 150,                  
    
    # 网络请求失败（如502/404/网络抖动）后的重试延迟（秒）
    "RETRY_DELAY": 0.5,                        
}

# 🎨 赛博霓虹风格颜色代码（终端 ANSI 转义序列，用于在命令行控制台渲染彩色高亮 UI）
C_CYAN = "\033[96m"       # 青色：用于系统级提示信息
C_MAGENTA = "\033[95m"    # 品红：备用视觉标签
C_GREEN = "\033[92m"      # 绿色：用于成功、完成状态
C_YELLOW = "\033[93m"     # 黄色：用于警告或过渡状态
C_RED = "\033[91m"        # 红色：用于错误或强行中断提示
C_RESET = "\033[0m"       # 重置：清除颜色属性，防止控制台文本后续染色异常

# 全局重试统计：用于跟踪并在最终报告中量化整个公链网络的健康状况
retry_stats = {"count": 0}

async def get_balance_stubborn(session, address, semaphore):
    """
    [顽固查询函数]
    核心拦截设计：
    1. 利用 asyncio.Semaphore 严格控制当前在网络上奔跑的并发连接数，防止瞬间冲垮目标节点。
    2. 使用 while True 构造无限死循环，配合 try...except 拦截一切因超时、节点崩溃或断网引发的物理异常。
    3. 只有当目标节点完全给出标准 HTTP 200 回应并成功解析出数值时，方可打破循环（Return），确保无任何一个断点漏单。
    """
    # 拼接官方规定的余额查询底层 API URL 路由
    url = f"{CONFIG['NODE_URL']}/addresses/balance/{address}"
    
    while True:
        # 激活信号量计数器：当并发池满了之后，后续的协程将在此行被异步挂起（阻塞），等待有空位释放
        async with semaphore:
            try:
                # 发起异步 GET 请求，并设置强行硬超时限制为 5 秒，防止某个卡死节点的连接永久挂起连接池
                async with session.get(url, timeout=5) as response:
                    # 只有当返回标准的 HTTP 200 状态码时，才被判定为有效的网络交互
                    if response.status == 200:
                        data = await response.json()
                        # VSYS 底层记账单元为 Satoshi，其精度固定为 10 的 8 次方（100,000,000）
                        # 必须除以 100_000_000 换算为人类直观可读的 float 实数余额
                        balance = data.get('balance', 0) / 100_000_000
                        # 成功突围，将清洗完的数据以元组形式向上层主程序投递，并彻底销毁本轮死循环
                        return address, balance
                    else:
                        # 节点返回非 200 错误码（例如 502 Bad Gateway），累加错误计数器
                        retry_stats["count"] += 1
            except Exception:
                # 捕获因超时 (TimeoutError) 或断网引发的任何连接层物理异常，累加错误计数器
                retry_stats["count"] += 1
        
        # 【自愈阻尼延迟】：如果触发了错误，在进入下一轮暴力死循环重试前，强制挂起 0.5 秒
        # 这既能防止高频空刷导致 CPU 飙升，也能有效避免被公开节点防火墙判定为恶意 DDoS 而永久封锁 IP
        await asyncio.sleep(CONFIG["RETRY_DELAY"])

async def main():
    # --- 1. 读取地址列表 ---
    # 健壮性前置断言：如果找不到存放待查钱包的文件，直接抛错拦截，防止后续协程空转
    if not os.path.exists(CONFIG["INPUT_FILE"]):
        print(f"{C_RED}❌ 错误: 找不到输入文件 {CONFIG['INPUT_FILE']}{C_RESET}")
        return

    addresses = []
    # 以防 BOM 头的安全模式 (utf-8-sig) 读取输入文本，防止 Excel 导出的 CSV 文件自带的特殊字符引发首行地址污染
    with open(CONFIG["INPUT_FILE"], 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            # 过滤并清洗：排除文件内的彻底空白行，同时剔除每条区块链地址两端的不可见空格
            if row and row[0].strip():
                addresses.append(row[0].strip())

    total = len(addresses)
    print(f"\n{C_CYAN}🚀 启动顽固扫描引擎 | 目标: {total} | 并发: {CONFIG['CONCURRENCY_LIMIT']}{C_RESET}")
    print(f"{C_CYAN}{'='*70}{C_RESET}")

    start_time = time.time()
    # 在主线程中初始化异步并发信号量锁
    semaphore = asyncio.Semaphore(CONFIG["CONCURRENCY_LIMIT"])
    
    # --- 2. 异步执行查询 ---
    # 构建 aiohttp 连接池上下文句柄，避免为每一个地址重复开关 TCP 三次握手
    async with aiohttp.ClientSession() as session:
        # 利用列表推导式，瞬间将数万个查询目标打包封装为 Python 的轻量级异步任务（Tasks）
        tasks = [get_balance_stubborn(session, addr, semaphore) for addr in addresses]
        
        results = []
        completed_count = 0
        
        # 【流式进度跟踪】：使用 as_completed 机制。哪个任务先从网络端返回数据，就立刻弹出来处理
        # 从而实现无延迟的控制台实时进度条渲染
        for future in asyncio.as_completed(tasks):
            res = await future  # 异步解包元组 (address, balance)
            results.append(res)
            completed_count += 1
            
            # --- UI 实时进度反馈逻辑 ---
            percent = (completed_count / total) * 100
            # 动态渲染百分比进度条：每 5% 映射为一个实心方块 █
            bar = "█" * int(percent / 5) + "-" * (20 - int(percent / 5))
            # 动态异常回显：只有在系统发生过真实的网络重试时，控制台才会高亮提示累计重试次数
            retry_msg = f"{C_RED} (Retries: {retry_stats['count']}){C_CYAN}" if retry_stats["count"] > 0 else ""
            
            # 配合 \r 实现单行高频率覆写刷新，动态回显当前地址的前6位、后4位以及其最新的可用余额数值
            print(f"\r{C_CYAN}[{bar}] {percent:>5.1f}% | ⚡ {completed_count}/{total} | 🕵️ {res[0][:6]}...{res[0][-4:]} | 💰 {res[1]:<10}{retry_msg}", end="", flush=True)

    # --- 3. 排序与安全写入 (修复 PermissionError 核心逻辑) ---
    # 架构学要点：由于 as_completed 是乱序返回的，为了保证输出的文件和原 list_address.csv 顺序完全对齐
    # 先将无序结果映射到临时字典中，再用原始 addresses 列表作为键值索引进行保序导出
    res_dict = {addr: bal for addr, bal in results}
    
    print(f"\n\n{C_YELLOW}📦 正在导出数据...{C_RESET}")
    
    target_path = CONFIG["OUTPUT_FILE"]
    
    # 【文件系统自愈状态机】：解决因 Excel 意外打开同名文件而导致写入崩溃的业界痛点
    while True:
        try:
            # 尝试写入标准 CSV 资产账本
            with open(target_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                for addr in addresses:
                    # 严格按照输入顺序，将地址与对应的科学换算后的余额安全写入
                    writer.writerow([addr, res_dict[addr]])
            # 如果成功落盘，彻底跳出该死循环
            break 
        except PermissionError:
            # 捕获操作系统级的文件拒绝访问错误（常见于 balance_address.csv 此时正被 Excel 打开并独占死锁）
            print(f"\n{C_RED}⚠️ 写入失败: {target_path} 正在被其他程序(如Excel)占用！{C_RESET}")
            # 生成以当前 Unix 秒级时间戳命名的全新备份文件名，强行自愈绕过死锁
            timestamp = int(time.time())
            target_path = f"balance_address_{timestamp}.csv"
            print(f"{C_CYAN}🔄 自动切换至新文件名保存: {target_path}{C_RESET}")
            # 进入下一次循环，使用全新的 target_path 重新尝试写入，确保数据无论如何都不会在内存中丢失

    # 计算整体全网扫描的总物理耗时（秒）
    duration = time.time() - start_time

    # --- 4. 最终扫描报告 ---
    print(f"{C_CYAN}{'='*70}{C_RESET}")
    print(f"{C_GREEN}✅ 任务已成功保存到: {target_path}{C_RESET}")
    print(f"📊 扫描耗时: {duration:.2f} 秒")
    print(f"🔄 异常重试: {retry_stats['count']} 次")
    print(f"🛰️  平均速率: {total/duration:.2f} addr/s")
    print(f"{C_CYAN}{'='*70}{C_RESET}\n")

if __name__ == "__main__":
    try:
        # 激活顶层异步事件循环
        asyncio.run(main())
    except KeyboardInterrupt:
        # 捕获用户在终端中按下的 Ctrl + C 组合键，优雅拦截并退出程序，防止抛出丑陋的 Traceback 堆栈报错
        print(f"\n{C_RED}🛑 用户手动强行停止{C_RESET}")