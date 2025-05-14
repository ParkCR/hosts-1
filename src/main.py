#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Hosts Updater 主程序
自动更新 GitHub 相关域名的 hosts 文件
"""

import asyncio
import sys
from datetime import datetime
from src.utils import (
    parse_domain_file,
    resolve_domains,
    generate_hosts_content
)

async def main():
    print(f"\n🚀 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始解析域名")
    
    try:
        # 1. 读取并解析Domain文件
        domain_structure = parse_domain_file()
        domains = [domain for _, domain in domain_structure if domain]
        print(f"📋 发现 {len(domains)} 个待解析域名")
        
        # 2. 批量解析域名
        print("⏳ 正在解析域名...")
        ip_map = await resolve_domains(domains)
        
        # 3. 生成格式化hosts内容
        hosts_content = generate_hosts_content(domain_structure, ip_map)
        
        # 4. 写入hosts.txt文件
        with open("hosts.txt", "w", encoding="utf-8") as f:
            f.write(hosts_content)
        
        # 5. 输出统计信息
        success_count = sum(1 for v in ip_map.values() if not v.startswith('#'))
        print(f"\n✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 解析完成")
        print(f"💾 生成结果已保存至 hosts.txt")
        print(f"📊 解析成功率: {success_count}/{len(ip_map)} ({success_count/len(ip_map):.0%})")
        
    except FileNotFoundError as e:
        print(f"\n❌ 文件未找到: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生未知错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Windows 事件循环兼容性设置
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 启动主程序
    asyncio.run(main())
