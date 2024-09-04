import asyncio
import os
import random
from asyncio import Task
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (BrowserContext, BrowserType, Page,
                                  async_playwright)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
import store as xhs_store
from tools import utils
from var import crawler_type_var

from .client import XiaoHongShuClient
from .exception import DataFetchError
from .field import SearchSortType
from .login import XiaoHongShuLogin


class XiaoHongShuCrawler(AbstractCrawler):
    context_page: Page
    xhs_client: XiaoHongShuClient
    browser_context: BrowserContext

    def __init__(self) -> None:
        self.index_url = "https://www.xiaohongshu.com"
        # self.user_agent = utils.get_user_agent()
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    #启动爬虫
    async def start(self) -> None:
        #代理设置
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = self.format_proxy_info(ip_proxy_info)

        #启动浏览器
        async with async_playwright() as playwright:
            # Launch a browser context.
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium,
                None,
                self.user_agent,
                headless=config.HEADLESS#是否以无头模式（无UI）启动
            )
            # stealth.min.js is a js script to prevent the website from detecting the crawler.
            #为了防止网站检测到这是一个爬虫，浏览器上下文会加载一个 stealth.min.js 脚本，这个脚本可能会修改一些浏览器特性，以模仿真实用户的操作。
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
            # add a cookie attribute webId to avoid the appearance of a sliding captcha on the webpage
            #设置一个名为 webId 的 cookie，这个 cookie 可能用于绕过网站的滑动验证码机制
            await self.browser_context.add_cookies([{
                'name': "webId",
                'value': "xxx123",  # any value
                'domain': ".xiaohongshu.com",
                'path': "/"
            }])
            self.context_page = await self.browser_context.new_page()
            #打开小红书的首页
            await self.context_page.goto(self.index_url)

            # Create a client to interact with the xiaohongshu website.
            #创建一个与小红书交互的客户端
            self.xhs_client = await self.create_xhs_client(httpx_proxy_format)
            #测试客户端是否正常连接。如果测试失败，将触发登录逻辑。
            if not await self.xhs_client.pong():
                login_obj = XiaoHongShuLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # input your phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES
                )
                await login_obj.begin()
                await self.xhs_client.update_cookies(browser_context=self.browser_context)

            #根据配置文件中设置的爬虫类型
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                #执行关键词搜索并获取评论信息
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                #获取指定笔记的信息和评论
                await self.get_specified_notes()
            elif config.CRAWLER_TYPE == "creator":
                # Get creator's information and their notes and comments
                #获取创作者的信息及其笔记和评论
                await self.get_creators_and_notes()
            else:
                pass

            utils.logger.info("[XiaoHongShuCrawler.start] Xhs Crawler finished ...")

    #搜索功能
    async def search(self) -> None:
        """Search for notes and retrieve their comment information."""
        utils.logger.info("[XiaoHongShuCrawler.search] Begin search xiaohongshu keywords")
        xhs_limit_count = 20  # xhs limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < xhs_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = xhs_limit_count
        start_page = config.START_PAGE
        #关键词遍历
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[XiaoHongShuCrawler.search] Current search keyword: {keyword}")
            page = 1
            #分页处理，多页数据
            while (page - start_page + 1) * xhs_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:#如果当前页码小于开始页码，则跳过该页
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Skip page {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] search xhs keyword: {keyword}, page: {page}")
                    note_id_list: List[str] = []
                    #按照关键词获取笔记列表
                    notes_res = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        sort=SearchSortType(config.SORT_TYPE) if config.SORT_TYPE != '' else SearchSortType.GENERAL,
                    )
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Search notes res:{notes_res}")
                    #没有更多笔记，结束关键词搜索
                    if not notes_res or not notes_res.get('has_more', False):
                        utils.logger.info("No more content!")
                        break
                    #使用 asyncio.Semaphore 控制并发数，并通过 asyncio.gather 并发获取每篇笔记的详细信息
                    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                    task_list = [
                        self.get_note_detail_async_task(
                            note_id=post_item.get("id"),
                            xsec_source=post_item.get("xsec_source"),
                            xsec_token=post_item.get("xsec_token"),
                            semaphore=semaphore
                        )
                        for post_item in notes_res.get("items", {})
                        #只处理 model_type 不为 'rec_query' 或 'hot_query' 的笔记
                        #'rec_query' 和 'hot_query' 可能对应的是推荐或热门查询的笔记，这些笔记可能不属于真正的搜索结果，或不符合特定的业务逻辑
                        if post_item.get('model_type') not in ('rec_query', 'hot_query')
                    ]
                    note_details = await asyncio.gather(*task_list)
                    for note_detail in note_details:
                        if note_detail:
                            #将获取的笔记详情保存到数据库
                            await xhs_store.update_xhs_note(note_detail)
                            #如果启用了媒体获取功能，爬虫还会获取笔记中的图片和视频
                            await self.get_notice_media(note_detail)
                            #收集所有笔记的 ID，以便稍后获取这些笔记的评论
                            note_id_list.append(note_detail.get("note_id"))
                    page += 1
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Note details: {note_details}")
                    #批量获取所有笔记的评论
                    await self.batch_get_note_comments(note_id_list)
                #发生数据获取错误
                except DataFetchError:
                    utils.logger.error("[XiaoHongShuCrawler.search] Get note detail error")
                    break

    #获取创作者信息及其笔记
    async def get_creators_and_notes(self) -> None:
        """Get creator's notes and retrieve their comment information."""
        utils.logger.info("[XiaoHongShuCrawler.get_creators_and_notes] Begin get xiaohongshu creators")
        for user_id in config.XHS_CREATOR_ID_LIST:
            # get creator detail info from web html content
            createor_info: Dict = await self.xhs_client.get_creator_info(user_id=user_id)
            if createor_info:
                await xhs_store.save_creator(user_id, creator=createor_info)

            # Get all note information of the creator
            all_notes_list = await self.xhs_client.get_all_notes_by_creator(
                user_id=user_id,
                crawl_interval=random.random(),
                callback=self.fetch_creator_notes_detail
            )

            note_ids = [note_item.get("note_id") for note_item in all_notes_list]
            await self.batch_get_note_comments(note_ids)

    async def fetch_creator_notes_detail(self, note_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail_async_task(
                note_id=post_item.get("note_id"),
                xsec_source=post_item.get("xsec_source"),
                xsec_token=post_item.get("xsec_token"),
                semaphore=semaphore
            )
            for post_item in note_list
        ]

        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail:
                await xhs_store.update_xhs_note(note_detail)

    #获取指定笔记
    async def get_specified_notes(self):
        """Get the information and comments of the specified post"""

        async def get_note_detail_from_html_task(note_id: str, semaphore: asyncio.Semaphore) -> Dict:
            async with semaphore:
                try:
                    _note_detail: Dict = await self.xhs_client.get_note_by_id_from_html(note_id)
                    print("------------------------")
                    print(_note_detail)
                    print("------------------------")
                    if not _note_detail:
                        utils.logger.error(
                            f"[XiaoHongShuCrawler.get_note_detail_from_html] Get note detail error, note_id: {note_id}")
                        return {}
                    return _note_detail
                except DataFetchError as ex:
                    utils.logger.error(f"[XiaoHongShuCrawler.get_note_detail_from_html] Get note detail error: {ex}")
                    return {}
                except KeyError as ex:
                    utils.logger.error(
                        f"[XiaoHongShuCrawler.get_note_detail_from_html] have not fund note detail note_id:{note_id}, err: {ex}")
                    return {}

        get_note_detail_task_list = [
            get_note_detail_from_html_task(note_id=note_id, semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)) for
            note_id in config.XHS_SPECIFIED_ID_LIST
        ]

        need_get_comment_note_ids = []
        note_details = await asyncio.gather(*get_note_detail_task_list)
        for note_detail in note_details:
            if note_detail:
                need_get_comment_note_ids.append(note_detail.get("note_id"))
                await xhs_store.update_xhs_note(note_detail)
        await self.batch_get_note_comments(need_get_comment_note_ids)

    #获取笔记详细信息
    async def get_note_detail_async_task(self, note_id: str, xsec_source: str, xsec_token: str, semaphore: asyncio.Semaphore) -> \
            Optional[Dict]:
        """Get note detail"""
        async with semaphore:
            try:
                note_detail: Dict = await self.xhs_client.get_note_by_id(note_id, xsec_source, xsec_token)
                if not note_detail:
                    utils.logger.error(
                        f"[XiaoHongShuCrawler.get_note_detail_async_task] Get note detail error, note_id: {note_id}")
                    return None
                note_detail.update({"xsec_token": xsec_token, "xsec_source": xsec_source})
                return note_detail
            except DataFetchError as ex:
                utils.logger.error(f"[XiaoHongShuCrawler.get_note_detail_async_task] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail_async_task] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    #批量获取笔记评论
    async def batch_get_note_comments(self, note_list: List[str]):
        """Batch get note comments"""
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[XiaoHongShuCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(
            f"[XiaoHongShuCrawler.batch_get_note_comments] Begin batch get note comments, note list: {note_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_list:
            task = asyncio.create_task(self.get_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """Get note comments with keyword filtering and quantity limitation"""
        async with semaphore:
            utils.logger.info(f"[XiaoHongShuCrawler.get_comments] Begin get note id comments {note_id}")
            await self.xhs_client.get_note_all_comments(
                note_id=note_id,
                crawl_interval=random.random(),
                callback=xhs_store.batch_update_xhs_note_comments
            )

    #格式化代理服务器的信息
    @staticmethod
    def format_proxy_info(ip_proxy_info: IpInfoModel) -> Tuple[Optional[Dict], Optional[Dict]]:
        """format proxy info for playwright and httpx"""
        playwright_proxy = {
            "server": f"{ip_proxy_info.protocol}{ip_proxy_info.ip}:{ip_proxy_info.port}",
            "username": ip_proxy_info.user,
            "password": ip_proxy_info.password,
        }
        httpx_proxy = {
            f"{ip_proxy_info.protocol}": f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
        }
        return playwright_proxy, httpx_proxy

    #创建一个用于与小红书网站进行交互的客户端
    async def create_xhs_client(self, httpx_proxy: Optional[str]) -> XiaoHongShuClient:
        """Create xhs client"""
        utils.logger.info("[XiaoHongShuCrawler.create_xhs_client] Begin create xiaohongshu API client ...")
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())
        xhs_client_obj = XiaoHongShuClient(
            proxies=httpx_proxy,
            headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_str,
                "Origin": "https://www.xiaohongshu.com",
                "Referer": "https://www.xiaohongshu.com",
                "Content-Type": "application/json;charset=UTF-8"
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )
        return xhs_client_obj

    #启动浏览器并创建一个浏览器上下文
    async def launch_browser(
            self,
            chromium: BrowserType,
            playwright_proxy: Optional[Dict],
            user_agent: Optional[str],
            headless: bool = True
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        utils.logger.info("[XiaoHongShuCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            # feat issue #14
            # we will save login state to avoid login every time
            user_data_dir = os.path.join(os.getcwd(), "browser_data",
                                         config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent
            )
            return browser_context

    #关闭浏览器上下文，结束所有与网页的交互
    async def close(self):
        """Close browser context"""
        await self.browser_context.close()
        utils.logger.info("[XiaoHongShuCrawler.close] Browser context closed ...")

    #如果启用了 config.ENABLE_GET_IMAGES，这个方法将获取笔记的图片和视频
    async def get_notice_media(self, note_detail: Dict):
        if not config.ENABLE_GET_IMAGES:
            utils.logger.info(f"[XiaoHongShuCrawler.get_notice_media] Crawling image mode is not enabled")
            return
        await self.get_note_images(note_detail)
        await self.get_notice_video(note_detail)

    #获取笔记图片
    async def get_note_images(self, note_item: Dict):
        """
        get note images. please use get_notice_media
        :param note_item:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            return
        note_id = note_item.get("note_id")
        image_list: List[Dict] = note_item.get("image_list", [])

        for img in image_list:
            if img.get('url_default') != '':
                img.update({'url': img.get('url_default')})

        if not image_list:
            return
        picNum = 0
        for pic in image_list:
            url = pic.get("url")
            if not url:
                continue
            content = await self.xhs_client.get_note_media(url)
            if content is None:
                continue
            extension_file_name = f"{picNum}.jpg"
            picNum += 1
            await xhs_store.update_xhs_note_image(note_id, content, extension_file_name)

    #获取笔记视频
    async def get_notice_video(self, note_item: Dict):
        """
        get note images. please use get_notice_media
        :param note_item:
        :return:
        """
        if not config.ENABLE_GET_IMAGES:
            return
        note_id = note_item.get("note_id")

        videos = xhs_store.get_video_url_arr(note_item)

        if not videos:
            return
        videoNum = 0
        for url in videos:
            content = await self.xhs_client.get_note_media(url)
            if content is None:
                continue
            extension_file_name = f"{videoNum}.mp4"
            videoNum += 1
            await xhs_store.update_xhs_note_image(note_id, content, extension_file_name)
