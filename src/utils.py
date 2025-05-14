#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub Hosts Updater 工具模块
"""
import re
import aiodns
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pythonping import ping
from requests_html import HTMLSession
from retry import retry

# 配置常量
PING_TIMEOUT = 1
DNS_SERVERS = ["1.1.1.1", "8.8.8.8", "101.101.101.101", "101.102.103.104"]
DISCARD_IPS = ["1.0.1.1", "1.2.1.1", "127.0.0.1"]

def parse_domain_file(file_path: str = "../Domain") -> List[Tuple[str, str]]:
    """
    解析Domain文件结构，保留注释和分类
    返回: [(注释行, 域名), ("", 域名), ...]
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip() for line in f if line.strip()]
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
    except aiodns.error.DNSError:
        return []

@retry(tries=3, delay=1)
def scrape_ips(domain: str) -> List[str]:
    """从ipaddress网站抓取IP"""
    session = HTMLSession()
    try:
        resp = session.get(
            f"https://sites.ipaddress.com/{domain}",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", resp.text)
        return [ip for ip in set(ips) if ip not in DISCARD_IPS]
    except Exception:
        return []
    finally:
        session.close()

def test_latency(ip: str) -> float:
    """测试IP延迟，返回毫秒数"""
    try:
        return ping(ip, count=3, timeout=PING_TIMEOUT).rtt_avg_ms
    except Exception:
        return float('inf')

async def resolve_domains(domains: List[str]) -> Dict[str, str]:
    """
    批量解析域名
    返回: {"domain.com": "1.1.1.1"}
    """
    result = {}
    for domain in domains:
        # 从多个来源获取IP
        ips = list(set(
            await resolve_dns(domain) + 
            scrape_ips(domain)
        ))
        
        # 选择延迟最低的IP
        best_ip = min(ips, key=test_latency, default=None) if ips else None
        result[domain] = best_ip or "# 解析失败"
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
    max_ip_len = max(
        len(ip) for ip in ip_map.values() 
        if not ip.startswith("#")
    ) if ip_map else 15
    
    padding_width = max_ip_len + min_padding
    
    # 文件头
    header = f"""# GitHub Hosts 自动更新
# 项目地址: https://github.com/yourname/github-hosts-updater
# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    # 构建内容
    content = []
    last_was_comment = False
    
    for comment, domain in domain_structure:
        if comment:
            # 处理注释行
            if not last_was_comment:
                content.append("")  # 添加空行分隔
            content.append(comment)
            last_was_comment = True
        elif domain:
            # 处理域名行
            ip = ip_map.get(domain, "# 域名未解析")
            line = f"{ip.ljust(padding_width)}{domain}"
            content.append(line)
            last_was_comment = False
    
    return header + "\n".join(content) + "\n"