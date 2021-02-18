#!/usr/bin/env python
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import asyncio
import yaml
import sqlite3


class DB:
    def __init__(self):
        self.connect = sqlite3.connect('data.db')
        self.cursor = self.connect.cursor()

    def install_tables(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS data(id INT PRIMARY KEY DEFAULT 1, last_news TEXT);')
        self.connect.commit()

    def update_data(self, column, data):
        self.cursor.execute('INSERT OR REPLACE INTO data(id, ' + column + ') VALUES(1, "' + data + '");')
        self.connect.commit()

    def read_data(self, data):
        self.cursor.execute('SELECT ' + data + ' FROM data WHERE id=1;')
        result = self.cursor.fetchone()
        return result[0]


class Config:
    def __init__(self):
        self.config = yaml.load(open('config.yaml'), Loader=yaml.Loader)
        self.config_location = 'config.yaml'

    def get_config_value(self, value):
        result = self.config['config'][str(value)]
        return result


class LadaOnline:
    def __init__(self, host="https://лада.онлайн/", url="auto-news/lada-vesta-news/"):
        self.host = host
        self.url = url
        self.response = requests.get(host+url)
        self.soup = BeautifulSoup(self.response.text, 'lxml')
        self.news = self.soup.find(id="dle-content")

    def headers(self):
        result = self.news.find('h3').text
        return result

    def content(self):
        c = self.news.find_all('td')
        result = c[1].text.replace('Подробнее', '')
        return result

    def image(self):
        images = self.news.find_all('img')
        image_src = images[0]['src']
        s = image_src[image_src.find("=") + 1:]
        result = '&w'.join(s.split('&w')[:-1])
        return result

    def news_url(self):
        news_url = self.news.find_all('a')
        result = news_url[0]['href']
        return result


# Test bot token 1558121095:AAHO71rediKKdjqPe9jsveSmrkEfPMJBLW8
# Prod bot token 1665950041:AAGBfPUmXZXShhG8vY7_NmtVi4m6eCyU-J0
t = Config()
token = t.get_config_value('token')
bot = Bot(token=token)
dp = Dispatcher(bot)


# logging.basicConfig(level=logging.DEBUG)


async def checknews():
    c = LadaOnline()
    title = c.headers()
    conf = Config()
    data = DB()
    chat_id = conf.get_config_value('chat_id')
    last_wrote_title = data.read_data('last_news')
    if title != last_wrote_title:
        msg = r'*Новость c сайта лада.онлайн*' + '\n' + '*' + c.headers() + '*' + '\n' + c.content()
        inline_btn_1 = InlineKeyboardButton('Подробнее', c.news_url())
        inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
        # 1001365037048
        await bot.send_photo(chat_id, types.InputFile.from_url(c.image()), msg, parse_mode="MARKDOWN",
                             reply_markup=inline_kb1)
        data.update_data('last_news', title)


async def scheduled(wait_for):
    while True:
        await asyncio.sleep(wait_for)
        await checknews()


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply(
        "Привет! Этот бот рассылает уведомления о новостях с сайта лада.онлайн. Для более подробной информации "
        "используйте опцию /help")


@dp.message_handler(commands=['help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await message.reply("Бот не доступен для общего пользования")


@dp.message_handler(commands=['news'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    c = LadaOnline()
    msg = r'*Новость c сайта лада.онлайн*' + '\n' + '*' + c.headers() + '*' + '\n' + c.content()
    inline_btn_1 = InlineKeyboardButton('Подробнее', c.news_url())
    inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
    # '250484890'
    await bot.send_photo(message.from_user.id, types.InputFile.from_url(c.image()), msg, parse_mode="MARKDOWN",
                         reply_markup=inline_kb1)


if __name__ == '__main__':
    db = DB()
    db.install_tables()
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled(1800))
    executor.start_polling(dp, skip_updates=True)
