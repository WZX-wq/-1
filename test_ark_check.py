# -*- coding: utf-8 -*-
"""测试火山引擎方舟 API 连通性"""
import sys, io, socket, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import urllib3
urllib3.disable_warnings()
import requests

# 1. DNS 解析
for h in ['ark.cn-beijing.volces.com', 'ark.cn-beijing.volces.com']:
    try:
        ips = set(i[4][0] for i in socket.getaddrinfo(h, None))
        print(f'DNS {h}: {ips}')
    except Exception as e:
        print(f'DNS {h} 解析失败: {e}')

# 2. TCP 连接测试
def tcp_test(host, port, timeout=8):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    t0 = time.time()
    try:
        s.connect((host, port))
        return f'可达 ({time.time()-t0:.1f}s)'
    except Exception as e:
        return f'失败: {e}'
    finally:
        s.close()

print('\nTCP ark.cn-beijing.volces.com:443 ->', tcp_test('ark.cn-beijing.volces.com', 443))

# 3. HTTPS 请求测试（轻量）
print('\n--- HTTPS GET ark.cn-beijing.volces.com ---')
try:
    r = requests.get('https://ark.cn-beijing.volces.com/api/v3', timeout=10, verify=False)
    print('状态码:', r.status_code)
except Exception as e:
    print('请求异常:', repr(e))
