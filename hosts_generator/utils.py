#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Hosts 工具模块
提供域名解析和IP处理功能
"""
import re
import asyncio
import aiodns
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pythonping import ping
from bs4 import BeautifulSoup
import requests
from retry import retry

# 配置常量
PING_TIMEOUT = 1  # 秒
DNS_SERVERS = ["1.1.1.1", "8.8.8.8", "101.101.101.101","101.102.103.104"]  # Cloudflare, Google, Quad101DNS
DISCARD_IPS = ["1.0.1.1", "1.2.1.1", "127.0.0.1"]  # 需要排除的IP
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def parse_domain_file(file_path: str = "Domain") -> List[Tuple[str, str]]:
    """
    解析Domain文件结构，保留注释和分类
    返回: [(注释行, 域名), ("", 域名), ...]
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Domain文件不存在: {file_path}")

    result = []
    current_comment = ""

    for line in lines:
        if line.startswith("#"):
            current_comment = line
            result.append((current_comment, ""))
        else:
            result.append(("", line))
    return result

@retry(tries=3, delay=1)
async def resolve_dns(domain: str) -> List[str]:
    """通过DNS解析获取域名IP列表"""
    resolver = aiodns.DNSResolver()
    resolver.nameservers = DNS_SERVERS
    try:
        answers = await resolver.query(domain, 'A')
        return [answer.host for answer in answers 
               if answer.host not in DISCARD_IPS]
    except (aiodns.error.DNSError, asyncio.TimeoutError) as e:
        print(f"DNS查询失败: {domain} - {str(e)}")
        return []

@retry(tries=3, delay=1)
def scrape_ips(domain: str) -> List[str]:
    """从ipaddress网站抓取IP（使用requests+BeautifulSoup）"""
    try:
        resp = requests.get(
            f"https://sites.ipaddress.com/{domain}",
            timeout=10,
            headers={"User-Agent": USER_AGENT}
        )
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 两种方式提取IP：正则匹配和特定CSS选择器
        ips = set()
        
        # 方法1：正则匹配
        ips.update(re.findall(
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
            soup.get_text()
        ))
        
        # 方法2：特定表格中的IP
        for table in soup.select("table.table"):
            if "IP Address" in table.get_text():
                ips.update(re.findall(
                    r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
                    table.get_text()
                ))
        
        return [ip for ip in ips if ip not in DISCARD_IPS]
    except Exception as e:
        print(f"网页抓取失败: {domain} - {str(e)}")
        return []

def test_latency(ip: str) -> float:
    """测试IP延迟，返回毫秒数"""
    try:
        response = ping(ip, count=3, timeout=PING_TIMEOUT)
        return response.rtt_avg_ms if response else float('inf')
    except Exception as e:
        print(f"Ping测试失败: {ip} - {str(e)}")
        return float('inf')

async def resolve_domains(domains: List[str]) -> Dict[str, str]:
    """
    批量解析域名
    返回: {"domain.com": "1.1.1.1"}
    """
    result = {}
    
    # 并行获取DNS和网页IP
    dns_results = await asyncio.gather(
        *(resolve_dns(domain) for domain in domains)
    )
    web_results = [scrape_ips(domain) for domain in domains]
    
    for domain, dns_ips, web_ips in zip(domains, dns_results, web_results):
        all_ips = list(set(dns_ips + web_ips))
        
        if not all_ips:
            result[domain] = "# 解析失败"
            continue
            
        # 选择延迟最低的IP
        best_ip = min(all_ips, key=test_latency)
        result[domain] = best_ip
        
        # 打印调试信息
        print(f"{domain}: 候选IP {len(all_ips)}个 -> 选择 {best_ip}")
    
    return result

def generate_hosts_content(
    domain_structure: List[Tuple[str, str]],
    ip_map: Dict[str, str],
    min_padding: int = 4
) -> str:
    """
    生成格式化的hosts内容
    :param domain_structure: parse_domain_file()的返回结构
    :param ip_map: 域名到IP的映射字典
    :param min_padding: IP与域名最小间隔空格数
    """
    # 动态计算对齐宽度
    valid_ips = [ip for ip in ip_map.values() if not ip.startswith("#")]
    max_ip_len = max(len(ip) for ip in valid_ips) if valid_ips else 15
    padding_width = max_ip_len + min_padding
    
    # 文件头
    header = f"""# GitHub Hosts 自动更新
# 项目地址: https://github.com/yourname/github-hosts-updater
# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 总计解析: {len([v for v in ip_map.values() if not v.startswith('#')])}/{len(ip_map)} 成功

"""
    
    # 构建内容
    content = []
    last_was_comment = False
    
    for comment, domain in domain_structure:
        if comment:
            # 处理注释行
            if not last_was_comment and content:  # 非开头时添加空行
                content.append("")
            content.append(comment)
            last_was_comment = True
        elif domain:
            # 处理域名行
            ip = ip_map.get(domain, "# 域名未解析")
            line = f"{ip.ljust(padding_width)}{domain}"
            
            # 标记超时IP
            if ip in ip_map and test_latency(ip) == float('inf'):
                line += "  # 超时"
                
            content.append(line)
            last_was_comment = False
    
    return header + "\n".join(content) + "\n"
