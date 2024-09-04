import asyncio
import json
import logging
from collections import Counter

import aiofiles
import jieba
import matplotlib.pyplot as plt
from wordcloud import WordCloud

import config
from tools import utils

plot_lock = asyncio.Lock()


class AsyncWordCloudGenerator:
    def __init__(self):
        logging.getLogger('jieba').setLevel(logging.WARNING)
        self.stop_words_file = config.STOP_WORDS_FILE
        self.lock = asyncio.Lock()
        self.stop_words = self.load_stop_words()
        self.custom_words = config.CUSTOM_WORDS
        self.tokenizer = jieba.Tokenizer()

        # 将自定义词汇添加到 jieba 的分词器中
        for word in self.custom_words.keys():
            self.tokenizer.add_word(word)

    def load_stop_words(self):
        with open(self.stop_words_file, 'r', encoding='utf-8') as f:
            return set(f.read().strip().split('\n'))

    async def generate_word_frequency_and_cloud(self, data, save_words_prefix):
        # 将 data 列表中所有条目的 content 字段合并成一个字符串 all_text
        all_text = ' '.join(item['content'] for item in data)

        # 使用 jieba 的分词器进行分词，并过滤停用词和不在自定义词汇中的词
        words = [
            word for word in self.tokenizer.lcut(all_text)
            if word in self.custom_words.keys() and word not in self.stop_words and len(word.strip()) > 0
        ]

        # 计算词频
        word_freq = Counter(words)

        # 保存词频
        freq_file = f"{save_words_prefix}_word_freq.json"
        async with aiofiles.open(freq_file, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(word_freq, ensure_ascii=False, indent=4))

        # 生成词云图片
        # 确保在同一时间只有一个任务在生成词云图片
        if plot_lock.locked():
            utils.logger.info("Skipping word cloud generation as the lock is held.")
            return

        await self.generate_word_cloud(word_freq, save_words_prefix)

    async def generate_word_cloud(self, word_freq, save_words_prefix):
        await plot_lock.acquire()
        print("生成词云")
        # 选择所有自定义词汇的词频
        custom_word_freq = {word: freq for word, freq in word_freq.items() if word in self.custom_words.keys()}

        wordcloud = WordCloud(
            font_path=config.FONT_PATH,
            width=800,
            height=400,
            background_color='white',
            max_words=20,
            stopwords=self.stop_words,
            colormap='viridis',
            contour_color='steelblue',
            contour_width=1
        ).generate_from_frequencies(custom_word_freq)

        # 保存词云图片
        plt.figure(figsize=(10, 5), facecolor='white')
        plt.imshow(wordcloud, interpolation='bilinear')

        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(f"{save_words_prefix}_word_cloud.png", format='png', dpi=300)
        plt.close()

        plot_lock.release()


