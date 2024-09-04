from asyncio.tasks import Task
from contextvars import ContextVar
from typing import List

import aiomysql

from async_db import AsyncMysqlDB

#用于在异步环境下管理状态或上下文。ContextVar 是 Python 中的一种变量类型，允许你在异步任务之间共享状态，而不需要明确地传递这些状态
request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
comment_tasks_var: ContextVar[List[Task]] = ContextVar("comment_tasks", default=[])
media_crawler_db_var: ContextVar[AsyncMysqlDB] = ContextVar("media_crawler_db_var")
db_conn_pool_var: ContextVar[aiomysql.Pool] = ContextVar("db_conn_pool_var")
