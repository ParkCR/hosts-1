#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Hosts 自动更新主程序
"""
import asyncio
import sys
from datetime import datetime
from .utils import (
    parse_domain_file,
    resolve_domains,
    generate_hosts_content
)

async def main():
    print(f"\n🚀 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始解析域名")
    
    try:
        # 1. 读取域名配置
        domain_structure = parse_domain_file("Domain")
        domains = [d for _, d in domain_structure if d]
        print(f"📋 共发现 {len(domains)} 个域名需要解析")
        
        # 2. 批量解析
        print("⏳ 正在解析域名...")
        ip_map = await resolve_domains(domains)
        
        # 3. 生成hosts内容
        hosts_content = generate_hosts_content(domain_structure, ip_map)
        
        # 4. 写入文件
        with open("hosts.txt", "w", encoding="utf-8") as f:
            f.write(hosts_content)
        
        # 5. 输出报告
        success = sum(1 for ip in ip_map.values() if not ip.startswith('#'))
        print(f"\n✅ 解析完成！成功率: {success}/{len(ip_map)}")
        print(f"💾 结果已保存到 hosts.txt")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
