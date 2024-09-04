import asyncio
import sys

import cmd_arg
import config
from base.base_crawler import AbstractCrawler

from media_platform import XiaoHongShuCrawler

#这个类用于根据指定的平台名称创建相应的爬虫实例
class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError("Invalid Media Platform Currently only supported xhs")
        return crawler_class()


async def main():
    # parse cmd解析命令行参数
    await cmd_arg.parse_cmd()

    # init db初始化数据库:
    if config.SAVE_DATA_OPTION == "db":
        await db.init_db()

    #创建并启动爬虫
    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()

    #关闭数据库连接
    if config.SAVE_DATA_OPTION == "db":
        await db.close()


if __name__ == '__main__':
    try:
        # asyncio.run(main())使用了asyncio库来管理异步任务，
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
