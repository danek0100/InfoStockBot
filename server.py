import vk_api.vk_api
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.upload import VkUpload
import threading

from firebase_class import FireBase
import user as user_lib

import datetime as dt
from time import sleep

import bs4 as bs4
import requests
import dataframe_image as dfi
import matplotlib.pyplot as plt

import yfinance as yf
import investpy as ip

import os

link_on_pay = os.environ['LINK_ON_PAY']
vk_api_token = os.environ['VK_API_TOKEN']
vk_group_id = os.environ['VK_GROUP_ID']

vk_session = vk_api.VkApi(token=vk_api_token)
P_M_Long_poll = VkBotLongPoll(vk_session, group_id=vk_group_id)


class StocksChecker(threading.Thread):
    def __init__(self, firebase, server_):
        threading.Thread.__init__(self)
        self.fb = firebase
        self.server = server_

    def run(self):
        while True:
            try:
                users = self.fb.get_users()
                checking_prices_t(users, self.server)
                self.fb.update_users(users)
            except Exception as e:
                print(e)
                sleep(5)
                continue
            sleep(300)


class SubscriptionChecker(threading.Thread):
    def __init__(self, firebase, server_):
        threading.Thread.__init__(self)
        self.fb = firebase
        self.server = server_

    def run(self):
        while True:
            try:
                users = self.fb.get_users()
                checking_subscription(users, self.server)
                # checking_differences(self.server)
            except Exception as e:
                print(e)
                sleep(5)
                continue
            sleep(86400)


class Server:
    def __init__(self, api_token, group_id, server_name: str = "Empty"):
        self.server_name = server_name
        self.vk = vk_api.VkApi(token=api_token)
        self.long_poll = VkBotLongPoll(self.vk, group_id)
        self.vk_api = self.vk.get_api()
        self.firebase = FireBase()

    def start(self):
        stocks_checker = StocksChecker(self.firebase, self)
        subscription_checker = SubscriptionChecker(self.firebase, self)
        stocks_checker.start()
        subscription_checker.start()

        while True:
            try:
                self.listening()
            except Exception:
                sleep(0.1)

    @staticmethod
    def send_a_message(user_id, msg, attachments):
        vk_session.method('messages.send', {'user_id': user_id,
                                            'random_id': get_random_id(),
                                            'message': msg,
                                            'attachment': attachments,
                                            'keyboard': None})

    @staticmethod
    def _clean_all_tag_from_str(string_line):
        result = ""
        not_skip = True
        for i in list(string_line):
            if not_skip:
                if i == "<":
                    not_skip = False
                else:
                    result += i
            else:
                if i == ">":
                    not_skip = True

        return result

    @staticmethod
    def send_message(user_id, message=None, attachment=None, keyboard=None):
        vk_session.method('messages.send', {'user_id': user_id,
                                            'random_id': get_random_id(),
                                            'message': message,
                                            'attachment': attachment,
                                            'keyboard': keyboard})

    def get_user_name_from_vk_id(self, user_id):
        request = requests.get("https://vk.com/id" + str(user_id))
        bs = bs4.BeautifulSoup(request.text, "html.parser")
        user_name = self._clean_all_tag_from_str(bs.findAll("title")[0])
        return user_name.split()[0]

    @staticmethod
    def upload_photo(upload, photo):
        response = upload.photo_messages(photo)[0]

        owner_id = response['owner_id']
        photo_id = response['id']
        access_key = response['access_key']

        return owner_id, photo_id, access_key

    @staticmethod
    def send_photo(peer_id, owner_id, photo_id, access_key):
        attachment = f'photo{owner_id}_{photo_id}_{access_key}'
        vk_session.method('messages.send', {'user_id': peer_id,
                                            'random_id': get_random_id(),
                                            'message': None,
                                            'attachment': attachment,
                                            'keyboard': None})

    def listening(self):
        vk_sessions = vk_api.VkApi(token=vk_api_token)
        sessions_api = vk_sessions.get_api()
        long_poll = VkLongPoll(vk_sessions, group_id=vk_group_id)

        while True:
            try:
                for event in long_poll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.from_user and not event.from_me:
                            response = event.text.lower()
                            context = vk_session.method('messages.getHistory',
                                                        {'user_id': event.user_id,
                                                         'start_message_id': event.message_id,
                                                         'offset': 0, 'count': 20})['items']

                            # Заполнение пустого диалога
                            if len(context) < 20:
                                while len(context) < 20:
                                    context.append(context[0])

                            # Вызов меню
                            if response == 'меню':
                                keyboard = create_keyboard('меню', self.firebase, event.user_id)
                                self.send_message(event.user_id, 'Держи меню!', keyboard=keyboard)

                            # Стартовое сообщение
                            elif response == "привет" or response == "start" or (context[0]['from_id'] == "") or \
                                    response == 'начать':
                                self.send_message(event.user_id, "Привет, " +
                                                  str(self.get_user_name_from_vk_id(event.user_id)) +
                                                  ", рад, что ты решил ко мне заглянуть, надюсь нас ждёт"
                                                  " плодотворное сотруднечество."
                                                  "\n\nНа данный момент бот имеет функционал для всех, а так же "
                                                  "специализированную расширеную версию для Донов. "
                                                  "\nНичего сложного в работе со мной ты не "
                                                  "встретишь - "
                                                  "всё управление выполняется с помощью кнопок. Единственное,"
                                                  " что некоторую"
                                                  "информацию нужно будет вводить самому.\n\n Сейчас основной "
                                                  "функционал бота"
                                                  " связан с предоставлением информации о состоянии рынка акции"
                                                  " прямо в VK.\n"
                                                  "\n С помощью меня ты можешь получать актуальную информацию "
                                                  "об акциях, о их цене, получить график, получить доступные "
                                                  "технические индиакаторы и анализ, точки пивот,"
                                                  " получать оповещения для покупки и продажи акций, проверить"
                                                  " зависимость акций и портфеля,"
                                                  " а также сохранять свою статистику.\n"
                                                  "\nНа данный момент это весь функционал"
                                                  " бота, но мы уже работаем над расширением функционала и количеством"
                                                  " поддерживаемых активов.\n\n"
                                                  "Спасибо за внимание, надеюсь нас ждёт"
                                                  " выгодная работа! \nА теперь держи меню!"
                                                  ,
                                                  keyboard=create_keyboard("меню", self.firebase, event.user_id))

                            # вызов меня портфеля
                            elif response == 'портфель 💼':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    self.send_message(event.user_id,
                                                      "Выберите функцию для работы с портфелем",
                                                      keyboard=create_keyboard('Портфель', self.firebase))

                            # Раздел портфеля - проверка на зависимость
                            elif response == 'зависимость портфеля ⚖':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    res = independent_analysis(current_user)
                                    if isinstance(res, str):
                                        self.send_a_message(event.user_id, res, 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    else:
                                        if res > 0.75:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nСильная зависимость в изменении цен", 0)

                                        elif 0.75 >= res > 0.35:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nСредняя зависимость в изменении цен",
                                                                0)

                                        elif 0.35 >= res > 0.1:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nНизкая зависимость в изменении цен",
                                                                0)

                                        elif 0.1 >= res > 0.0:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nАктивы почти независимы в изменении цен",
                                                                0)

                                        elif res == 0:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nАктивы независимы", 0)

                                        elif 0.0 > res > -0.1:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nАктивы имеют очень слабую обратную"
                                                                           " зависимость в "
                                                                           "изменении цен", 0)

                                        elif -0.1 >= res > -0.35:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nСлабая обратная зависимость в "
                                                                           "изменении цен", 0)

                                        elif -0.35 >= res > -0.75:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nСредняя обратная "
                                                                           "зависимость в изменении цен", 0)

                                        elif -0.75 >= res:
                                            self.send_a_message(event.user_id,
                                                                "Средний коэфицент корреляции за последние"
                                                                " пол года = " +
                                                                str(res) + "\nСильная обратная"
                                                                           " зависимость в изменении цен", 0)

                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))

                            # Раздел портфеля - мои активы
                            elif response == 'мои активы 📂':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    string = "Ваши активы\n\n"
                                    if len(current_user.unsupported_stocks) != 0:
                                        string += "Пользовательсике активы:\n"
                                        for stock in current_user.unsupported_stocks:
                                            string += '\n' + str(stock.id) + '. ' + stock.key + '\nПоследняя ' + \
                                                      'добавленная цена: ' + str(stock.last_price) + ' ' + \
                                                      str(stock.currency) + '\n'

                                            if (stock.last_price - stock.buying_price) > 0.0:
                                                string += 'Изменение в цене: +' + str(round(stock.last_price -
                                                                                            stock.buying_price, 2)) + \
                                                          ' (+' + str(round((stock.last_price / stock.buying_price) *
                                                                            100.0 - 100, 2)) + '%)\n'
                                            else:
                                                string += 'Изменение в цене: ' + str(round(stock.last_price -
                                                                                           stock.buying_price, 2)) + \
                                                          ' (' + str(round((stock.last_price / stock.buying_price) *
                                                                           100.0 - 100, 2)) + '%)\n'

                                            string += 'Цена покупки: ' + str(stock.buying_price) + ' ' + \
                                                      str(stock.currency)
                                            string += '\nОбъём: ' + str(stock.volume) + '\n\n'

                                    if len(current_user.supported_stocks) != 0:
                                        string += "Отслеживаемые активы:\n"
                                        for stock in current_user.supported_stocks:
                                            string += '\n' + str(stock.id) + '. ' + stock.key + '\nАктуальая ' + \
                                                      'цена: ' + str(stock.last_price) + ' ' + str(
                                                stock.currency) + '\n'

                                            if (stock.last_price - stock.buying_price) > 0.0:
                                                string += 'Изменение в цене: +' + str(round(stock.last_price -
                                                                                            stock.buying_price,
                                                                                            2)) + \
                                                          ' (+' + str(
                                                    round((stock.last_price / stock.buying_price) *
                                                          100.0 - 100, 2)) + '%)\n'
                                            else:
                                                string += 'Изменение в цене: ' + str(round(stock.last_price -
                                                                                           stock.buying_price, 2)) + \
                                                          ' (' + str(round((stock.last_price / stock.buying_price) *
                                                                           100.0 - 100, 2)) + '%)\n'

                                            string += 'Цена покупки: ' + str(stock.buying_price) + ' ' + str(
                                                stock.currency)
                                            string += '\nОбъём: ' + str(stock.volume) + '\n'
                                            string += 'Оповещения: '
                                            if int(stock.tracking):
                                                string += 'Да\nОжидаемый доход: ' \
                                                          + str(stock.profit_margin) + '\nОжидаемые потери: ' \
                                                          + str(stock.loss_limit) + '\n\n'
                                            else:
                                                string += 'Нет\n\n'

                                    if string == "Ваши активы\n\n":
                                        string = 'У вас нет отслеживаемых активов'
                                    self.send_message(event.user_id, string, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Раздел портфеля - статистика
                            elif response == 'статистика 💰':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    currencies = []
                                    for stock in current_user.supported_stocks:
                                        currencies.append(stock.currency)
                                    for stock in current_user.unsupported_stocks:
                                        currencies.append(stock.currency)
                                    curr_set = set(currencies)
                                    curr_counter = {}
                                    curr_counter_b = {}
                                    for curr in curr_set:
                                        curr_counter[curr] = 0.0
                                        curr_counter_b[curr] = 0.0

                                    for stock in current_user.supported_stocks:
                                        curr_counter[stock.currency] += stock.last_price * stock.volume
                                        curr_counter_b[stock.currency] += stock.buying_price * stock.volume
                                    for stock in current_user.unsupported_stocks:
                                        curr_counter[stock.currency] += stock.last_price * stock.volume
                                        curr_counter_b[stock.currency] += stock.buying_price * stock.volume

                                    result = "Статистика портфеля\n\n"
                                    if len(curr_counter.keys()) == 0:
                                        result += 'На данный момент портфель пуст!\n\n'
                                    else:
                                        result += 'Ваш портфель включает активы стоимостью:\n'
                                        for key in curr_counter.keys():
                                            result += str(curr_counter[key]) + ' ' + key
                                            if curr_counter[key] - curr_counter_b[key] >= 0.0:
                                                result += ' (+' + str(round((curr_counter[key] / curr_counter_b[key])
                                                                            * 100 - 100, 2)) + '%)\n'
                                            else:
                                                result += ' (' + str(round((curr_counter[key] / curr_counter_b[key])
                                                                           * 100 - 100, 2)) + '%)\n'

                                    result += '\nОбщая цена купленых / проданых активов:\n'
                                    for curr in current_user.general_purchases:
                                        result += str(current_user.general_purchases[curr]) + ' / ' + \
                                                  str(current_user.general_sales[curr]) + ' ' + curr
                                        try:
                                            if current_user.general_sales[curr] - \
                                                    current_user.general_purchases[curr] > 0.0:
                                                result += ' (+' + str(round((current_user.general_sales[curr] /
                                                                             current_user.general_purchases[curr]) *
                                                                            100 - 100, 2)) + ')\n'
                                            else:
                                                result += ' (' + str(round((current_user.general_sales[curr] /
                                                                            current_user.general_purchases[curr]) *
                                                                           100 - 100, 2)) + ')\n'
                                        except ZeroDivisionError:
                                            result += ' (0.0%)\n'

                                    self.send_message(event.user_id, result, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Раздел портфеля - добавление пользовательского актива
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'пользовательские активы ✍🏻' \
                                    and context[1]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id,
                                                  "Выберите действие", keyboard=create_keyboard('купил/продал_2',
                                                                                                self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'добавить актив ➕' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'добавить актив ➕' \
                                    and context[3]['text'].lower() == 'выберите действие' \
                                    and context[5]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите название страны на английском' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'выберите действие' \
                                    and context[7]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id, "Введите тикер или название актива", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите тикер или название актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[7]['text'].lower() == 'выберите действие' \
                                    and context[9]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id, "Введите количество активов", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите количество активов' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[5]['text'].lower() == 'введите название страны на английском' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[9]['text'].lower() == 'выберите действие' \
                                    and context[11]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id, "Введите цену покупки", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите цену покупки' \
                                    and context[3]['text'].lower() == 'введите количество активов' \
                                    and context[5]['text'].lower() == 'введите тикер или название актива' \
                                    and context[7]['text'].lower() == 'введите название страны на английском' \
                                    and context[9]['text'].lower() == 'выберите тип актива' \
                                    and context[11]['text'].lower() == 'выберите действие' \
                                    and context[13]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id, "Введите валюту",
                                                  keyboard=create_keyboard('Валюта', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите валюту' \
                                    and context[3]['text'].lower() == 'введите цену покупки' \
                                    and context[5]['text'].lower() == 'введите количество активов' \
                                    and context[7]['text'].lower() == 'введите тикер или название актива' \
                                    and context[9]['text'].lower() == 'введите название страны на английском' \
                                    and context[11]['text'].lower() == 'выберите тип актива' \
                                    and context[13]['text'].lower() == 'выберите действие' \
                                    and context[15]['text'].lower() == 'выберите функцию для работы с портфелем':
                                current_user = self.firebase.get_user(event.user_id)
                                if len(current_user.supported_stocks) != 0 and len(current_user.unsupported_stocks) \
                                        != 0:
                                    stock_id = max(current_user.supported_stocks[-1].id + 1,
                                                   current_user.unsupported_stocks[-1].id + 1)

                                elif len(current_user.supported_stocks) == 0 and \
                                        len(current_user.unsupported_stocks) > 0:
                                    stock_id = current_user.unsupported_stocks[-1].id + 1

                                elif len(current_user.supported_stocks) != 0 and \
                                        len(current_user.unsupported_stocks) == 0:
                                    stock_id = current_user.supported_stocks[-1].id + 1
                                else:
                                    stock_id = 1
                                try:
                                    current_stock = user_lib.CustomStock(stock_id, context[6]['text'],
                                                                         context[2]['text'].lower(),
                                                                         context[4]['text'].lower(),
                                                                         context[8]['text'].lower(),
                                                                         response.lower())
                                    current_user.add_new_stock(current_stock)
                                    self.firebase.change_user(current_user)
                                    self.send_a_message(event.user_id, "Акция успешно добавлена", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                except TypeError:
                                    self.send_a_message(event.user_id, "Была допущена ошибка"
                                                                       " в формате введёных данных", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Раздел портфеля - удаление пользовательского актива
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'удалить актив ❌' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'удалить актив ❌' \
                                    and context[3]['text'].lower() == 'выберите действие' \
                                    and context[5]['text'].lower() == 'выберите функцию для работы с портфелем':
                                current_user = self.firebase.get_user(event.user_id)
                                string = ""
                                for stock in current_user.unsupported_stocks:
                                    string += str(stock.id) + ' - ' + str(stock.key) + ', цена покупки: ' \
                                              + str(stock.buying_price) + str(stock.currency) + '\n'
                                if string == "":
                                    self.send_a_message(event.user_id, "Активов не найдено!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                else:
                                    self.send_a_message(event.user_id, "Список акций:\n" + string, 0)
                                    self.send_a_message(event.user_id, "Введите id акции для удаления", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите id акции для удаления' \
                                    and context[4]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'удалить актив ❌' \
                                    and context[6]['text'].lower() == 'выберите действие' \
                                    and context[8]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_a_message(event.user_id, "Введите цену продажи", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите цену продажи' \
                                    and context[3]['text'].lower() == 'введите id акции для удаления' \
                                    and context[6]['text'].lower() == 'выберите тип актива' \
                                    and context[7]['text'].lower() == 'удалить актив ❌' \
                                    and context[8]['text'].lower() == 'выберите действие' \
                                    and context[10]['text'].lower() == 'выберите функцию для работы с портфелем':
                                try:
                                    current_user = self.firebase.get_user(event.user_id)
                                    current_stock = None
                                    for stock in current_user.unsupported_stocks:
                                        if int(stock.id) == int(context[2]['text'].lower()):
                                            current_stock = stock
                                            break

                                    current_user.unsupported_stocks.remove(current_stock)

                                    if current_stock.currency in current_user.general_sales.keys():
                                        current_user.general_purchases[str(current_stock.currency)] += \
                                            float(current_stock.buying_price) * int(current_stock.volume)
                                        current_user.general_sales[str(current_stock.currency)] += \
                                            float(response) * int(current_stock.volume)
                                    else:
                                        current_user.general_purchases[str(current_stock.currency)] = \
                                            float(current_stock.buying_price) * int(current_stock.volume)
                                        current_user.general_sales[str(current_stock.currency)] = \
                                            float(response) * int(current_stock.volume)

                                    self.firebase.change_user(current_user)
                                    self.send_a_message(event.user_id, "Акция успешно удалена!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                                except TypeError:
                                    self.send_a_message(event.user_id, "Введены некоректнные значения!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                except ValueError:
                                    self.send_a_message(event.user_id, "Введен не верный id акции", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Раздел портфеля - обновление цены пользовательского актива
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'обновить цену актива 📝' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))
                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'обновить цену актива 📝' \
                                    and context[3]['text'].lower() == 'выберите действие' \
                                    and context[5]['text'].lower() == 'выберите функцию для работы с портфелем':
                                current_user = self.firebase.get_user(event.user_id)
                                string = ""
                                for stock in current_user.unsupported_stocks:
                                    string += str(stock.id) + ' - ' + str(stock.key) + ', последняя цена: ' \
                                              + str(stock.last_price) + str(stock.currency) + '\n'
                                if string == "":
                                    self.send_a_message(event.user_id, "Активов не найдено!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                else:
                                    self.send_a_message(event.user_id, "Список акций:\n" + string, 0)
                                    self.send_a_message(event.user_id, "Введите id актива для обновления цены", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите id актива для обновления цены' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[4]['text'].lower() == 'обновить цену актива 📝' \
                                    and context[5]['text'].lower() == 'выберите действие' \
                                    and context[7]['text'].lower() == 'выберите функцию для работы с портфелем':
                                self.send_a_message(event.user_id, "Введите актуальную цену", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите актуальную цену' \
                                    and context[3]['text'].lower() == 'введите id актива для обновления цены' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[6]['text'].lower() == 'обновить цену актива 📝' \
                                    and context[7]['text'].lower() == 'выберите действие' \
                                    and context[9]['text'].lower() == 'выберите функцию для работы с портфелем':
                                try:
                                    current_user = self.firebase.get_user(event.user_id)
                                    current_stock = None
                                    for stock in current_user.unsupported_stocks:
                                        if int(stock.id) == int(context[2]['text'].lower()):
                                            stock.last_price = float(response)
                                            break

                                    if current_stock is None:
                                        raise ValueError

                                    self.firebase.change_user(current_user)
                                    self.send_a_message(event.user_id, "Цена успешно удалена!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                                except TypeError:
                                    self.send_a_message(event.user_id, "Введены некоректнные значения!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                except ValueError:
                                    self.send_a_message(event.user_id, "Введен не верный id акции", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Выхов меню ЧЗВ
                            elif response == 'часто задаваемые вопросы ❓':
                                self.send_message(event.user_id, 'Выбери раздел',
                                                  keyboard=create_keyboard('вопросы', self.firebase,
                                                                           event.user_id))

                            # Раздел ЧЗВ - Вопрос - Ответ
                            elif response == 'вопрос - ответ ⁉':
                                answer = 'Свой вопрос вы можете задать администратору'
                                answer += 'Ввожу цену актива и получаю ошибку с чем это может быть связано?\nЦену ' \
                                          'необходимо вводить через точку, например 192.2\n\n'
                                answer += 'Почему необходимо выбирать тип актива, если можно выбрать только ' \
                                          'акцию?\n\nМы работаем над добавлением новых типов активов. Обращаем ' \
                                          'внимание, что \' введите \' и \'выберите\' имеет разный смысл, ' \
                                          'если необходимо выбрать страну, то введение любой другой поддерживаемой ' \
                                          'страны, приведёт к ошибке, будьте внимательны! '
                                self.send_message(event.user_id, answer, 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            # Раздел ЧЗВ - Список поддерживаемых активов
                            elif response == 'поддерживаемые страны 🚩' \
                                    and context[1]['text'].lower() == 'выбери раздел':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))
                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'поддерживаемые страны 🚩' \
                                    and context[3]['text'].lower() == 'выбери раздел':
                                result = "Страны:\n"
                                if response == 'акция':
                                    country_list = ip.stocks.get_stock_countries()
                                    for country in country_list:
                                        result += country + '\n'

                                self.send_message(event.user_id, result, 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            # Раздел ЧВЗ - Поддерживаемые активы
                            elif response == 'поддерживаемые активы ✅' \
                                    and context[1]['text'].lower() == 'выбери раздел':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))
                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'поддерживаемые активы ✅' \
                                    and context[3]['text'].lower() == 'выбери раздел':
                                self.send_message(event.user_id,
                                                  "Введите страну", keyboard=create_keyboard('Страны',
                                                                                             self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите страну' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[4]['text'].lower() == 'поддерживаемые активы ✅' \
                                    and context[5]['text'].lower() == 'выбери раздел':
                                if context[2]['text'].lower() == 'акция':
                                    try:
                                        stocks = ip.stocks.get_stocks(response)
                                        result = "Активы:\n"
                                        for stock in range(len(stocks)):
                                            result += stocks['full_name'][stock] + ' - ' + stocks['symbol'][
                                                stock] + '\n'

                                        i = 0
                                        while i < len(result):
                                            self.send_message(event.user_id, result[i:i + 4095], 0)
                                            i += 4095
                                            sleep(0.5)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    except Exception:
                                        self.send_message(event.user_id, 'Ошибка в введённых данных!', 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))

                            # Вызов меню Информации
                            elif response == 'информация 📖':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    self.send_message(event.user_id,
                                                      "Какая информация нужна?",
                                                      keyboard=create_keyboard('Информация', self.firebase))

                            # Раздел информация - лидеры роста
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'лидеры роста 📈' \
                                    and context[1]['text'].lower() == 'какая информация нужна?':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'лидеры роста 📈' \
                                    and context[3]['text'].lower() == 'какая информация нужна?':
                                self.send_message(event.user_id,
                                                  "Выберите период", keyboard=create_keyboard('Период_2',
                                                                                              self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите период' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[4]['text'].lower() == 'лидеры роста 📈' \
                                    and context[5]['text'].lower() == 'какая информация нужна?':
                                self.send_message(event.user_id,
                                                  "Выберите страну", keyboard=create_keyboard('Страны_info',
                                                                                              self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите страну' \
                                    and context[3]['text'].lower() == 'выберите период' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[6]['text'].lower() == 'лидеры роста 📈' \
                                    and context[7]['text'].lower() == 'какая информация нужна?':

                                try:
                                    if context[4]['text'].lower() == 'акция':
                                        data = self.firebase.get_prices_info(response, 'stocks')
                                        if context[2]['text'].lower() == 'день':
                                            data.sort(key=diff_daily)
                                            result = 'Лидеры роста за день:\n'
                                            for i in range(11):
                                                result += str((data[i]).key) + ': ' + str((data[i]).differences_daily) \
                                                          + '% \n'
                                            self.send_message(event.user_id, result, 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))

                                        elif context[2]['text'].lower() == 'неделя':
                                            data.sort(key=diff_weekly)
                                            result = 'Лидеры роста за неделю:\n'
                                            for i in range(11):
                                                result += str((data[i]).key) + ': ' + str((data[i]).differences_weekly) \
                                                          + '% \n'
                                            self.send_message(event.user_id, result, 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))

                                        elif context[2]['text'].lower() == 'месяц':
                                            data.sort(key=diff_monthly)
                                            result = 'Лидеры роста за месяц:\n'
                                            for i in range(11):
                                                result += str((data[i]).key) + ': ' + \
                                                          str((data[i]).differences_monthly) + '% \n'
                                            self.send_message(event.user_id, result, 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))
                                except Exception:
                                    self.send_message(event.user_id, 'Введены неверные данные!', 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Раздел информации - лидеры падения
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'лидеры падения 📉' \
                                    and context[1]['text'].lower() == 'какая информация нужна?':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'лидеры падения 📉' \
                                    and context[3]['text'].lower() == 'какая информация нужна?':
                                self.send_message(event.user_id,
                                                  "Выберите период", keyboard=create_keyboard('Период_2',
                                                                                              self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите период' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[4]['text'].lower() == 'лидеры падения 📉' \
                                    and context[5]['text'].lower() == 'какая информация нужна?':
                                self.send_message(event.user_id,
                                                  "Выберите страну", keyboard=create_keyboard('Страны_info',
                                                                                              self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите страну' \
                                    and context[3]['text'].lower() == 'выберите период' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[6]['text'].lower() == 'лидеры падения 📉' \
                                    and context[7]['text'].lower() == 'какая информация нужна?':

                                try:
                                    if context[4]['text'].lower() == 'акция':
                                        data = self.firebase.get_prices_info(response, 'stocks')
                                        if context[2]['text'].lower() == 'день':
                                            data.sort(key=diff_daily, reverse=True)
                                            result = 'Лидеры падения за день:\n'
                                            for i in range(11):
                                                result += str((data[i]).key) + ': ' + str((data[i]).differences_daily) \
                                                          + '% \n'
                                            self.send_message(event.user_id, result, 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))

                                        elif context[2]['text'].lower() == 'неделя':
                                            data.sort(key=diff_weekly, reverse=True)
                                            result = 'Лидеры падения за неделю:\n'
                                            for i in range(11):
                                                result += str((data[i]).key) + ': ' + str((data[i]).differences_weekly) \
                                                          + '% \n'
                                            self.send_message(event.user_id, result, 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))

                                        elif context[2]['text'].lower() == 'месяц':
                                            data.sort(key=diff_monthly, reverse=True)
                                            result = 'Лидеры падения за месяц:\n'
                                            for i in range(11):
                                                result += str((data[i]).key) + ': ' + \
                                                          str((data[i]).differences_monthly) + '% \n'
                                            self.send_message(event.user_id, result, 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))
                                except Exception:
                                    self.send_message(event.user_id, 'Введены неверные данные!', 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Раздел информация - информация о активе
                            elif response == 'информация о активе 📄':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'информация о активе 📄':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'информация о активе 📄' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[1]['text'].lower() == 'введите название страны на английском':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'информация о активе 📄' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':
                                active_info(self, event.user_id, response.upper(), context[2]['text'].lower(),
                                            context[4]['text'].lower())
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # вызов меню настроек
                            elif response == 'настройки ⚙':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    self.send_message(event.user_id,
                                                      "Выберите что будем настраивать",
                                                      keyboard=create_keyboard('Настройки', self.firebase))

                            # настройки - сброс статистики
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'сбросить статистику 🗑' \
                                    and context[1]['text'].lower() == 'выберите что будем настраивать':
                                self.send_message(event.user_id,
                                                  "Вы уверены, что хотите сбросить статистику?\n"
                                                  "Востановить даннные будет невозможно!",
                                                  keyboard=create_keyboard('да/нет', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'да' \
                                    and context[1]['text'].lower() == 'вы уверены, что хотите сбросить статистику?\n' \
                                                                      'востановить даннные будет невозможно!' \
                                    and context[3]['text'].lower() == 'выберите что будем настраивать':
                                current_user = self.firebase.get_user(event.user_id)
                                current_user.general_sales = {'RUB': 0.0, 'USD': 0.0}
                                current_user.general_purchases = {'RUB': 0.0, 'USD': 0.0}
                                self.firebase.change_user(current_user)
                                self.send_message(event.user_id, "Статиска сброшена!", 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'нет' \
                                    and context[1]['text'].lower() == 'вы уверены, что хотите сбросить статистику?\n' \
                                                                      'востановить даннные будет невозможно!' \
                                    and context[3]['text'].lower() == 'выберите что будем настраивать':
                                self.send_message(event.user_id, "Сброс статистики отменён!", 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            # Настройки отмена подписки
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'отменить подписку 🚫' \
                                    and context[1]['text'].lower() == 'выберите что будем настраивать':
                                self.send_message(event.user_id,
                                                  "Вы можете отменить подписку по ссылке\n" + str(link_on_pay) +
                                                  "\nОтменили подписку?",
                                                  keyboard=create_keyboard('да/нет', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'да' \
                                    and context[2]['text'].lower() == 'отменить подписку 🚫' \
                                    and context[3]['text'].lower() == 'выберите что будем настраивать':
                                current_user = self.firebase.get_user(event.user_id)
                                current_user.subscription = '0'
                                self.firebase.change_user(current_user)
                                self.send_message(event.user_id, "Ваша подписка отменена!", 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'нет' \
                                    and context[1]['text'].lower() == ('вы можете отменить подписку по ссылке\n'
                                                                       + str(link_on_pay) + '\nотменили подписку?') \
                                    and context[3]['text'].lower() == 'выберите что будем настраивать':
                                self.send_message(event.user_id, "Подписка сохранена!", 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            # Настройки - оповещения
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'оповещения 📩' \
                                    and context[1]['text'].lower() == 'выберите что будем настраивать':
                                self.send_message(event.user_id,
                                                  "Что будем делать с оповещениями?",
                                                  keyboard=create_keyboard('включить/отключить', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'включить' \
                                    and context[1]['text'].lower() == 'что будем делать с оповещениями?' \
                                    and context[3]['text'].lower() == 'выберите что будем настраивать':
                                current_user = self.firebase.get_user(event.user_id)
                                current_user.alerts = 1
                                self.firebase.change_user(current_user)
                                self.send_message(event.user_id, "Статус оповещений обновлён!", 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'отключить' \
                                    and context[1]['text'].lower() == 'что будем делать с оповещениями?' \
                                    and context[3]['text'].lower() == 'выберите что будем настраивать':
                                current_user = self.firebase.get_user(event.user_id)
                                current_user.alerts = 0
                                self.firebase.change_user(current_user)
                                self.send_message(event.user_id, "Статус оповещений обновлён!", 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            # Вызов меню раздела Анализ
                            elif response == 'анализ 🔎':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    self.send_message(event.user_id,
                                                      "Выберите функцию анализа",
                                                      keyboard=create_keyboard('Анализ', self.firebase))

                            # Технический анализ
                            elif response == 'технический анализ 📝' \
                                    and context[1]['text'].lower() == 'выберите функцию анализа':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'технический анализ 📝':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'технический анализ 📝' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[1]['text'].lower() == 'введите название страны на английском':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'технический анализ 📝' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':
                                self.send_message(event.user_id,
                                                  "Выберите период для техического анализа",
                                                  keyboard=create_keyboard('Период', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[8]['text'].lower() == 'технический анализ 📝' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'введите название страны на английском' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[1]['text'].lower() == 'выберите период для техического анализа':
                                answer = technical_analysis(context[2]['text'].lower(), context[4]['text'].lower(),
                                                            context[6]['text'].lower(), context[0]['text'].lower())

                                if isinstance(answer, str):
                                    self.send_a_message(event.user_id, answer, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                                else:
                                    df_styled = answer.style.background_gradient()
                                    dfi.export(df_styled, "tech_table.png", table_conversion='matplotlib')

                                    upload = VkUpload(self.vk_api)

                                    active = context[2]['text'].upper()
                                    self.send_message(event.user_id, "Результат техического анализа для " +
                                                      active + ":", 0)

                                    self.send_photo(event.user_id, *self.upload_photo(upload, 'tech_table.png'))

                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Технические индикаторы
                            elif response == 'технические индикаторы 📊' \
                                    and context[1]['text'].lower() == 'выберите функцию анализа':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'технические индикаторы 📊':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'технические индикаторы 📊' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[1]['text'].lower() == 'введите название страны на английском':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'технические индикаторы 📊' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':
                                self.send_message(event.user_id,
                                                  "Выберите период для получения техических идикаторов",
                                                  keyboard=create_keyboard('Период', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[8]['text'].lower() == 'технические индикаторы 📊' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'введите название страны на английском' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[1]['text'].lower() == 'выберите период для' \
                                                                      ' получения техических идикаторов':
                                answer = technical_indicators(context[2]['text'].lower(), context[4]['text'].lower(),
                                                              context[6]['text'].lower(), context[0]['text'].lower())

                                if isinstance(answer, str):
                                    self.send_a_message(event.user_id,
                                                        answer, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                                else:
                                    df_styled = answer.style.background_gradient()
                                    dfi.export(df_styled, "tech_ind.png", table_conversion='matplotlib')

                                    upload = VkUpload(self.vk_api)

                                    active = context[2]['text'].upper()
                                    self.send_message(event.user_id, "Технические индикаторы для " +
                                                      active + ":", 0)

                                    self.send_photo(event.user_id, *self.upload_photo(upload, 'tech_ind.png'))

                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Точки пивот
                            elif response == 'точки пивот 💢' \
                                    and context[1]['text'].lower() == 'выберите функцию анализа':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'точки пивот 💢':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'точки пивот 💢' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[1]['text'].lower() == 'введите название страны на английском':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'точки пивот 💢' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':
                                self.send_message(event.user_id,
                                                  "Выберите период для получения точек пивот",
                                                  keyboard=create_keyboard('Период', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[8]['text'].lower() == 'точки пивот 💢' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'введите название страны на английском' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[1]['text'].lower() == 'выберите период для' \
                                                                      ' получения точек пивот':
                                answer = pivot_points(context[2]['text'].lower(), context[4]['text'].lower(),
                                                      context[6]['text'].lower(), context[0]['text'].lower())

                                if isinstance(answer, str):
                                    self.send_a_message(event.user_id,
                                                        answer, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                                else:
                                    df_styled = answer.style.background_gradient()
                                    dfi.export(df_styled, "pivot_ind.png", table_conversion='matplotlib')

                                    upload = VkUpload(self.vk_api)

                                    active = context[2]['text'].upper()
                                    self.send_message(event.user_id, "Точки пивот для " +
                                                      active + ":", 0)

                                    self.send_photo(event.user_id, *self.upload_photo(upload, 'pivot_ind.png'))

                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # График цены
                            elif response == 'график цены 📈' \
                                    and context[1]['text'].lower() == 'выберите функцию анализа':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'график цены 📈':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'график цены 📈' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[1]['text'].lower() == 'введите название страны на английском':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'график цены 📈' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':
                                self.send_message(event.user_id,
                                                  "Выберите период для получения графика",
                                                  keyboard=create_keyboard('Период_', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[8]['text'].lower() == 'график цены 📈' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'введите название страны на английском' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[1]['text'].lower() == 'выберите период для' \
                                                                      ' получения графика':
                                answer = history_of_active(context[2]['text'].lower(), context[4]['text'].lower(),
                                                           context[6]['text'].lower(), context[0]['text'].lower())

                                if isinstance(answer, str):
                                    self.send_a_message(event.user_id,
                                                        answer, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                                else:
                                    build_graph(answer)

                                    upload = VkUpload(self.vk_api)

                                    active = context[2]['text'].upper()
                                    self.send_message(event.user_id, "График для " +
                                                      active + ":", 0)

                                    self.send_photo(event.user_id, *self.upload_photo(upload, 'hist.png'))

                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Проверка на зависимость
                            elif response == 'проверка на зависимость ⚖':
                                self.send_message(event.user_id,
                                                  "Выберите тип первого актива",
                                                  keyboard=create_keyboard('Тип актива', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип первого актива' \
                                    and context[2]['text'].lower() == 'проверка на зависимость ⚖':
                                self.send_message(event.user_id, "Выберите (введите) страну",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'проверка на зависимость ⚖' \
                                    and context[3]['text'].lower() == 'выберите тип первого актива' \
                                    and context[1]['text'].lower() == 'выберите (введите) страну':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'проверка на зависимость ⚖' \
                                    and context[5]['text'].lower() == 'выберите тип первого актива' \
                                    and context[3]['text'].lower() == 'выберите (введите) страну' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':

                                answer = history_of_active(context[0]['text'].lower(), context[2]['text'].lower(),
                                                           context[4]['text'].lower(), '6 месяцев')
                                if isinstance(answer, str):
                                    self.send_a_message(event.user_id, answer, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                                else:
                                    self.send_message(event.user_id,
                                                      "Выберите тип второго актива",
                                                      keyboard=create_keyboard('Тип актива', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[8]['text'].lower() == 'проверка на зависимость ⚖' \
                                    and context[7]['text'].lower() == 'выберите тип первого актива' \
                                    and context[5]['text'].lower() == 'выберите (введите) страну' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[1]['text'].lower() == 'выберите тип второго актива':

                                self.send_message(event.user_id, "Выберите (введите) страну",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[10]['text'].lower() == 'проверка на зависимость ⚖' \
                                    and context[9]['text'].lower() == 'выберите тип первого актива' \
                                    and context[7]['text'].lower() == 'выберите (введите) страну' \
                                    and context[5]['text'].lower() == 'введите тикер или название актива' \
                                    and context[3]['text'].lower() == 'выберите тип второго актива' \
                                    and context[1]['text'].lower() == 'выберите (введите) страну':

                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[12]['text'].lower() == 'проверка на зависимость ⚖' \
                                    and context[11]['text'].lower() == 'выберите тип первого актива' \
                                    and context[9]['text'].lower() == 'выберите (введите) страну' \
                                    and context[7]['text'].lower() == 'введите тикер или название актива' \
                                    and context[5]['text'].lower() == 'выберите тип второго актива' \
                                    and context[3]['text'].lower() == 'выберите (введите) страну' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':

                                data_2 = history_of_active(context[0]['text'].lower(), context[2]['text'].lower(),
                                                           context[4]['text'].lower(), '6 месяцев')
                                if isinstance(data_2, str):
                                    self.send_a_message(event.user_id,
                                                        data_2, 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                                else:
                                    data_1 = history_of_active(context[6]['text'].lower(), context[8]['text'].lower(),
                                                               context[10]['text'].lower(), '6 месяцев')

                                    name_of_first = context[6]['text'].lower()
                                    name_of_second = context[0]['text'].lower()
                                    data_2 = data_2.Close
                                    table = data_1
                                    table[name_of_second] = data_2
                                    table_res = table.drop(columns=['Open', 'High', 'Low', 'Volume', 'Currency'])
                                    table_res.rename(columns={'Close': name_of_first}, inplace=True)
                                    returns = table_res.pct_change()
                                    corr = returns.corr()
                                    if round(corr[name_of_first][name_of_second], 2) > 0.75:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nСильная зависимость в изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif 0.75 >= round(corr[name_of_first][name_of_second], 2) > 0.35:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nСредняя зависимость в изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif 0.35 >= round(corr[name_of_first][name_of_second], 2) > 0.1:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nНизкая зависимость в изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif 0.1 >= round(corr[name_of_first][name_of_second], 2) > 0.0:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nАктивы почти независимы в изменении цен",
                                                            0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif round(corr[name_of_first][name_of_second], 3) == 0:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nАктивы независимы", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif 0.0 > round(corr[name_of_first][name_of_second], 2) > -0.1:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nАктивы имеют очень слабую обратную"
                                                                            " зависимость в "
                                                                            "изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif -0.1 >= round(corr[name_of_first][name_of_second], 2) > -0.35:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nСлабая обратная зависимость в "
                                                                            "изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif -0.35 >= round(corr[name_of_first][name_of_second], 2) > -0.75:
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nСредняя обратная "
                                                                            "зависимость в изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    elif -0.75 >= round(corr[name_of_first][name_of_second], 2):
                                        self.send_a_message(event.user_id,
                                                            "Коэфицент корреляции за последние пол года = " +
                                                            str(round(corr[name_of_first][name_of_second],
                                                                      3)) + "\nСильная обратная"
                                                                            " зависимость в изменении цен", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    else:
                                        self.send_a_message(event.user_id,
                                                            "Ошибка! Что-то пошло не так!", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))

                            # Вызов меню отслеживания
                            elif response == 'отслеживание цены 📈':
                                current_user = self.firebase.get_user(event.user_id)
                                if current_user != 0 and current_user.subscription != '0':
                                    self.send_message(event.user_id,
                                                      "Выберите тип отслеживания",
                                                      keyboard=create_keyboard('Отслеживание', self.firebase))

                            # Подраздел оповещение о цене
                            elif response == 'оповещение о цене ✉':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива",
                                                  keyboard=create_keyboard('Тип актива', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'оповещение о цене ✉':
                                self.send_message(event.user_id, "Выберите (введите) страну",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[4]['text'].lower() == 'оповещение о цене ✉' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[1]['text'].lower() == 'выберите (введите) страну':
                                self.send_message(event.user_id, "Введите тикер или название актива")

                            elif context[0]['from_id'] == event.user_id \
                                    and context[6]['text'].lower() == 'оповещение о цене ✉' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[3]['text'].lower() == 'выберите (введите) страну' \
                                    and context[1]['text'].lower() == 'введите тикер или название актива':
                                self.send_a_message(event.user_id, "При какой цене вас оповестить?", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[8]['text'].lower() == 'оповещение о цене ✉' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'выберите (введите) страну' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[1]['text'].lower() == 'при какой цене вас оповестить?':
                                try:
                                    data_ = ip.stocks.get_stocks_overview(context[4]['text'].lower(), n_results=1000)
                                    data_ = data_.drop(
                                        columns=['name', 'country', 'turnover', 'change', 'change_percentage', 'high',
                                                 'low'])
                                    index = 0
                                    flag = 0
                                    for symbol in data_['symbol']:
                                        if symbol == context[2]['text'].upper():
                                            flag = 1
                                            break
                                        index += 1

                                    if flag:
                                        try:
                                            float(response)
                                        except ValueError:
                                            self.send_a_message(event.user_id, "Число введено неверно!", 0)

                                        spy_stock = user_lib.SpyStock(event.user_id, context[2]['text'].upper(),
                                                                      context[4]['text'].lower(),
                                                                      response, context[6]['text'].lower())

                                        self.firebase.add_spy_stock(spy_stock)
                                        self.send_a_message(event.user_id, 'Актив добавлен!', 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))

                                    elif context[7]['text'].lower() == 'акция':
                                        try:
                                            if context[4]['text'].lower() == 'russia':
                                                active_name = context[2]['text'].upper() + '.ME'
                                                data = yf.download(tickers=active_name, period='0')
                                                spy_stock = user_lib.SpyStock(event.user_id, context[2]['text'].upper(),
                                                                              context[4]['text'].lower(),
                                                                              context[7]['text'].lower(),
                                                                              response)
                                                self.firebase.add_spy_stock(spy_stock)
                                                self.send_a_message(event.user_id, 'Актив добавлен!', 0)
                                                self.send_message(event.user_id, 'Держи меню!',
                                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                                           event.user_id))

                                            elif context[4]['text'].lower() == 'united states':
                                                active_name = context[2]['text'].upper()
                                                data = yf.download(tickers=active_name, period='0')
                                                spy_stock = user_lib.SpyStock(event.user_id, context[2]['text'].upper(),
                                                                              context[4]['text'].lower(),
                                                                              context[7]['text'].lower(),
                                                                              response)
                                                self.firebase.add_spy_stock(spy_stock)
                                                self.send_a_message(event.user_id, 'Актив добавлен!', 0)
                                                self.send_message(event.user_id, 'Держи меню!',
                                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                                           event.user_id))

                                            else:
                                                self.send_a_message(event.user_id, 'Актив не поддерживаеться!', 0)
                                                self.send_message(event.user_id, 'Держи меню!',
                                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                                           event.user_id))

                                        except Exception:
                                            self.send_a_message(event.user_id, 'Актив не поддерживаеться!', 0)
                                            self.send_message(event.user_id, 'Держи меню!',
                                                              keyboard=create_keyboard('меню', self.firebase,
                                                                                       event.user_id))

                                    else:
                                        self.send_a_message(event.user_id, 'Проверь правильность введённых данных!\n'
                                                                           'Не вышло добавить актив для отслеживания',
                                                            0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))

                                except Exception:
                                    self.send_a_message(event.user_id, 'Возникла ошибка!', 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Раздел слежение за активом
                            elif response == 'отслеживание актива 📌' \
                                    and context[1]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id,
                                                  "Выберите действие",
                                                  keyboard=create_keyboard('купил/продал', self.firebase))

                            # Список отслеживаемых активов
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'список отслеживаемых активов 📜' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите тип отслеживания':
                                current_user = self.firebase.get_user(event.user_id)
                                string = ""
                                for stock in current_user.supported_stocks:
                                    string += str(stock.id) + '. ' + str(stock.key) + \
                                              '\nАктуальная цена: ' + str(stock.last_price) + ' ' + str(stock.currency) \
                                              + '\nЦена покупки: ' \
                                              + str(stock.buying_price) + ' ' + str(stock.currency) + '\nКоличество: ' \
                                              + str(stock.volume) + \
                                              '\nОтслеживание: '
                                    if int(stock.tracking):
                                        string += 'Да\nОжидаемый доход: ' \
                                                  + str(stock.profit_margin) + '\nОжидаемые потери: ' \
                                                  + str(stock.loss_limit) + '\n\n'
                                    else:
                                        string += 'Нет\n\n'

                                if string == "":
                                    string = 'У вас нет отслеживаемых активов'
                                self.send_message(event.user_id, string, 0)
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase,
                                                                           event.user_id))

                            # Добавление отслеживаемого актива
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'добавить актив ➕' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'добавить актив ➕' \
                                    and context[3]['text'].lower() == 'выберите действие' \
                                    and context[5]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id, "Введите название страны на английском",
                                                  keyboard=create_keyboard('Страны', self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите название страны на английском' \
                                    and context[3]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'выберите действие' \
                                    and context[7]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id, "Введите тикер или название актива", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите тикер или название актива' \
                                    and context[3]['text'].lower() == 'введите название страны на английском' \
                                    and context[5]['text'].lower() == 'выберите тип актива' \
                                    and context[7]['text'].lower() == 'выберите действие' \
                                    and context[9]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id, "Введите количество активов", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите количество активов' \
                                    and context[3]['text'].lower() == 'введите тикер или название актива' \
                                    and context[5]['text'].lower() == 'введите название страны на английском' \
                                    and context[7]['text'].lower() == 'выберите тип актива' \
                                    and context[9]['text'].lower() == 'выберите действие' \
                                    and context[11]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id, "Введите цену покупки", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите цену покупки' \
                                    and context[3]['text'].lower() == 'введите количество активов' \
                                    and context[5]['text'].lower() == 'введите тикер или название актива' \
                                    and context[7]['text'].lower() == 'введите название страны на английском' \
                                    and context[9]['text'].lower() == 'выберите тип актива' \
                                    and context[11]['text'].lower() == 'выберите действие' \
                                    and context[13]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id, "Присылать оповещения?",
                                                  keyboard=create_keyboard('да/нет', self.firebase))

                            # Без оповещений отслеживаемый актив
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'нет' \
                                    and context[1]['text'].lower() == 'присылать оповещения?' \
                                    and context[3]['text'].lower() == 'введите цену покупки' \
                                    and context[5]['text'].lower() == 'введите количество активов' \
                                    and context[7]['text'].lower() == 'введите тикер или название актива' \
                                    and context[9]['text'].lower() == 'введите название страны на английском' \
                                    and context[11]['text'].lower() == 'выберите тип актива' \
                                    and context[13]['text'].lower() == 'выберите действие' \
                                    and context[15]['text'].lower() == 'выберите тип отслеживания':
                                current_user = self.firebase.get_user(event.user_id)
                                if len(current_user.supported_stocks) != 0 and len(current_user.unsupported_stocks) \
                                        != 0:
                                    stock_id = max(current_user.supported_stocks[-1].id + 1,
                                                   current_user.unsupported_stocks[-1].id + 1)

                                elif len(current_user.supported_stocks) == 0 and \
                                        len(current_user.unsupported_stocks) > 0:
                                    stock_id = current_user.unsupported_stocks[-1].id + 1

                                elif len(current_user.supported_stocks) != 0 and \
                                        len(current_user.unsupported_stocks) == 0:
                                    stock_id = current_user.supported_stocks[-1].id + 1
                                else:
                                    stock_id = 1
                                try:
                                    current_stock = user_lib.SupportedStock(stock_id, context[6]['text'].upper(),
                                                                            context[2]['text'].lower(),
                                                                            context[4]['text'].lower(),
                                                                            context[8]['text'].lower(),
                                                                            0)
                                    result = check_stock(current_stock)
                                    if isinstance(result, str):
                                        self.send_a_message(event.user_id, "Акция не поддерживается!", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    else:
                                        current_user.add_new_sp_stock(current_stock)
                                        self.firebase.change_user(current_user)
                                        self.send_a_message(event.user_id, "Акция успешно добавлена", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                except TypeError:
                                    self.send_a_message(event.user_id, "Была допущена ошибка"
                                                                       " в формате введёных данных", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Отслеживаемый актив с оповешением
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'да' \
                                    and context[1]['text'].lower() == 'присылать оповещения?' \
                                    and context[3]['text'].lower() == 'введите цену покупки' \
                                    and context[5]['text'].lower() == 'введите количество активов' \
                                    and context[7]['text'].lower() == 'введите тикер или название актива' \
                                    and context[9]['text'].lower() == 'введите название страны на английском' \
                                    and context[11]['text'].lower() == 'выберите тип актива' \
                                    and context[13]['text'].lower() == 'выберите действие' \
                                    and context[15]['text'].lower() == 'выберите тип отслеживания':
                                self.send_a_message(event.user_id, "Введите сколько % вы хотете заработать", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите сколько % вы хотете заработать' \
                                    and context[3]['text'].lower() == 'присылать оповещения?' \
                                    and context[5]['text'].lower() == 'введите цену покупки' \
                                    and context[7]['text'].lower() == 'введите количество активов' \
                                    and context[9]['text'].lower() == 'введите тикер или название актива' \
                                    and context[11]['text'].lower() == 'введите название страны на английском' \
                                    and context[13]['text'].lower() == 'выберите тип актива' \
                                    and context[15]['text'].lower() == 'выберите действие' \
                                    and context[17]['text'].lower() == 'выберите тип отслеживания':
                                self.send_a_message(event.user_id, "Сколько % вы не боитесь потерять?", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'сколько % вы не боитесь потерять?' \
                                    and context[3]['text'].lower() == 'введите сколько % вы хотете заработать' \
                                    and context[5]['text'].lower() == 'присылать оповещения?' \
                                    and context[7]['text'].lower() == 'введите цену покупки' \
                                    and context[9]['text'].lower() == 'введите количество активов' \
                                    and context[11]['text'].lower() == 'введите тикер или название актива' \
                                    and context[13]['text'].lower() == 'введите название страны на английском' \
                                    and context[15]['text'].lower() == 'выберите тип актива' \
                                    and context[17]['text'].lower() == 'выберите действие' \
                                    and context[19]['text'].lower() == 'выберите тип отслеживания':
                                current_user = self.firebase.get_user(event.user_id)
                                if len(current_user.supported_stocks) != 0 and len(current_user.unsupported_stocks) \
                                        != 0:
                                    stock_id = max(current_user.supported_stocks[-1].id + 1,
                                                   current_user.unsupported_stocks[-1].id + 1)

                                elif len(current_user.supported_stocks) == 0 and \
                                        len(current_user.unsupported_stocks) > 0:
                                    stock_id = current_user.unsupported_stocks[-1].id + 1

                                elif len(current_user.supported_stocks) != 0 and \
                                        len(current_user.unsupported_stocks) == 0:
                                    stock_id = current_user.supported_stocks[-1].id + 1
                                else:
                                    stock_id = 1
                                try:
                                    current_stock = user_lib.SupportedStock(stock_id, context[10]['text'].upper(),
                                                                            context[6]['text'].lower(),
                                                                            context[8]['text'].lower(),
                                                                            context[12]['text'].lower(),
                                                                            1, 0,
                                                                            round(float(context[6]['text'].lower()) + (
                                                                                    float(context[6]['text'].lower())
                                                                                    / 100)
                                                                                  * int(context[2]['text'].lower()), 2),
                                                                            round(float(context[6]['text'].lower()) -
                                                                                  (float(context[6]['text'].lower())
                                                                                   / 100)
                                                                                  * int(context[0]['text'].lower()), 2))
                                    result = check_stock(current_stock)
                                    if isinstance(result, str):
                                        self.send_a_message(event.user_id, "Акция не поддерживается!", 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                    else:
                                        current_user.add_new_sp_stock(current_stock)
                                        self.firebase.change_user(current_user)
                                        self.send_a_message(event.user_id, "Акция успешно добавлена!\nЕё id = " +
                                                            str(stock_id), 0)
                                        self.send_message(event.user_id, 'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   event.user_id))
                                except TypeError:
                                    self.send_a_message(event.user_id, "Была допущена ошибка"
                                                                       " в формате введёных данных", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Удаление отслеживаемого актива
                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'удалить актив ❌' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and response == 'удалить актив ❌' \
                                    and context[1]['text'].lower() == 'выберите действие' \
                                    and context[3]['text'].lower() == 'выберите тип отслеживания':
                                self.send_message(event.user_id,
                                                  "Выберите тип актива", keyboard=create_keyboard('Тип актива',
                                                                                                  self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'выберите тип актива' \
                                    and context[2]['text'].lower() == 'удалить актив ❌' \
                                    and context[3]['text'].lower() == 'выберите действие' \
                                    and context[5]['text'].lower() == 'выберите тип отслеживания':
                                current_user = self.firebase.get_user(event.user_id)
                                string = ""
                                for stock in current_user.supported_stocks:
                                    string += str(stock.id) + ' - ' + str(stock.key) + ', цена покупки: ' \
                                              + str(stock.buying_price) + ' ' + str(stock.currency) + '\n'
                                if string == "":
                                    self.send_a_message(event.user_id, "Активов не найдено!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                else:
                                    self.send_a_message(event.user_id, "Список акций:\n" + string, 0)
                                    self.send_a_message(event.user_id, "Введите id акции для удаления", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите id акции для удаления' \
                                    and context[4]['text'].lower() == 'выберите тип актива' \
                                    and context[5]['text'].lower() == 'удалить актив ❌' \
                                    and context[6]['text'].lower() == 'выберите действие' \
                                    and context[8]['text'].lower() == 'выберите тип отслеживания':
                                self.send_a_message(event.user_id, "Введите цену продажи", 0)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[1]['text'].lower() == 'введите цену продажи' \
                                    and context[3]['text'].lower() == 'введите id акции для удаления' \
                                    and context[6]['text'].lower() == 'выберите тип актива' \
                                    and context[7]['text'].lower() == 'удалить актив ❌' \
                                    and context[8]['text'].lower() == 'выберите действие' \
                                    and context[10]['text'].lower() == 'выберите тип отслеживания':
                                try:
                                    current_user = self.firebase.get_user(event.user_id)
                                    current_stock = None
                                    for stock in current_user.supported_stocks:
                                        if int(stock.id) == int(context[2]['text'].lower()):
                                            current_stock = stock
                                            break

                                    current_user.supported_stocks.remove(current_stock)

                                    if current_stock.currency in current_user.general_sales.keys():
                                        current_user.general_purchases[str(current_stock.currency)] += \
                                            float(current_stock.buying_price) * int(current_stock.volume)
                                        current_user.general_sales[str(current_stock.currency)] += \
                                            float(response) * int(current_stock.volume)
                                    else:
                                        current_user.general_purchases[str(current_stock.currency)] = \
                                            float(current_stock.buying_price) * int(current_stock.volume)
                                        current_user.general_sales[str(current_stock.currency)] = \
                                            float(response) * int(current_stock.volume)

                                    self.firebase.change_user(current_user)
                                    self.send_a_message(event.user_id, "Акция успешно удалена!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                                except TypeError:
                                    self.send_a_message(event.user_id, "Введены некоректнные значения!", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))
                                except ValueError:
                                    self.send_a_message(event.user_id, "Введен не верный id акции", 0)
                                    self.send_message(event.user_id, 'Держи меню!',
                                                      keyboard=create_keyboard('меню', self.firebase,
                                                                               event.user_id))

                            # Приобретение подписки
                            elif response == 'приобрести подписку 🤑':
                                self.send_message(event.user_id,
                                                  "Чтобы приобрести подписку необходимо стать спонсором сообщества.\n"
                                                  "Перейди по ссылке ниже и оформите ежемесячную подписку: \n"
                                                  + str(link_on_pay))
                                self.send_message(event.user_id,
                                                  "Оформил подписку? 🤗",
                                                  keyboard=create_keyboard("да/нет", self.firebase))

                            elif context[0]['from_id'] == event.user_id \
                                    and context[3]['text'].lower() == 'приобрести подписку 🤑' \
                                    and response == 'да':
                                admins_list = self.firebase.get_admins()
                                self.send_message(event.user_id,
                                                  "Информация о вашей подписке была отправлена на проверку "
                                                  "администраторам, "
                                                  "вы получите доступ ко всем возможностям бота сразу после"
                                                  " рассмотрения заявки. "
                                                  "А пока можете пользоваться бесплатными функциями бота!",
                                                  keyboard=create_keyboard("меню", self.firebase))
                                sleep(0.5)
                                for admin in admins_list:
                                    self.send_message(admin, "Пользователь: " + "https://vk.com/id" + str(event.user_id)
                                                      + " - проверить" + " на подписку. \nid " +
                                                      str(event.user_id), self.firebase)

                            elif context[0]['from_id'] == event.user_id \
                                    and context[3]['text'].lower() == 'приобрести подписку 🤑' \
                                    and response == 'нет':
                                self.send_message(event.user_id,
                                                  "Очень жаль, что вы приняли такое решение!")
                                self.send_message(event.user_id, 'Держи меню!',
                                                  keyboard=create_keyboard('меню', self.firebase, event.user_id))

                            # Раздел администрирование
                            elif response == 'администрирование':
                                admins_list = self.firebase.get_admins()
                                if int(event.user_id) in admins_list:
                                    self.send_message(event.user_id, "+++")

                            elif context[0]['from_id'] == event.user_id and context[1]['text'].lower() == '+++':
                                continue

                            # Добавление дона
                            elif context[0]['from_id'] == event.user_id and context[2]['text'].lower() == '+++':
                                if context[1]['text'].lower() == 'подписка':
                                    if self.firebase.user_in_base(int(response)):
                                        user_ = self.firebase.get_user(int(response))
                                        day = dt.date.today() + dt.timedelta(days=32)
                                        new_format = "%d/%m/%Y"
                                        user_.subscription = day.strftime(new_format)
                                        self.firebase.change_user(user_)
                                        self.send_message(event.user_id, "Пользователь добавлен")
                                        sleep(0.5)
                                        self.send_message(int(response), 'Поздравляем! Ваша подписка успешно'
                                                                         ' подтверждена!\nДержи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   int(response)))

                                    else:
                                        day = dt.date.today() + dt.timedelta(days=30)
                                        new_format = "%d/%m/%Y"
                                        subscription = day.strftime(new_format)
                                        user = user_lib.User(int(response), subscription_=subscription)
                                        self.firebase.add_new_user(user)
                                        self.send_message(event.user_id, "Пользователь добавлен")
                                        sleep(0.5)
                                        self.send_message(int(response), 'Спасибо, что поддеражли наше сообщество! '
                                                                         'Ваша подписка подтверждена! '
                                                                         'Держи обновлённое меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   int(response)))

                                # Удаление дона
                                elif context[1]['text'].lower() == 'отказ':
                                    if self.firebase.user_in_base(int(response)):
                                        self.send_message(event.user_id, "Уведомление об отказе отправлено")
                                        user = self.firebase.get_user(int(response))
                                        user.subscription = 0
                                        self.firebase.change_user(user)
                                        sleep(0.5)
                                        self.send_message(int(response), 'К сожалению администратор не нашёл вас в'
                                                                         'списке донов. '
                                                                         'Жаль, что вы больше не с нами.\n'
                                                                         'Если вы считаете, что произошла ошибка '
                                                                         'обратитесь к администратору!\n'
                                                                         'Держи меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   int(response)))

                                    else:
                                        self.send_message(event.user_id, "Уведомление об отказе отправлено")
                                        sleep(0.5)
                                        self.send_message(int(response), 'К сожалению администратор не нашёл вас в'
                                                                         'списке донов.\n'
                                                                         'Если вы считаете, что произошла ошибка '
                                                                         'обратитесь к администратору!\n'
                                                                         'Держи обычное меню!',
                                                          keyboard=create_keyboard('меню', self.firebase,
                                                                                   int(response)))

                            # Крайний случай
                            elif response:
                                self.send_a_message(event.user_id, "Ошибка! Команда не найдена!", 0)
                                self.send_message(event.user_id, 'Держи меню!', keyboard=create_keyboard('меню',
                                                                                                         self.firebase,
                                                                                                         event.user_id))

            except Exception as e:
                self.send_a_message(160480415, str(e), 0)
                sleep(0.1)


def create_keyboard(response, fb, user_id=0):
    keyboard = VkKeyboard(one_time=True)

    if response == "привет":
        keyboard.add_button('Создать пользователя', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('Акции', color=VkKeyboardColor.PRIMARY)

    elif response == "меню":
        current_user = fb.get_user(user_id)
        if current_user == 0 or current_user.subscription == '0':
            keyboard.add_button('Приобрести подписку 🤑', color=VkKeyboardColor.POSITIVE)
            keyboard.add_line()
            keyboard.add_button('Информация о активе 📄', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Проверка на зависимость ⚖', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Оповещение о цене ✉', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Часто задаваемые вопросы ❓', color=VkKeyboardColor.SECONDARY)

        else:
            keyboard.add_button('Портфель 💼', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Информация 📖', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Анализ 🔎', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Отслеживание цены 📈', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Настройки ⚙', color=VkKeyboardColor.SECONDARY)
            keyboard.add_line()
            keyboard.add_button('Часто задаваемые вопросы ❓', color=VkKeyboardColor.SECONDARY)

    elif response == 'Тип актива':
        keyboard.add_button('Акция', color=VkKeyboardColor.PRIMARY)
        '''
        keyboard.add_line()
        keyboard.add_button('Фонд', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('ETF', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Индекс', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Облигация', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Товар', color=VkKeyboardColor.PRIMARY)
        '''

    elif response == 'Страны':
        keyboard.add_button('Russia', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('United States', color=VkKeyboardColor.SECONDARY)

    elif response == 'вопросы':
        keyboard.add_button('Поддерживаемые страны 🚩', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Поддерживаемые активы ✅', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Вопрос - Ответ ⁉', color=VkKeyboardColor.SECONDARY)

    elif response == 'Страны_info':
        keyboard.add_button('Russia', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('United States', color=VkKeyboardColor.PRIMARY)

    elif response == 'Анализ':
        keyboard.add_button('Проверка на зависимость ⚖', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Технический анализ 📝', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Точки пивот 💢', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Технические индикаторы 📊', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('График цены 📈', color=VkKeyboardColor.SECONDARY)

    elif response == 'Отслеживание':
        keyboard.add_button('Отслеживание актива 📌', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Оповещение о цене ✉', color=VkKeyboardColor.SECONDARY)

    elif response == 'купил/продал':
        keyboard.add_button('Добавить актив ➕', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Удалить актив ❌', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Список отслеживаемых активов 📜', color=VkKeyboardColor.SECONDARY)

    elif response == 'купил/продал_2':
        keyboard.add_button('Добавить актив ➕', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Удалить актив ❌', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Обновить цену актива 📝', color=VkKeyboardColor.SECONDARY)

        # keyboard.add_button('Изменить актив ✍🏻', color=VkKeyboardColor.SECONDARY)
        # изменение отселживания и % для оповещений

    elif response == 'Настройки':
        keyboard.add_button('Оповещения 📩', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Отменить подписку 🚫', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Сбросить статистику 🗑', color=VkKeyboardColor.SECONDARY)

    elif response == 'Портфель':
        keyboard.add_button('Мои активы 📂', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Статистика 💰', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Зависимость портфеля ⚖', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Пользовательские активы ✍🏻', color=VkKeyboardColor.SECONDARY)

    elif response == 'Информация':
        keyboard.add_button('Информация о активе 📄', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Лидеры роста 📈', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Лидеры падения 📉', color=VkKeyboardColor.SECONDARY)

    elif response == 'Часто задаваемые вопросы':
        keyboard.add_button('Список поддерживаемых стран', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Список поддерживаемых активов ', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Вопрос - Ответ ', color=VkKeyboardColor.SECONDARY)

    elif response == 'включить/отключить':
        keyboard.add_button('Включить', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Отключить', color=VkKeyboardColor.NEGATIVE)

    elif response == 'Период':
        keyboard.add_button('5 минут', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('15 минут', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('30 минут', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Час', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('5 часов', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('День', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Неделя', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Месяц', color=VkKeyboardColor.PRIMARY)

    elif response == 'Период_2':
        keyboard.add_button('День', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Неделя', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('Месяц', color=VkKeyboardColor.SECONDARY)

    elif response == 'Период_':
        keyboard.add_button('Неделя', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('Месяц', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('3 месяца', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('6 месяцев', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('1 год', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('2 года', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('5 лет', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('10 лет', color=VkKeyboardColor.PRIMARY)

    elif response == "нет подписки":
        keyboard.add_button('Приобрести подписку', color=VkKeyboardColor.POSITIVE)

    elif response == "да/нет":
        keyboard.add_button('Да', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Нет', color=VkKeyboardColor.NEGATIVE)

    elif response == "Валюта":
        keyboard.add_button('RUB', color=VkKeyboardColor.SECONDARY)
        keyboard.add_line()
        keyboard.add_button('USD', color=VkKeyboardColor.SECONDARY)

    return keyboard.get_keyboard()


def diff_daily(price_info):
    return price_info.differences_daily


def diff_weekly(price_info):
    return price_info.differences_weekly


def diff_monthly(price_info):
    return price_info.differences_monthly


def checking_prices_t(users, server_checker):
    stocks = []
    for user in users:
        if user.subscription != '0':
            for stock in user.supported_stocks:
                stocks.append(stock)

    for stock in server_checker.firebase.get_spy_stocks():
        stocks.append(stock)

    stocks = set(stocks)
    stocks = list(stocks)
    stock_filtered = []
    data_russia = ip.stocks.get_stocks_overview('russia', n_results=1000)
    data_usa = ip.stocks.get_stocks_overview('united states', n_results=1000)

    for stock in stocks:
        if stock.country == 'russia':
            data_ = data_russia.drop(columns=['name', 'country', 'turnover', 'change', 'change_percentage',
                                              'high', 'low'])
        elif stock.country == 'united states':
            data_ = data_usa.drop(columns=['name', 'country', 'turnover', 'change', 'change_percentage',
                                           'high', 'low'])
        else:
            data_ = ip.stocks.get_stocks_overview(stock.country, n_results=1000)
            data_ = data_.drop(columns=['name', 'country', 'turnover', 'change', 'change_percentage', 'high', 'low'])
        index = 0
        flag = 0
        for symbol in data_['symbol']:
            if symbol == stock.key:
                flag = 1
                break
            index += 1

        if flag:
            stock_filtered.append({stock.key: round(float(data_['last'][index]), 2)})
        else:
            if stock.country == 'russia':
                price_data = yf.download(tickers=str(stock.key) + '.ME', period='0')
                if not price_data.empty:
                    now = price_data['Close'][0]
                    now = round(now, 3)
                    stock_filtered.append({stock.key: now})
                else:
                    server_checker.send_a_message(str(160480415), "Акция " + str(stock.key) + " не скачать", 0)
                    continue

            elif stock.country == 'united states':
                price_data = yf.download(tickers=str(stock.key), period='0')
                if not price_data.empty:
                    now = price_data['Close'][0]
                    now = round(now, 3)
                    stock_filtered.append({stock.key: now})
                else:
                    server_checker.send_a_message(str(160480415), "Акция " + str(stock.key) + " не скачать", 0)
                    continue
            else:
                server_checker.send_a_message(str(160480415), "Акция " + str(stock.key) + " не скачать", 0)
                continue

    for user in users:
        if user.subscription != '0':
            for stock in user.supported_stocks:
                for current_stock in stock_filtered:
                    if (list(current_stock.keys()))[0] == stock.key:
                        now = (list(current_stock.values()))[0]
                        if stock.tracking != 0 and user.alerts == 1:
                            if stock.state == 0 and now > float(stock.profit_margin):
                                server_checker.send_a_message(user.id,
                                                              str(server_checker.get_user_name_from_vk_id(user.id))
                                                              + ", достигнут верхний порог прибыли, пора забирать "
                                                                "деньги!\n "
                                                                "Акция "
                                                              + str(stock.key) + " - " + str(now), 0)
                                stock.state = 1
                                stock.last_price = now

                            elif stock.state == 1 and now < 0.9 * float(stock.profit_margin):
                                server_checker.send_a_message(user.id,
                                                              str(server_checker.get_user_name_from_vk_id(user.id))
                                                              + ", время упущенно, денги ушли!\nАкция "
                                                              + str(stock.key) + " - " + str(now), 0)
                                stock.state = 0
                                stock.last_price = now

                            elif stock.state == 0 and now < float(stock.loss_limit):
                                server_checker.send_a_message(user.id,
                                                              str(server_checker.get_user_name_from_vk_id(user.id))
                                                              + ", пробит нижний порог, пора продавать!\nАкция "
                                                              + str(stock.key) + " - " + str(now), 0)
                                stock.state = 2
                                stock.last_price = now

                            elif stock.state == 2 and now > 1.1 * float(stock.loss_limit):
                                server_checker.send_a_message(user.id,
                                                              str(server_checker.get_user_name_from_vk_id(user.id))
                                                              + ", цена стабилизировалсь, у вас есть шансы!\nАкция "
                                                              + str(stock.key) + " - " + str(now), 0)
                                stock.state = 0
                                stock.last_price = now

                            else:
                                stock.last_price = now
                                break

                        else:
                            stock.last_price = now
                            break

    for stock in server_checker.firebase.get_spy_stocks():
        for current_stock in stock_filtered:
            if (list(current_stock.keys()))[0] == stock.key:
                now = (list(current_stock.values()))[0]
                if 0.98 * stock.goal <= now <= 1.02 * stock.goal:
                    server_checker.send_a_message(stock.user_id,
                                                  str(server_checker.get_user_name_from_vk_id(stock.user_id))
                                                  + ", цена по акции " + str(stock.key) + " достигнута!\n"
                                                  + "Последняя цена: " + str(now), 0)
                    server_checker.firebase.delete_spy_stock(stock)
                    break


def check_stock(stock):
    try:
        data_ = ip.stocks.get_stocks_overview(stock.country, n_results=1000)
        data_ = data_.drop(columns=['name', 'country', 'turnover', 'change', 'change_percentage', 'high', 'low'])
        flag = 0
        for symbol in data_['symbol']:
            if symbol == stock.key:
                flag = 1
                break

        if flag:
            stock.currency = data_['currency'][0]
            return 1
        else:
            if stock.country == 'russia':
                price_data = yf.download(tickers=str(stock.key) + '.ME', period='0')
                if not price_data.empty:
                    stock.currency = 'RUB'
                    return 1
                else:
                    return "Не удалось получить цену для акции, возможно она не поддерживается!"

            elif stock.country == 'united states':
                price_data = yf.download(tickers=str(stock.key), period='0')
                if not price_data.empty:
                    stock.currency = 'USD'
                    return 1
                else:
                    raise Exception("Не удалось получить цену для акции, возможно она не поддерживается!")
            else:
                return "Не удалось получить цену для акции, возможно она не поддерживается!"

    except Exception as e:
        return "Не удалось получить цену для акции, возможно она не поддерживается!"


def checking_subscription(users, server_checker_adm):
    for user in users:
        day = dt.datetime.today()
        check_day = user.subscription
        new_format = "%d/%m/%Y"
        day = day.strftime(new_format)
        if check_day == day:
            admins_list = server_checker_adm.firebase.get_admins()
            for admin in admins_list:
                server_checker_adm.send_message(admin, "Пользователь: " + "https://vk.com/id" + str(user.id)
                                                + " - проверить" + " на подписку (Срок подписки истёк). \nid " +
                                                str(user.id), server_checker_adm.firebase)
                sleep(0.5)
            server_checker_adm.send_message(str(user.id), "Прошёл месяц с момента последней проверки, поэтому"
                                                          " был сделан запрос администратору на проверку.",
                                            server_checker_adm.firebase)

        elif check_day == ((dt.datetime.today() - dt.timedelta(days=1)).strftime(new_format)):
            server_checker_adm.send_message(str(user.id), "Подписка не была продлена. Дополнительный функционал"
                                                          " отключен, если это"
                                                          " ошибка - обратитесь к администратору.",
                                            server_checker_adm.firebase)
            user.subscription = 0
            server_checker_adm.firebase.change_user(user)


def checking_differences(server_checker_differences):
    active_types = ['stock']
    countries = ['russia', 'united states']
    for type_a in active_types:
        for country in countries:
            if type_a == 'stock':
                data_s = ip.stocks.get_stocks_overview(country, n_results=1000)
                server_checker_differences.firebase.push_price_data(data_s, country)


def independent_analysis(user):
    if len(user.supported_stocks) == 0:
        return 'У вас нет активов!'
    elif len(user.supported_stocks) == 1:
        return 'У вас только один актив!'
    else:
        today = dt.date.today() - dt.timedelta(days=1)
        past_time = today - dt.timedelta(days=183)
        new_format = "%d/%m/%Y"
        today = today.strftime(new_format)
        past_time = past_time.strftime(new_format)
        table = None

        for stock in user.supported_stocks:
            try:
                if table is None:
                    table = ip.get_stock_historical_data(stock=stock.key.lower(), country=stock.country,
                                                         from_date=str(past_time), to_date=str(today))
                    table = table.drop(columns=['Open', 'High', 'Low', 'Volume', 'Currency'])
                    table.rename(columns={'Close': stock.key}, inplace=True)

                else:
                    table[stock.key] = ip.get_stock_historical_data(stock=stock.key.lower(), country=stock.country,
                                                                    from_date=str(past_time), to_date=str(today)).Close
            except Exception as e:
                if stock.country == 'russia':
                    price_data = yf.download(tickers=str(stock.key) + '.ME', start=today, end=past_time)
                    if not price_data.empty:
                        table[stock.key] = price_data['Close']
                    else:
                        continue

                elif stock.country == 'united states':
                    price_data = yf.download(tickers=str(stock.key), start=today, end=past_time)
                    if not price_data.empty:
                        table[stock.key] = price_data['Close']
                    else:
                        continue

        returns = table.pct_change()
        corr = returns.corr()
        corr_sum = 0.0
        count = 0
        for stock_a in user.supported_stocks:
            for stock_b in user.supported_stocks:
                if stock_a.key == stock_b.key:
                    continue
                corr_sum += round(corr[stock_a.key][stock_b.key], 3)
                count += 1

        try:
            result = corr_sum / count
            return result
        except ZeroDivisionError:
            return 'Поддерживаемых активов не найдено!'


def technical_analysis(name_of_active, country, product_type, period):
    product_types = ['stock', 'fund', 'etf', 'index', 'bond', 'commodities']
    countries = []
    if product_type not in product_types:
        if product_type == 'акция':
            product_type = product_types[0]
            countries = ip.stocks.get_stock_countries()
        elif product_type == 'фонд':
            product_type = product_types[1]
            countries = ip.funds.get_fund_countries()
        elif product_type == 'etf':
            countries = ip.etfs.get_etf_countries()
        elif product_type == 'индекс':
            product_type = product_types[3]
            countries = ip.indices.get_index_countries()
        elif product_type == 'облигация':
            product_type = product_types[4]
            countries = ip.bonds.get_bond_countries()
        elif product_type == 'товар':
            product_type = product_types[5]
            countries = ip.stocks.get_stock_countries()
        else:
            return 'Error in type!'

    if country not in countries:
        return 'Error in country, you may have made a mistake or the country is not supported.'

    if product_type == product_types[0]:
        name_of_active = name_of_active.upper()
        if name_of_active not in ip.stocks.get_stocks_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[1]:
        if name_of_active not in ip.funds.get_funds_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[2]:
        if name_of_active not in ip.etfs.get_etfs_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[3]:
        if name_of_active not in ip.indices.get_indices_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[4]:
        if name_of_active not in ip.bonds.get_bonds_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[5]:
        if name_of_active not in ip.commodities.get_commodities_list():
            return 'Error in name of active!'

    if period == '5 минут':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='5mins')
        return data

    elif period == '15 минут':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='15mins')
        return data

    elif period == '30 минут':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='30mins')
        return data

    elif period == 'час':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='1hour')
        return data

    elif period == '5 часов':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='5hours')
        return data

    elif period == 'день':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='daily')
        return data

    elif period == 'неделя':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='weekly')
        return data

    elif period == 'месяц':
        data = ip.moving_averages(name=name_of_active, country=country, product_type=product_type, interval='monthly')
        return data

    else:
        return 'Error in period'


def technical_indicators(name_of_active, country, product_type, period):
    product_types = ['stock', 'fund', 'etf', 'index', 'bond', 'commodities']
    countries = []
    if product_type not in product_types:
        if product_type == 'акция':
            product_type = product_types[0]
            countries = ip.stocks.get_stock_countries()
        elif product_type == 'фонд':
            product_type = product_types[1]
            countries = ip.funds.get_fund_countries()
        elif product_type == 'etf':
            countries = ip.etfs.get_etf_countries()
        elif product_type == 'индекс':
            product_type = product_types[3]
            countries = ip.indices.get_index_countries()
        elif product_type == 'облигация':
            product_type = product_types[4]
            countries = ip.bonds.get_bond_countries()
        elif product_type == 'товар':
            product_type = product_types[5]
            countries = ip.stocks.get_stock_countries()
        else:
            return 'Error in type!'

    if country not in countries:
        return 'Error in country, you may have made a mistake or the country is not supported.'

    if product_type == product_types[0]:
        name_of_active = name_of_active.upper()
        if name_of_active not in ip.stocks.get_stocks_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[1]:
        if name_of_active not in ip.funds.get_funds_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[2]:
        if name_of_active not in ip.etfs.get_etfs_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[3]:
        if name_of_active not in ip.indices.get_indices_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[4]:
        if name_of_active not in ip.bonds.get_bonds_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[5]:
        if name_of_active not in ip.commodities.get_commodities_list():
            return 'Error in name of active!'

    if period == '5 минут':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='5mins')
        return data

    elif period == '15 минут':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='15mins')
        return data

    elif period == '30 минут':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='30mins')
        return data

    elif period == 'час':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='1hour')
        return data

    elif period == '5 часов':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='5hours')
        return data

    elif period == 'день':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='daily')
        return data

    elif period == 'неделя':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='weekly')
        return data

    elif period == 'месяц':
        data = ip.technical_indicators(name=name_of_active, country=country, product_type=product_type,
                                       interval='monthly')
        return data

    else:
        return 'Error in period'


def pivot_points(name_of_active, country, product_type, period):
    product_types = ['stock', 'fund', 'etf', 'index', 'bond', 'commodities']
    countries = []
    if product_type not in product_types:
        if product_type == 'акция':
            product_type = product_types[0]
            countries = ip.stocks.get_stock_countries()
        elif product_type == 'фонд':
            product_type = product_types[1]
            countries = ip.funds.get_fund_countries()
        elif product_type == 'etf':
            countries = ip.etfs.get_etf_countries()
        elif product_type == 'индекс':
            product_type = product_types[3]
            countries = ip.indices.get_index_countries()
        elif product_type == 'облигация':
            product_type = product_types[4]
            countries = ip.bonds.get_bond_countries()
        elif product_type == 'товар':
            product_type = product_types[5]
            countries = ip.stocks.get_stock_countries()
        else:
            return 'Error in type!'

    if country not in countries:
        return 'Error in country, you may have made a mistake or the country is not supported.'

    if product_type == product_types[0]:
        name_of_active = name_of_active.upper()
        if name_of_active not in ip.stocks.get_stocks_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[1]:
        if name_of_active not in ip.funds.get_funds_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[2]:
        if name_of_active not in ip.etfs.get_etfs_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[3]:
        if name_of_active not in ip.indices.get_indices_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[4]:
        if name_of_active not in ip.bonds.get_bonds_list(country):
            return 'Error in name of active!'
    elif product_type == product_types[5]:
        if name_of_active not in ip.commodities.get_commodities_list():
            return 'Error in name of active!'

    if period == '5 минут':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='5mins')
        return data

    elif period == '15 минут':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='15mins')
        return data

    elif period == '30 минут':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='30mins')
        return data

    elif period == 'час':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='1hour')
        return data

    elif period == '5 часов':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='5hours')
        return data

    elif period == 'день':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='daily')
        return data

    elif period == 'неделя':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='weekly')
        return data

    elif period == 'месяц':
        data = ip.technical.pivot_points(name=name_of_active, country=country, product_type=product_type,
                                         interval='monthly')
        return data

    else:
        return 'Error in period'


def history_of_active(name_of_active, country, product_type, period):
    try:
        product_types = ['stock', 'fund', 'etf', 'index', 'bond', 'commodities']
        countries = []
        if product_type not in product_types:
            if product_type == 'акция':
                product_type = product_types[0]
                countries = ip.stocks.get_stock_countries()
            elif product_type == 'фонд':
                product_type = product_types[1]
                countries = ip.funds.get_fund_countries()
            elif product_type == 'etf':
                countries = ip.etfs.get_etf_countries()
            elif product_type == 'индекс':
                product_type = product_types[3]
                countries = ip.indices.get_index_countries()
            elif product_type == 'облигация':
                product_type = product_types[4]
                countries = ip.bonds.get_bond_countries()
            elif product_type == 'товар':
                product_type = product_types[5]
                countries = ip.stocks.get_stock_countries()
            else:
                return 'Была допущена ошибка в типе актива или он не поддерживается!'

        if country not in countries:
            return 'Была допущена ошибка в названии страны или она не поддерживается!'

        if product_type == product_types[0]:
            name_of_active = name_of_active.upper()
            if name_of_active not in ip.stocks.get_stocks_list(country):
                return 'Возможно была допущена ошибка в тикере / имени актива или он не поддерживается.\nОбратитесь к ' \
                       'администратору, чтобы уточнить информацию! '

            if period == 'неделя':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=7)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'месяц':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=31)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '3 месяца':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=93)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '6 месяцев':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=183)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'год':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=365)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '2 года':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=730)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '5 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=1825)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '10 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=3650)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.get_stock_historical_data(stock=name_of_active, country=country,
                                                    from_date=str(past_time), to_date=str(today))
                return data

            else:
                return 'Ошибка в периоде!'

        elif product_type == product_types[1]:
            if name_of_active not in ip.funds.get_funds_list(country):
                return 'Возможно была допущена ошибка в тикере / имени актива или он не поддерживается.\nОбратитесь к ' \
                       'администратору, чтобы уточнить информацию! '

            if period == 'неделя':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=7)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'месяц':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=31)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '3 месяца':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=93)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '6 месяцев':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=183)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'год':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=365)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '2 года':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=730)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '5 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=1825)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '10 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=3650)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.funds.get_fund_historical_data(fund=name_of_active, country=country,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            else:
                return 'Ошибка в периоде!'

        elif product_type == product_types[2]:
            if name_of_active not in ip.etfs.get_etfs_list(country):
                return 'Возможно была допущена ошибка в тикере / имени актива или он не поддерживается.\nОбратитесь к ' \
                       'администратору, чтобы уточнить информацию! '

            if period == 'неделя':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=7)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'месяц':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=31)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == '3 месяца':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=93)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == '6 месяцев':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=183)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'год':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=365)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == '2 года':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=730)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == '5 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=1825)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            elif period == '10 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=3650)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.etfs.get_etf_historical_data(etf=name_of_active, country=country,
                                                       from_date=str(past_time), to_date=str(today))
                return data

            else:
                return 'Ошибка в периоде!'

        elif product_type == product_types[3]:
            if name_of_active not in ip.indices.get_indices_list(country):
                return 'Возможно была допущена ошибка в тикере / имени актива или он не поддерживается.\nОбратитесь к ' \
                       'администратору, чтобы уточнить информацию! '

            if period == 'неделя':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=7)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'месяц':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=31)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == '3 месяца':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=93)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == '6 месяцев':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=183)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'год':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=365)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == '2 года':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=730)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == '5 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=1825)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            elif period == '10 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=3650)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.indices.get_index_historical_data(index=name_of_active, country=country,
                                                            from_date=str(past_time), to_date=str(today))
                return data

            else:
                return 'Ошибка в периоде!'

        elif product_type == product_types[4]:
            if name_of_active not in ip.bonds.get_bonds_list(country):
                return 'Возможно была допущена ошибка в тикере / имени актива или он не поддерживается.\nОбратитесь к ' \
                       'администратору, чтобы уточнить информацию! '

            if period == 'неделя':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=7)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'месяц':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=31)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '3 месяца':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=93)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '6 месяцев':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=183)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'год':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=365)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '2 года':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=730)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '5 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=1825)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            elif period == '10 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=3650)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.bonds.get_bond_historical_data(bond=name_of_active,
                                                         from_date=str(past_time), to_date=str(today))
                return data

            else:
                return 'Ошибка в периоде!'

        elif product_type == product_types[5]:
            if name_of_active not in ip.commodities.get_commodities_list():
                return 'Возможно была допущена ошибка в тикере / имени актива или он не поддерживается.\nОбратитесь к ' \
                       'администратору, чтобы уточнить информацию! '

            if period == 'неделя':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=7)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'месяц':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=31)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '3 месяца':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=93)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '6 месяцев':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=183)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == 'год':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=365)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '2 года':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=730)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '5 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=1825)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            elif period == '10 лет':
                today = dt.date.today() - dt.timedelta(days=1)
                past_time = today - dt.timedelta(days=3650)
                new_format = "%d/%m/%Y"
                today = today.strftime(new_format)
                past_time = past_time.strftime(new_format)
                data = ip.commodities.get_commodity_historical_data(commodity=name_of_active, country=country,
                                                                    from_date=str(past_time), to_date=str(today))
                return data

            else:
                return 'Ошибка в периоде!'

    except Exception as e:
        return str(e)


def build_graph(data):
    data.Close.plot()
    plt.savefig('hist.png')


def active_info(server, user_id, name_of_active, country, product_type):
    hst = history_of_active(name_of_active, country, product_type, '3 месяца')
    if isinstance(hst, str):
        server.send_a_message(user_id, hst, 0)

    else:
        hst.Close.plot()
        plt.savefig('h_' + name_of_active + '.png')
        plt.close()
        upload = VkUpload(server.vk_api)
        t_a = technical_analysis(name_of_active, country, product_type, 'неделя')
        t_i = technical_indicators(name_of_active, country, product_type, 'месяц')
        p_p = pivot_points(name_of_active, country, product_type, 'месяц')

        if product_type == 'акция':
            data_ = ip.stocks.get_stocks_overview(country, n_results=1000)
            data_ = data_.drop(columns=['name', 'country', 'turnover', 'change', 'change_percentage', 'high', 'low'])
            index = 0
            flag = 0
            for symbol in data_['symbol']:
                if symbol == name_of_active:
                    flag = 1
                    break
                index += 1

            data = ip.stocks.get_stock_information(name_of_active, country)
            result_str = "Информация о активе " + name_of_active + "\n\n"
            if flag:
                result_str += "Цена сейчас: " + str(round(float(data_['last'][index]), 2)) + \
                              ' ' + str(data_['currency'][index]) + "\n"
            else:
                result_str += "Цена вчера: " + str(round(float(data["Prev. Close"]), 2)) + "\n"
            result_str += "Последние дивиденды: " + data["Dividend (Yield)"] + "\n"
            result_str += "Изменение цены за год: " + data["1-Year Change"] + "\n"
            result_str += "Предположительная дата следующих девидендов: " + data["Next Earnings Date"] + "\n"
            result_str += "\nРезультаты техического анализа на месяц: " + str(t_a['ema_signal'][0]) + '\n'
            result_str += "\nТехнический индикатор RSI: \nValue = " + str(t_i['value'][0]) + \
                          "\nSignal = " + str(t_i['signal'][0]) + "\n\n"
            result_str += "Классические точки пивот на месяц:\n" + 's_3: ' + str(p_p['s3'][0]) + '\ns_2: ' \
                          + str(p_p['s2'][0]) + '\ns_1: ' + str(p_p['s1'][0]) + '\nc_0: ' \
                          + str(p_p['pivot_points'][0]) + '\nr_1: ' + str(p_p['r1'][0]) + '\nr_2: ' \
                          + str(p_p['r2'][0]) + '\nr_3: ' + str(p_p['r3'][0]) + '\n\n'

            result_str += "Каждый инструмет анализа в полном объёме доступен для Донов.\n\n"
            result_str += "График цены за последние три месяца"
            server.send_message(int(user_id), result_str, 0)
            server.send_photo(user_id, *server.upload_photo(upload, 'h_' + name_of_active + '.png'))
            sleep(0.3)

        else:
            server.send_message(int(user_id), 'К сожалению данная функция сейчас не поддерживается :-(', 0)
