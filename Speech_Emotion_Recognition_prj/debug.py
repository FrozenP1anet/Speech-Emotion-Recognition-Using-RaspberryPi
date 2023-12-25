import subprocess

def get_ip_address(interface='wlan0'):
    try:
        # 运行 ifconfig 命令并捕获输出
        result = subprocess.run(['ifconfig', interface], capture_output=True, text=True)

        # 从输出中提取IP地址信息
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if 'inet ' in line:
                ip_address = line.split()[1]
                return ip_address

        return "No IP address found for the specified interface"
    except Exception as e:
        return str(e)

# 指定网络接口，例如 'eth0' 或 'wlan0'
interface_name = 'wlan0'

# 获取并打印指定网络接口的IP地址
ip_address = get_ip_address(interface_name)
print(f"IP Address for {interface_name}: {ip_address}")
