import asyncio
import aiohttp
import logging
import aiofiles
import json
import random
import os
import itertools
from aiohttp import ClientProxyConnectionError, ClientHttpProxyError, ServerDisconnectedError
from asyncio import TimeoutError

LOGGER = logging.getLogger()

OUTPUT_DIR = "/storage/output"
HTML_SOURCE_DIR = "/storage/html"

NO_PROXY = None

USER_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", #GOOGLE BOT,
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)", #BIG BOT
    "Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)", #Yahoo BOT
    "DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)", #DuckDuck BOT
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246", #Windows 10/ Edge browser
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36", #Windows 7/ Chrome browser
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9", #Mac OS X10/Safari browser
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1 ", #Linux PC/Firefox browser
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",

]
USER_AGENTS = itertools.cycle(USER_AGENTS)

class ProxyManager:
    dead_proxies = []

    async def get(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:5555/random") as r:
                    proxy = await r.text()
                    proxy = "http://" +proxy
                    if "443" in proxy or proxy in self.dead_proxies:
                        return await self.get_proxy()
                    return proxy
        except:
            return NO_PROXY

    def set_dead(self, proxy):
        self.dead_proxies.append(proxy)
PROXIES = ProxyManager()


class Requester:
    @classmethod
    async def get(cls, url):
        try:
            return await cls._send_request(url)
        except ProxyError:
            LOGGER.info("Retry request with another proxy")
            try:
                return await cls._send_request(url)
            except:
                pass

    @classmethod
    async def _send_request(cls, url):
        # await asyncio.sleep(random.random())
        params = {
                "timeout": 20,
                "headers": {'User-Agent': USER_AGENTS.__next__()}
            }

        proxy = await PROXIES.get()
        if proxy:
            params["proxy"] = proxy

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, **params) as response:
                    if response.status == 200:
                        html = await response.text()
                        LOGGER.info(f"request done: {url} \r\tproxy: {proxy}")
                        return html
                    LOGGER.warning(f"request fail with status {response.status}: {url}")
            except Exception as e:
                LOGGER.warning(f"Requet fail: {url}\n {proxy} \n"+str(e))
                raise ProxyError(str(e))
    

class StorageConfig:
    def __init__(self, root_dir=None):
        """
            /storage
                html
                output
                temp
                    question_stock
                    used
        """
        self.ROOT = root_dir if root_dir is not None else "/storage"
        self.HTML_SOURCE_DIR = os.path.join(self.ROOT, "html")
        self.OUTPUT_DIR = os.path.join(self.ROOT, "output")

        self.QUESTION_STOCK = os.path.join(self.ROOT, "temp/question_stock")
FILE_STORAGE_CONFIG = StorageConfig()


async def save_json(data, filename, root_dir=None):
    if not data:
        LOGGER.warning(f"No data to save into file {filename}")
        return

    root_dir = root_dir or FILE_STORAGE_CONFIG.OUTPUT_DIR
    out_file_path = os.path.join(root_dir, filename)

    dir_name = os.path.dirname(out_file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    async with aiofiles.open(out_file_path, mode="w", encoding="utf-8") as file:
        await file.write(json.dumps(data))
        LOGGER.info(f"output saved: {filename}")


async def save_html(data:str, filename, root_dir=None):
    if not data:
        LOGGER.warning(f"{filename} is empty, ignore")
        return 
        
    root_dir = root_dir or FILE_STORAGE_CONFIG.HTML_SOURCE_DIR
    out_file_path = os.path.join(root_dir, filename)

    dir_name = os.path.dirname(out_file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    async with aiofiles.open(out_file_path, mode="w", encoding="utf-8") as file:
        await file.write(data)
        LOGGER.info(f"page source saved: {filename}")


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i: i+n]


class ProxyError(Exception):
    pass




