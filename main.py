import asyncio
import aiohttp
import random
import re
import time
import sys
from aiohttp_socks import ProxyConnector

# ====== НАСТРОЙКИ ======
# ЗАПОЛНИТЕ ЭТИ ДАННЫЕ ПЕРЕД ЗАПУСКОМ
CHANNEL_USERNAME = "tonxbio"  # Имя канала (без @)
POST_ID = "2"  # ID поста
VIEWS_PER_PROXY = 3  # Сколько просмотров отправлять с каждой прокси
MAX_CONCURRENT_REQUESTS = 50  # Максимум одновременных запросов
# =======================

# Список источников прокси
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

class SimpleTelegramViewBot:
    def __init__(self, channel, post_id):
        self.channel = channel
        self.post_id = post_id
        self.working_proxies = []
        self.test_url = f"https://t.me/{channel}/{post_id}?embed=1"
        
    async def fetch_proxies(self, session, url):
        """Получаем прокси из источника"""
        try:
            async with session.get(url, timeout=10) as response:
                text = await response.text()
                proxies = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+\b', text)
                return proxies
        except:
            return []
    
    async def get_proxies(self):
        """Собираем прокси"""
        print("[+] Ищу прокси...")
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            all_proxies = []
            for url in PROXY_SOURCES:
                try:
                    proxies = await self.fetch_proxies(session, url)
                    if proxies:
                        all_proxies.extend(proxies)
                        print(f"[+] Найдено {len(proxies)} прокси из {url}")
                except:
                    continue
        
        # Удаляем дубликаты и берем первые 100
        unique_proxies = list(set(all_proxies))[:100]
        
        if not unique_proxies:
            print("[!] Не удалось получить прокси. Использую запасные...")
            unique_proxies = [
                "45.81.76.241:8080", "47.243.124.34:8080", "43.156.3.229:8888",
                "47.243.242.70:8080", "45.81.76.156:8080", "8.219.97.248:80",
            ]
        
        print(f"[+] Всего прокси: {len(unique_proxies)}")
        return unique_proxies
    
    async def test_proxy(self, proxy):
        """Тестируем прокси"""
        try:
            connector = ProxyConnector.from_url(f"http://{proxy}")
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Получаем данные
                async with session.get(self.test_url, timeout=10) as response:
                    if response.status != 200:
                        return None
                    
                    text = await response.text()
                    
                    if 'data-view="' not in text:
                        return None
                    
                    key = text.split('data-view="')[1].split('"')[0]
                    
                    # Проверяем cookie
                    cookies = response.cookies
                    cookie_str = ""
                    for cookie in cookies:
                        if 'stel_ssid' in str(cookie):
                            cookie_str = f"stel_ssid={cookie.value}"
                            break
                    
                    if not cookie_str:
                        return None
                    
                    # Отправляем просмотр
                    view_url = f"{self.test_url}&view={key}"
                    view_headers = {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Referer': self.test_url,
                        'Cookie': cookie_str,
                    }
                    
                    async with session.get(view_url, headers=view_headers) as view_response:
                        if view_response.status == 200:
                            print(f"[+] Прокси {proxy} работает")
                            return proxy
        except:
            pass
        
        return None
    
    async def process_proxies(self, proxies):
        """Обрабатываем прокси"""
        print("[+] Тестирую прокси...")
        
        tasks = []
        for proxy in proxies:
            task = asyncio.create_task(self.test_proxy(proxy))
            tasks.append(task)
            
            # Ограничиваем количество одновременных запросов
            if len(tasks) >= MAX_CONCURRENT_REQUESTS:
                results = await asyncio.gather(*tasks)
                for result in results:
                    if result:
                        self.working_proxies.append(result)
                tasks = []
        
        # Обрабатываем оставшиеся задачи
        if tasks:
            results = await asyncio.gather(*tasks)
            for result in results:
                if result:
                    self.working_proxies.append(result)
        
        print(f"[+] Найдено {len(self.working_proxies)} рабочих прокси")
    
    async def send_views(self):
        """Отправляем просмотры"""
        if not self.working_proxies:
            print("[!] Нет рабочих прокси!")
            return
        
        print(f"[+] Начинаю отправку просмотров...")
        total_views = 0
        
        for proxy in self.working_proxies:
            for i in range(VIEWS_PER_PROXY):
                try:
                    connector = ProxyConnector.from_url(f"http://{proxy}")
                    timeout = aiohttp.ClientTimeout(total=15)
                    
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        # Получаем данные
                        async with session.get(self.test_url) as response:
                            if response.status != 200:
                                continue
                            
                            text = await response.text()
                            
                            if 'data-view="' not in text:
                                continue
                            
                            key = text.split('data-view="')[1].split('"')[0]
                            cookies = response.cookies
                            
                            cookie_str = ""
                            for cookie in cookies:
                                if 'stel_ssid' in str(cookie):
                                    cookie_str = f"stel_ssid={cookie.value}"
                                    break
                            
                            if not cookie_str:
                                continue
                            
                            # Отправляем просмотр
                            view_url = f"{self.test_url}&view={key}"
                            view_headers = {
                                'X-Requested-With': 'XMLHttpRequest',
                                'Referer': self.test_url,
                                'Cookie': cookie_str,
                            }
                            
                            async with session.get(view_url, headers=view_headers) as view_response:
                                if view_response.status == 200:
                                    total_views += 1
                                    print(f"[+] Просмотр #{total_views} отправлен через {proxy}")
                                    
                                    # Задержка между запросами
                                    await asyncio.sleep(random.uniform(1, 3))
                
                except:
                    continue
        
        return total_views
    
    async def run(self):
        """Основная функция"""
        print("=" * 50)
        print("Telegram View Bot")
        print(f"Канал: @{self.channel}")
        print(f"Пост: {self.post_id}")
        print("=" * 50)
        print()
        
        # Получаем прокси
        proxies = await self.get_proxies()
        
        # Тестируем прокси
        await self.process_proxies(proxies)
        
        # Отправляем просмотры
        total_views = await self.send_views()
        
        print()
        print("=" * 50)
        print(f"Готово! Отправлено просмотров: {total_views}")
        print("=" * 50)

def main():
    """Точка входа"""
    print("Запуск Telegram View Bot...")
    
    # Проверяем настройки
    if CHANNEL_USERNAME == "ваш_канал" or not CHANNEL_USERNAME:
        print("ОШИБКА: Заполните настройки в коде!")
        print("1. Откройте файл telegram_view_bot.py")
        print("2. Найдите строки:")
        print("   CHANNEL_USERNAME = 'ваш_канал'")
        print("   POST_ID = '1234'")
        print("3. Замените на ваши данные")
        return
    
    # Запускаем бота
    bot = SimpleTelegramViewBot(CHANNEL_USERNAME, POST_ID)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nСкрипт остановлен")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
