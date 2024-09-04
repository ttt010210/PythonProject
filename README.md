**小红书爬虫**
抓取小红书的视频、图片、评论、点赞、转发等信息。

原理：利用[playwright](https://playwright.dev/)搭桥，保留登录成功后的上下文浏览器环境，通过执行JS表达式获取一些加密参数
通过使用此方式，免去了复现核心加密JS代码，逆向难度大大降低

## 项目代码结构

```
pythonClass
├── base 
│   └── base_crawler.py         # 项目的抽象类
├── browser_data                # 换成用户的浏览器数据目录 
├── config.py                   # 基础配置
├── data                        # 数据保存目录 
│   ├── json                    # 原本的评论内容在json文件夹下
│   ├── words                   # 其中json为词频统计文件，png为词云图
├── docs
│   ├── hit_stopwords.txt       #输入禁用词(注意一个词语一行)
│   ├──STZHONGS.TTF             #中文字体文件
├── libs 
│   └── stealth.min.js          # 去除浏览器自动化特征的JS
├── media_platform              # 小红书crawler实现
├── tools
│   ├── utils.py                # 暴露给外部的工具函数
│   ├── crawler_util.py         # 爬虫相关的工具函数
│   ├── slider_util.py          # 滑块相关的工具函数
│   ├── time_util.py            # 时间相关的工具函数
│   ├── easing.py               # 模拟滑动轨迹相关的函数
|   └── words.py				# 生成词云图相关的函数
├── main.py                     # 程序入口
├── var.py                      # 上下文变量定义
└── recv_sms_notification.py    # 短信转发器的HTTP SERVER接口
```


## 使用方法
### 安装依赖库

   ```shell
   pip install -r requirements.txt
   ```

### 安装 playwright浏览器驱动

   ```shell
   playwright install
   ```

### 运行爬虫程序

   ```shell
   ### 项目默认是没有开启评论爬取模式，如需评论请在config/base_config.py中的 ENABLE_GET_COMMENTS 变量修改
   ### 一些其他支持项，也可以在config/base_config.py查看功能，写的有中文注释
   
   # 从配置文件中读取关键词搜索相关的帖子并爬取帖子信息与评论
   python main.py --platform xhs --lt qrcode --type search
   
   # 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
   python main.py --platform xhs --lt qrcode --type detail
  
   # 打开对应APP扫二维码登录 
   ```

### 数据保存
- 支持保存到csv中（data/目录下）
- 支持保存到json中（data/目录下）