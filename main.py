#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import logging
import sqlite3
import string
from os import path
import re

import requests
import yaml
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup

basedir = path.abspath(path.dirname(__file__))

from error_codes import ErrorCodes


# logging.basicConfig(level=logging.DEBUG)


class DB:
    def __init__(self, db_name=path.join(basedir, 'data.db')):
        self.connect = sqlite3.connect(db_name)
        self.cursor = self.connect.cursor()

    def install_tables(self):
        self.cursor.executescript('''CREATE TABLE IF NOT EXISTS data(id INTEGER PRIMARY KEY DEFAULT 1, last_news 
        TEXT, content TEXT, url TEXT); CREATE TABLE IF NOT EXISTS wall_posts(id INTEGER PRIMARY KEY AUTOINCREMENT NOT 
        NULL, post_id INTEGER); CREATE TABLE IF NOT EXISTS rules_requests(id INTEGER PRIMARY KEY AUTOINCREMENT NOT 
        NULL, last_post_date INTEGER, last_r_user_id INTEGER, message_id, INTEGER);
        ''')
        self.connect.commit()

    def update_data(self, *data):
        self.cursor.execute('INSERT OR REPLACE INTO data VALUES (1, ?, ?, ?);', data)
        self.connect.commit()

    def read_data(self, data, table, id):
        self.cursor.execute('SELECT ' + data + ' FROM ' + table + ' WHERE id=' + str(id) + ';')
        result = self.cursor.fetchone()
        if result is None:
            return None
        else:
            return result[0]

    def write_post(self, post_id):
        self.cursor.execute('INSERT INTO wall_posts(post_id) VALUES(' + str(post_id) + ');')
        self.connect.commit()

    def read_posts(self, data, table, id):
        self.cursor.execute('SELECT ' + data + ' FROM ' + table + ' WHERE post_id=' + str(id) + ';')
        result = self.cursor.fetchone()
        if result is None:
            return None
        else:
            return result[0]

    def write_rules_request_data(self, data):
        self.cursor.execute('INSERT OR REPLACE INTO rules_requests VALUES (1, ?, ?, ?);', data)
        self.connect.commit()

    def read_rules_request_data(self, data):
        self.cursor.execute('SELECT ' + str(data) + ' FROM rules_requests;')
        result = self.cursor.fetchone()
        if result is None:
            return None
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
        last_wrote_title = self.dbase.read_data('last_news', 'data', 1)
        if last_wrote_title is None or title != last_wrote_title:
            content = self.__content()
            url = self.__headers()
            self.dbase.update_data(title, content, url)
        else:
            content = self.dbase.read_data('content', 'data', 1)
            title = last_wrote_title
        result = r'*Новость c сайта лада.онлайн*' + '\n' + '*' + title + '*' + '\n' + content
        return result

    def __fresh(self):
        title = self.__headers()
        last_wrote_title = self.dbase.read_data('last_news', 'data', 1)
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

    def get_rules(self):
        vk_method = 'board.getComments'
        r = 'https://api.vk.com/method/' + vk_method + '?access_token=' + self.token + '&group_id=' + self.group + \
            '&topic_id=' + self.topic + '&need_likes=0&count=2&extended=1&v=5.130'
        respond = requests.get(r).json()
        result = respond['response']["items"][0]["text"]
        return result

    def link_to_rules(self):
        url = 'https://vk.com/topic'
        result = url + '-' + self.group + '_' + self.topic
        return result

    def last_wall_posts(self):
        db = DB()
        vk_method = 'wall.get'
        r = 'https://api.vk.com/method/' + vk_method + '?access_token=' + self.token + '&owner_id=-' + self.group + \
            '&count=2&extended=1&v=5.130&lang=ru'
        respond = requests.get(r).json()
        result = {}
        i = 0
        for k in respond['response']['items']:
            if k['post_type'] == 'post' and k['text'] != '':
                r = db.read_posts('post_id', 'wall_posts', k['id'])
                if r is None:
                    result[i] = {'post_id': k['id'], 'post_text': k['text'],
                                 'group_name': respond['response']['groups'][0]['name'],
                                 'group_screen_name': respond['response']['groups'][0]['screen_name'],
                                 'group_id': respond['response']['groups'][0]['id']}

            i += 1
        if len(result) == 0:
            return False
        else:
            return result


t = Config()
token = t.get_config_value('token')
update_time = t.get_config_value('update_time')
bot = Bot(token=token)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)


async def checknews():
    conf = Config()
    chat_id = conf.get_config_value('chat_id')
    c = LadaOnline()
    data = c.data()

    vk = VK()
    wall = vk.last_wall_posts()

    db = DB()

    if data['fresh'] is True:
        # 1001365037048
        inline_btn_1 = InlineKeyboardButton('Подробнее', data['url'])
        inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
        await bot.send_photo(chat_id, types.InputFile.from_url(data['img']), data['msg'], parse_mode="MARKDOWN",
                             reply_markup=inline_kb1)
    elif wall is not False:
        for k in wall:
            msg = 'Новая запись на стене сообщества <b>' + wall[k]['group_name'] + '</b>\n' \
                                                                                   '<b>Запись:</b>\n' + wall[k][
                      'post_text']
            url = 'https://vk.com/' + wall[k]['group_screen_name'] + '?w=wall-' + str(wall[k]['group_id']) + '_' \
                  + str(wall[k]['post_id'])
            inline_btn_1 = InlineKeyboardButton('Подробнее', url)
            inline_kb1 = InlineKeyboardMarkup().add(inline_btn_1)
            await bot.send_message(chat_id, msg, parse_mode='HTML', reply_markup=inline_kb1)
            db.write_post(wall[k]['post_id'])


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
    conf = Config()
    chat_id = conf.get_config_value('chat_id')
    db = DB()
    last_req = db.read_rules_request_data('last_post_date')
    if last_req is None:
        last_req = 0
    date = message.date.timestamp()
    t_comp = date - last_req
    if int(t_comp) > 1800 or message.chat.id != chat_id:
        vk = VK()
        rules = vk.get_rules()
        link_to_rules = vk.link_to_rules()
        msg = rules + '\nСсылка: <a href="' + link_to_rules + '">Правила группы</a>'
        resp = await message.reply(msg, parse_mode='HTML')
        user_id = message.from_user.id
        data = (int(date), int(user_id), int(resp))
        if message.chat.id == chat_id:
            db.write_rules_request_data(data)
    else:
        mes_id = db.read_rules_request_data('message_id')
        conf = Config()
        chat_id = conf.get_config_value('chat_id')
        msg = 'Я отправлял сообщение с правилами в чат менее 30 минут назад, не вижу смысла отправлять ещё раз. ' \
              'Но я не гордый, поэтому вот вам ссылка на сообщение.'
        await bot.send_message(chat_id=chat_id, text=msg, reply_to_message_id=mes_id)


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
    msg = 'Привет, ' + user + '!\nМы рады преветствовать тебя в нашем чате!\nНо прежде чем начать общение, ' \
                              'пожалуйста ознакомься с правилами вызвав команду <b>/rules</b> или можешь почитать ' \
                              'их Вконтакте: <a href="' + link_to_rules + '">Правила группы</a>\nПриятного общения! '
    await message.reply(msg, parse_mode='HTML')


@dp.message_handler(content_types=["left_chat_member"])
async def leftuser(message: types.Message):
    await bot.send_message(
        message.chat.id, 'Теряем бойцов, капитан!')


@dp.message_handler(content_types=['text'])
async def reply(message: types.Message):
    text = message.text.lower()
    ntext = text.translate(str.maketrans('', '', string.punctuation)).lower()
    arr = ntext.split()
    if 'масло' in arr and 'какое' in arr or 'свечи' in arr and 'какие' in arr or 'бензин' in arr and 'какой' in arr:
        with open(path.join(basedir, 'img/shitstorm.jpg'), 'rb') as photo:
            await message.reply_photo(photo)
    match = re.findall(r'[Pp]\d{4}', text)
    if not match:
        match = re.findall(r'[Рр]\d{4}', text)  # На кириллице
        if match:
            error_code = match[0].upper()
            error_code = error_code.replace('Р', 'P')  # Меняем киррилическую Р на латинскую П
            print(error_code)
            match[0] = error_code
        else:
            match = re.findall(r'[Uu]\d{4}', text)  # U коды
    if match:
        ec = match[0].upper()
        err_code = ErrorCodes(ec)
        result = err_code.codes_return()
        user = message.from_user.first_name
        msg = 'Пссс, %s, у меня есть информация об этой ошибке, ' \
              'смотри\n<b>Ошибка:</b> %s\n<b>Описание:</b> %s \n<b>Устранение неисправности:</b>\n%s' % \
              (user, result['error_code'], result['description'], result['troubleshooting'])
        await message.reply(msg, parse_mode='HTML')


if __name__ == '__main__':
    data_base = DB()
    data_base.install_tables()
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled(update_time))
    executor.start_polling(dp, skip_updates=True)
