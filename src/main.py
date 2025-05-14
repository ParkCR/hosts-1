#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Hosts Updater 主程序
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
        # 读取并解析Domain文件结构
        domain_structure = parse_domain_file()
        domains = [domain for _, domain in domain_structure if domain]
        print(f"📋 发现 {len(domains)} 个待解析域名")
        
        # 解析所有域名
        ip_map = await resolve_domains(domains)
        
        # 生成格式化hosts内容
        hosts_content = generate_hosts_content(domain_structure, ip_map)
        
        # 写入文件
        with open("../hosts.txt", "w", encoding="utf-8") as f:
            f.write(hosts_content)
        
        print(f"\n✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 解析完成")
        print(f"💾 生成结果已保存至 hosts.txt")
        print(f"🔍 解析成功率: {sum(1 for v in ip_map.values() if not v.startswith('#'))}/{len(ip_map)}")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Windows 事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())