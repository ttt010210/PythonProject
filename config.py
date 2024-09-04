# 基础配置
PLATFORM = "xhs"
KEYWORDS = "南京景点攻略"
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = ""
# 具体值参见media_platform.xxx.field下的枚举值
SORT_TYPE = "popularity_descending"
PUBLISH_TIME_TYPE = 0
CRAWLER_TYPE = "search"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2
# cache type
CACHE_TYPE_REDIS = "redis"
CACHE_TYPE_MEMORY = "memory"
# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
# 小红书如果一直扫码登录不通过，打开浏览器手动过一下滑动验证码
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 数据保存类型选项配置,支持三种类型：csv、json
SAVE_DATA_OPTION = "json"  # csv or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 10

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬图片模式, 默认不开启爬图片
ENABLE_GET_IMAGES = False

# 是否开启爬评论模式, 默认不开启爬评论
#此处为True，需要爬取评论才可以生成评论的词云图。
ENABLE_GET_COMMENTS = True

# 是否开启爬二级评论模式, 默认不开启爬二级评论
ENABLE_GET_SUB_COMMENTS = False

# 指定小红书需要爬虫的笔记ID列表
XHS_SPECIFIED_ID_LIST = [
    "6422c2750000000027000d88",
    # ........................
]
# 词云相关
# 是否开启生成评论词云图
ENABLE_GET_WORDCLOUD = True
# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
# CUSTOM_WORDS = {
#     '零几': '年份',  # 将“零几”识别为一个整体
#     '高频词': '专业术语'  # 示例自定义词
# }

# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    '夫子庙': '景点',
    '中山陵': '景点',
    '明孝陵': '景点',
    '玄武湖': '景点',
    '秦淮河': '景点',
    '总统府': '景点',
    '雨花台': '景点',
    '南京博物院': '景点',
    '南京长江大桥': '景点',
    '南京城墙': '景点',
    '莫愁湖': '景点',
    '栖霞山': '景点',
    '紫金山': '景点',
    '鸡鸣寺': '景点',
    '阅江楼': '景点',
    '梅园新村': '景点',
    '燕子矶': '景点',
    '甘熙故居': '景点',
    '中华门': '景点',
    '南京大屠杀遇难同胞纪念馆': '景点',
    '南京大学': '景点',
    '南京科技馆': '景点',
    '南京博物馆': '景点',
    '朝天宫': '景点',
    '南京植物园': '景点',
    '南京栖霞寺': '景点',
    '白鹭洲公园': '景点',
    '南京云锦博物馆': '景点',
    '南京眼步行桥': '景点',
    '侵华日军南京大屠杀遇难同胞纪念馆': '景点',
    '中山码头': '景点',
    '汤山温泉': '景点',
    '南京图书馆': '景点',
    '红山动物园': '景点',
    '鸭血粉丝汤': '美食',
    '盐水鸭': '美食',
    '烤鸭': '美食',
    '桂花糖芋苗': '美食',
    '皮肚面': '美食',
    '小笼包': '美食',
    '牛肉锅贴': '美食',
    '萝卜丝饼': '美食',
    '黄焖鸡米饭': '美食',
    '烧饼夹里脊': '美食',
    '鸭油酥烧饼': '美食'
}



# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"
