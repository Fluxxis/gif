import asyncio
import aiohttp
import random
import re
import time
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
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
]

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
]

class TelegramViewBot:
    def __init__(self, channel, post_id):
        self.channel = channel
        self.post_id = post_id
        self.working_proxies = []
        self.test_url = f"https://t.me/{channel}/{post_id}?embed=1"
        self.total_views = 0
        self.failed_proxies = 0
        
    def print_stats(self):
        """Вывод статистики"""
        print(f"\n{'='*50}")
        print(f"📊 СТАТИСТИКА:")
        print(f"   Канал: @{self.channel}")
        print(f"   Пост: {self.post_id}")
        print(f"   Рабочих прокси: {len(self.working_proxies)}")
        print(f"   Отправлено просмотров: {self.total_views}")
        print(f"   Не рабочих прокси: {self.failed_proxies}")
        print(f"{'='*50}\n")
    
    async def fetch_proxies(self, session, url):
        """Получаем прокси из источника"""
        try:
            async with session.get(url, timeout=10, headers={'User-Agent': random.choice(USER_AGENTS)}) as response:
                if response.status == 200:
                    text = await response.text()
                    # Ищем паттерны IP:PORT
                    proxies = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+\b', text)
                    return proxies
        except Exception as e:
            print(f"[-] Ошибка получения прокси из {url}: {str(e)[:50]}")
        return []
    
    async def get_all_proxies(self):
        """Собираем прокси со всех источников"""
        print("[🔄] Ищу прокси в интернете...")
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_proxies(session, url) for url in PROXY_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        all_proxies = []
        for i, proxy_list in enumerate(results):
            if isinstance(proxy_list, list):
                all_proxies.extend(proxy_list)
                if proxy_list:
                    print(f"[+] Найдено {len(proxy_list)} прокси из источника {i+1}")
        
        # Удаляем дубликаты
        unique_proxies = list(set(all_proxies))
        
        if not unique_proxies:
            print("[⚠️] Не удалось получить прокси из интернета. Использую резервный список...")
            # Резервные прокси
            unique_proxies = [
                "45.81.76.241:8080", "47.243.124.34:8080", "43.156.3.229:8888",
                "47.243.242.70:8080", "45.81.76.156:8080", "8.219.97.248:80",
                "8.213.128.6:8080", "8.213.128.90:8080", "47.243.242.70:8080",
                "47.243.242.114:8080", "47.243.242.114:8080", "8.213.128.90:8080"
            ]
        
        print(f"[✅] Всего собрано {len(unique_proxies)} уникальных прокси")
        return unique_proxies
    
    async def test_proxy(self, proxy):
        """Тестируем прокси на работоспособность с Telegram"""
        try:
            connector = ProxyConnector.from_url(f"http://{proxy}")
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Первый запрос - получаем cookie и key
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                }
                
                async with session.get(self.test_url, headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    text = await response.text()
                    
                    # Проверяем, что пост существует
                    if 'data-view="' not in text:
                        print(f"[-] Пост не найден или недоступен: {self.test_url}")
                        return None
                    
                    key = text.split('data-view="')[1].split('"')[0]
                    cookies = response.cookies
                    
                    # Ищем stel_ssid в cookies
                    cookie_str = ""
                    for cookie in cookies:
                        if 'stel_ssid' in str(cookie):
                            cookie_str = f"stel_ssid={cookie.value}"
                            break
                    
                    if not cookie_str:
                        return None
                    
                    # Второй запрос - отправляем просмотр
                    view_url = f"{self.test_url}&view={key}"
                    view_headers = {
                        'User-Agent': random.choice(USER_AGENTS),
                        'X-Requested-With': 'XMLHttpRequest',
                        'Referer': self.test_url,
                        'Cookie': cookie_str,
                        'Accept': '*/*',
                    }
                    
                    async with session.get(view_url, headers=view_headers) as view_response:
                        if view_response.status == 200:
                            print(f"[✅] Прокси {proxy} работает!")
                            return proxy
        except Exception:
            pass
        
        return None
    
    async def process_proxies(self, proxies):
        """Обрабатываем прокси с ограничением на одновременные запросы"""
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        async def worker(proxy):
            async with semaphore:
                result = await self.test_proxy(proxy)
                if result:
                    self.working_proxies.append(result)
                    return True
                else:
                    self.failed_proxies += 1
                    return False
        
        print(f"[🔄] Тестирую {len(proxies)} прокси...")
        
        tasks = [worker(proxy) for proxy in proxies[:300]]  # Тестируем первые 300 прокси
        results = await asyncio.gather(*tasks)
        
        working_count = sum(1 for r in results if r)
        print(f"[✅] Найдено {working_count} рабочих прокси из {len(proxies[:300])}")
        
        return working_count > 0
    
    async def send_view(self, proxy, attempt=1):
        """Отправляет один просмотр через указанный прокси"""
        try:
            connector = ProxyConnector.from_url(f"http://{proxy}")
            timeout = aiohttp.ClientTimeout(total=15)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Получаем данные для просмотра
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                }
                
                async with session.get(self.test_url, headers=headers) as response:
                    if response.status != 200:
                        return False
                    
                    text = await response.text()
                    
                    if 'data-view="' not in text:
                        return False
                    
                    key = text.split('data-view="')[1].split('"')[0]
                    cookies = response.cookies
                    
                    cookie_str = ""
                    for cookie in cookies:
                        if 'stel_ssid' in str(cookie):
                            cookie_str = f"stel_ssid={cookie.value}"
                            break
                    
                    if not cookie_str:
                        return False
                    
                    # Отправляем просмотр
                    view_url = f"{self.test_url}&view={key}"
                    view_headers = {
                        'User-Agent': random.choice(USER_AGENTS),
                        'X-Requested-With': 'XMLHttpRequest',
                        'Referer': self.test_url,
                        'Cookie': cookie_str,
                        'Accept': '*/*',
                    }
                    
                    async with session.get(view_url, headers=view_headers) as view_response:
                        if view_response.status == 200:
                            self.total_views += 1
                            return True
        except Exception:
            if attempt < 2:  # Пробуем еще раз
                await asyncio.sleep(1)
                return await self.send_view(proxy, attempt + 1)
        
        return False
    
    async def run_view_attack(self):
        """Запускает атаку просмотрами"""
        print(f"[🎯] Начинаю накрутку просмотров...")
        print(f"[🎯] Цель: @{self.channel}/{self.post_id}")
        print(f"[🎯] Просмотров с каждой прокси: {VIEWS_PER_PROXY}")
        
        if not self.working_proxies:
            print("[⚠️] Нет рабочих прокси для атаки!")
            return
        
        attack_start_time = time.time()
        successful_views = 0
        
        # Создаем задачи для отправки просмотров
        tasks = []
        for proxy in self.working_proxies:
            for _ in range(VIEWS_PER_PROXY):
                task = asyncio.create_task(self.send_view(proxy))
                tasks.append(task)
                
                # Ограничиваем скорость создания задач
                await asyncio.sleep(0.05)
        
        # Ждем завершения всех задач
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Считаем успешные просмотры
        successful_views = sum(1 for r in results if r is True)
        
        attack_time = time.time() - attack_start_time
        print(f"\n[🎉] АТАКА ЗАВЕРШЕНА!")
        print(f"[⏱️] Время выполнения: {attack_time:.2f} секунд")
        print(f"[👁️] Успешных просмотров: {successful_views}")
        
        # Сохраняем рабочие прокси в файл для будущего использования
        if self.working_proxies:
            with open('working_proxies.txt', 'w') as f:
                for proxy in self.working_proxies:
                    f.write(f"{proxy}\n")
            print(f"[💾] Рабочие прокси сохранены в 'working_proxies.txt'")
    
    async def main(self):
        """Основная функция"""
        print_banner()
        
        # Проверяем настройки
        if not CHANNEL_USERNAME or not POST_ID:
            print("[❌] ОШИБКА: Заполните настройки в начале скрипта!")
            print("     CHANNEL_USERNAME и POST_ID не могут быть пустыми")
            return
        
        print(f"[🚀] Запуск Telegram View Bot")
        print(f"[📺] Канал: @{CHANNEL_USERNAME}")
        print(f"[📝] Пост ID: {POST_ID}")
        print(f"[⚙️] Ограничение одновременных запросов: {MAX_CONCURRENT_REQUESTS}")
        print(f"[🔁] Просмотров с прокси: {VIEWS_PER_PROXY}")
        print(f"[⏳] Начинаю через 3 секунды...\n")
        
        await asyncio.sleep(3)
        
        # Получаем прокси
        all_proxies = await self.get_all_proxies()
        
        if not all_proxies:
            print("[❌] Не удалось получить прокси. Завершение работы.")
            return
        
        # Тестируем прокси
        has_working_proxies = await self.process_proxies(all_proxies)
        
        if not has_working_proxies:
            print("[❌] Нет рабочих прокси. Завершение работы.")
            return
        
        self.print_stats()
        
        # Запускаем атаку
        await self.run_view_attack()
        
        # Финальная статистика
        print("\n" + "="*60)
        print("🎊 ФИНАЛЬНАЯ СТАТИСТИКА 🎊")
        print("="*60)
        print(f"   Целевой канал: @{CHANNEL_USERNAME}")
        print(f"   ID поста: {POST_ID}")
        print(f"   Всего прокси получено: {len(all_proxies)}")
        print(f"   Рабочих прокси: {len(self.working_proxies)}")
        print(f"   Не рабочих прокси: {self.failed_proxies}")
        print(f"   Отправлено просмотров: {self.total_views}")
        print(f"   Теоретический максимум: {len(self.working_proxies) * VIEWS_PER_PROXY}")
        print("="*60)
        print("\n[✅] Скрипт завершил работу успешно!")

def print_banner():
    """Красивый баннер"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║    ████████╗███████╗ █████╗ ██████╗ ██████╗  █████╗ ███╗   ║
║    ╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗████╗  ║
║       ██║   █████╗  ███████║██████╔╝██║  ██║███████║██╔██╗ ║
║       ██║   ██╔══╝  ██╔══██║██╔══██╗██║  ██║██╔══██║██║╚██╗║
║       ██║   ███████╗██║  ██║██║  ██║██████╔╝██║  ██║██║ ╚██╗║
║       ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝║
║                                                           ║
║                   V I E W   B O T                         ║
║           Автоматическая накрутка просмотров              ║
╚═══════════════════════════════════════════════════════════╝
    """)

# Запуск скрипта
if __name__ == "__main__":
    # Проверяем зависимости
    try:
        import aiohttp_socks
    except ImportError:
        print("\n[❌] ОШИБКА: Не установлены необходимые библиотеки!")
        print("[🔧] Установите зависимости командой:")
        print("     pip install aiohttp aiohttp_socks")
        exit(1)
    
    # Создаем и запускаем бота
    bot = TelegramViewBot(CHANNEL_USERNAME, POST_ID)
    
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print("\n\n[⚠️] Скрипт остановлен пользователем (Ctrl+C)")
        bot.print_stats()
    except Exception as e:
        print(f"\n[❌] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
