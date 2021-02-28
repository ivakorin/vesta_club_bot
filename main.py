#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import sqlite3

import requests
import yaml
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, User
from bs4 import BeautifulSoup
import logging
from os import path

basedir = path.abspath(path.dirname(__file__))

class DB:
    def __init__(self, db_name=path.join(basedir, 'data.db')):
        self.connect = sqlite3.connect(db_name)
        self.cursor = self.connect.cursor()

    def install_tables(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS data(id INT PRIMARY KEY DEFAULT 1, last_news TEXT, content '
                            'TEXT, url TEXT);')
        self.connect.commit()

    def update_data(self, *data):
        self.cursor.execute('INSERT OR REPLACE INTO data VALUES (1, ?, ?, ?);', data)
        # self.cursor.execute('INSERT OR REPLACE INTO data(id, ' + column + ') VALUES(1, "' + data + '");')
        self.connect.commit()

    def read_data(self, data):
        self.cursor.execute('SELECT ' + data + ' FROM data WHERE id=1;')
        result = self.cursor.fetchone()
        if result is None:
            return None
        else:
            return result[0]


class Config:
    def __init__(self):
        self.config = yaml.load(open(path.join(basedir, 'config.yaml')), Loader=yaml.Loader)
        self.config_location = path.join(basedir, 'config.yaml')

    def get_config_value(self, value):
        result = self.config['config'][str(value)]
        return result


class LadaOnline:
    def __init__(self, host="https://лада.онлайн/", url="auto-news/lada-vesta-news/"):
        self.host = host
        self.url = url
        self.response = requests.get(host + url)
        self.soup = BeautifulSoup(self.response.text, 'lxml')
        self.news = self.soup.find(id="dle-content")
        self.dbase = DB()

    def __headers(self):
        result = self.news.find('h3').text
        return result

    def __content(self):
        c = self.news.find_all('td')
        result = c[1].text.replace('Подробнее', '')
        return result

    def __image(self):
        images = self.news.find_all('img')
        image_src = images[0]['src']
        s = image_src[image_src.find("=") + 1:]
        result = '&w'.join(s.split('&w')[:-1])
        return result

    def __news_url(self):
        news_url = self.news.find_all('a')
        result = news_url[0]['href']
        return result

    def __msg(self):
        title = self.__headers()
        last_wrote_title = self.dbase.read_data('last_news')
        if last_wrote_title is None or title != last_wrote_title:
            content = self.__content()
            url = self.__headers()
            self.dbase.update_data(title, content, url)
        else:
            content = self.dbase.read_data('content')
            title = last_wrote_title
        result = r'*Новость c сайта лада.онлайн*' + '\n' + '*' + title + '*' + '\n' + content
        return result

    def __fresh(self):
        title = self.__headers()
        last_wrote_title = self.dbase.read_data('last_news')
        if title != last_wrote_title:
            return True
        else:
            return False

    def data(self):
        fresh = self.__fresh()
        msg = self.__msg()
        url = self.__news_url()
        img = self.__image()
        result = {'msg': msg, 'url': url, 'img': img, 'fresh': fresh}
        return result


class VK:
    def __init__(self):
        t = Config()
        self.token = str(t.get_config_value('vk_token'))
        self.group = str(t.get_config_value('vk_group_id'))
        self.topic = str(t.get_config_value('vk_topic_id'))

    def getrules(self):
        r = 'https://api.vk.com/method/board.getComments?group_id=' + self.group + '&topic_id=' + self.topic + \
            '&need_likes=0&count=2&extended=1&access_token=' + self.token + '&v=5.130 '
        print(r)
        respond = requests.get(r).json()
        result = respond['response']["items"][0]["text"]
        return result

    def link_to_rules(self):
        url = 'https://vk.com/topic'
        result = url + '-' + self.group + '_' + self.topic
        return result


# Test bot token 1558121095:AAHO71rediKKdjqPe9jsveSmrkEfPMJBLW8
# Prod bot token 1665950041:AAGBfPUmXZXShhG8vY7_NmtVi4m6eCyU-J0
t = Config()
token = t.get_config_value('token')
update_time = t.get_config_value('update_time')
bot = Bot(token=token)
dp = Dispatcher(bot)

#logging.basicConfig(level=logging.DEBUG)


async def checknews():
    conf = Config()
    chat_id = conf.get_config_value('chat_id')
    c = LadaOnline()
    data = c.data()
    inline_btn_1 = InlineKeyboardButton('Подробнее', data['url'])
    inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)

    if data['fresh'] is True:
        # 1001365037048
        await bot.send_photo(chat_id, types.InputFile.from_url(data['img']), data['msg'], parse_mode="MARKDOWN",
                             reply_markup=inline_kb1)


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


@dp.message_handler(commands=['rules'])
async def send_welcome(message: types.Message):
    vk = VK()
    rules = vk.getrules()
    link_to_rules = vk.link_to_rules()
    msg = rules + '\nСсылка: ' + link_to_rules
    await message.reply(msg)


@dp.message_handler(commands=['news'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    c = LadaOnline()
    data = c.data()
    inline_btn_1 = InlineKeyboardButton('Подробнее', data['url'])
    inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
    # '250484890'
    await bot.send_photo(message.from_user.id, types.InputFile.from_url(data['img']), data['msg'],
                         parse_mode="MARKDOWN",
                         reply_markup=inline_kb1)


@dp.message_handler(content_types=["new_chat_members"])
async def newuser(message: types.Message):
    vk = VK()
    link_to_rules = vk.link_to_rules()
    user = message.new_chat_members[0].first_name
    msg = 'Привет, ' + user + '!\nМы рады преветствовать тебя в нашем чате!\nНо прежде чем начать общение, пожалуйста ' \
                              'ознакомься с правилами вызвав команду /rules или можешь почитать их по ссылке:' + \
          link_to_rules + '\nПриятного общения! '
    await message.reply(msg)


@dp.message_handler(content_types=["left_chat_member"])
async def leftuser(message: types.Message):
    await bot.send_message(
        message.chat.id, 'Теряем бойцов, капитан!')


if __name__ == '__main__':
    data_base = DB()
    data_base.install_tables()
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled(update_time))
    executor.start_polling(dp, skip_updates=True)
