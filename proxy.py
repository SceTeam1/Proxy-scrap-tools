import requests
import os
import fade
import sys
import asyncio
import aiohttp
import json
import time
from bs4 import BeautifulSoup
from colorama import Fore, Style
from alive_progress import alive_bar

class Config:
    def __init__(self):
        self.load()
    
    def load(self):
        self.data = {
            'timeout': 5,
            'workers': 100,
            'save_by_type': True,
            'sort_by_speed': True,
            'geo_filter': None,
            'min_latency': 0.1,
            'max_latency': 3.0,
            'webhook_url': None,
            'webhook_notify': False,
            'notify_every': 10,
            'theme': 'dark',
            'autosave_config': True,
            'proxy_score_enabled': True,
            'sources': [
                'https://www.sslproxies.org/',
                'https://free-proxy-list.net/',
                'https://www.us-proxy.org/',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt',
                'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt'
            ]
        }
        if os.path.exists('config/settings.json'):
            try:
                with open('config/settings.json') as f:
                    self.data.update(json.load(f))
            except:
                pass
    
    def save(self):
        os.makedirs('config', exist_ok=True)
        with open('config/settings.json', 'w') as f:
            json.dump(self.data, f)

config = Config()

class ProxyDB:
    def __init__(self):
        self.proxies = {}
        self.load()
    
    def load(self):
        if os.path.exists('config/proxy_db.json'):
            try:
                with open('config/proxy_db.json') as f:
                    self.proxies = json.load(f)
            except:
                self.proxies = {}
    
    def save(self):
        with open('config/proxy_db.json', 'w') as f:
            json.dump(self.proxies, f)
    
    def update(self, proxy, latency, country=None, protocol=None):
        if proxy not in self.proxies:
            self.proxies[proxy] = {
                'latency': [],
                'success': 0,
                'fail': 0,
                'last_check': 0,
                'country': country,
                'protocol': protocol
            }
        self.proxies[proxy]['latency'].append(latency)
        if latency > 0:
            self.proxies[proxy]['success'] += 1
            self.proxies[proxy]['last_check'] = time.time()
        else:
            self.proxies[proxy]['fail'] += 1
        self.save()

proxy_db = ProxyDB()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_title():
    cols = os.get_terminal_size().columns
    if cols < 80:
        return fade.fire('''
 ██████╗ ██████╗  ██████╗ 
██╔══██╗██╔══██╗██╔═══██╗
██████╔╝██████╔╝██║   ██║
██╔═══╝ ██╔══██╗██║   ██║
██║     ██║  ██║╚██████╔╝
╚═╝     ╚═╝  ╚═╝ ╚═════╝ 
discord.gg/shop2sca
''')
    else:
        return fade.fire('''
                    ███████╗██╗  ██╗ ██████╗ ██████╗ ██████╗ ███████╗
                    ██╔════╝██║  ██║██╔═══██╗██╔══██╗██╔══██╗██╔════╝
                    ███████╗███████║██║   ██║██████╔╝██████╔╝█████╗  
                    ╚════██║██╔══██║██║   ██║██╔═══╝ ██╔═══╝ ██╔══╝  
                    ███████║██║  ██║╚██████╔╝██║     ██║     ███████╗
                    ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝     ╚══════╝
                          Discord: discord.gg/shop2sca
''')

async def check_proxy(session, proxy, timeout):
    start = time.time()
    protocol = proxy.split('://')[0] if '://' in proxy else 'http'
    try:
        async with session.get(
            "http://httpbin.org/ip",
            proxy=proxy,
            timeout=timeout
        ) as response:
            latency = (time.time() - start) * 1000
            if response.status == 200:
                country = await get_country(response)
                proxy_db.update(proxy, latency, country, protocol)
                return proxy, latency, country, protocol
    except:
        pass
    proxy_db.update(proxy, -1)
    return None

async def get_country(response):
    try:
        ip = (await response.json())['origin'].split(',')[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://ip-api.com/json/{ip}') as r:
                data = await r.json()
                return data.get('countryCode', 'UNKNOWN')
    except:
        return 'UNKNOWN'

async def mass_check(proxies, timeout, workers):
    conn = aiohttp.TCPConnector(limit=workers)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [check_proxy(session, proxy, timeout) for proxy in proxies]
        with alive_bar(len(proxies), title='Testing proxies', bar='filling') as bar:
            for future in asyncio.as_completed(tasks):
                result = await future
                if result:
                    proxy, latency, country, protocol = result
                    bar.text = f'✅ {proxy} | {latency:.2f}ms | {country}'
                    yield result
                bar()

def get_proxies():
    proxies = set()
    for url in config.data['sources']:
        try:
            if url.endswith('.txt'):
                response = requests.get(url, timeout=10)
                proxies.update(response.text.splitlines())
            else:
                response = requests.get(url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find(id='proxylisttable')
                if table:
                    rows = table.find('tbody').find_all('tr')
                    for row in rows:
                        tds = row.find_all('td')
                        ip = tds[0].text
                        port = tds[1].text
                        protocol = tds[6].text.lower()
                        proxies.add(f"{protocol}://{ip}:{port}")
        except:
            continue
    return list(proxies)

def save_proxy(proxy, latency, country, protocol):
    os.makedirs('proxies', exist_ok=True)
    if config.data['save_by_type']:
        with open(f'proxies/{protocol}.txt', 'a') as f:
            f.write(f"{proxy}\n")
    if country and config.data['geo_filter'] in [None, country]:
        os.makedirs(f'proxies/countries', exist_ok=True)
        with open(f'proxies/countries/{country}.txt', 'a') as f:
            f.write(f"{proxy}\n")
    if config.data['sort_by_speed']:
        with open('proxies/fastest.txt', 'a') as f:
            f.write(f"{proxy}|{latency:.2f}\n")

def clean_results():
    for root, _, files in os.walk('proxies'):
        for file in files:
            if file.endswith('.txt'):
                open(os.path.join(root, file), 'w').close()

async def quick_check():
    proxies = get_proxies()[:200]
    valid = 0
    async for proxy, latency, country, protocol in mass_check(proxies, config.data['timeout'], config.data['workers']):
        save_proxy(proxy, latency, country, protocol)
        valid += 1
    print(f"\nFound {valid} valid proxies!")

async def full_scan():
    proxies = get_proxies()
    valid = 0
    async for proxy, latency, country, protocol in mass_check(proxies, config.data['timeout'], config.data['workers']):
        save_proxy(proxy, latency, country, protocol)
        valid += 1
    print(f"\nFound {valid} valid proxies!")

def custom_list():
    file = input("File path: ")
    if os.path.exists(file):
        with open(file) as f:
            proxies = f.read().splitlines()
        asyncio.run(mass_check(proxies, config.data['timeout'], config.data['workers']))
    else:
        print("File not found")

def settings_menu():
    print("\n[1] Change timeout")
    print("[2] Change workers")
    print("[3] Toggle theme")
    print("[4] Clean results")
    print("[5] Back")
    choice = input("> ")
    if choice == '1':
        config.data['timeout'] = float(input(f"Timeout ({config.data['timeout']}): "))
    elif choice == '2':
        config.data['workers'] = int(input(f"Workers ({config.data['workers']}): "))
    elif choice == '3':
        config.data['theme'] = 'light' if config.data['theme'] == 'dark' else 'dark'
    elif choice == '4':
        clean_results()
    config.save()

def menu():
    clear()
    print(get_title())
    print("\n[1] Quick Check (200 proxies)")
    print("[2] Full Scan (All proxies)")
    print("[3] Custom List")
    print("[4] Settings")
    print("[5] Exit")
    return input("\n> ")

async def main():
    os.makedirs('logs', exist_ok=True)
    while True:
        choice = menu()
        if choice == '1':
            await quick_check()
        elif choice == '2':
            await full_scan()
        elif choice == '3':
            custom_list()
        elif choice == '4':
            settings_menu()
        elif choice == '5':
            sys.exit()
        input("\nPress ENTER to continue...")

if __name__ == "__main__":
    asyncio.run(main())