import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import user
import os


class FireBase:
    def __init__(self):
        config_values = {
            "type": "service_account",
            "project_id": os.environ['PROJECT_ID'],
            "private_key_id": os.environ['PRIVATE_KEY_ID'],
            "private_key": os.environ['PRIVATE_KEY'],
            "client_email": os.environ['CLIENT_EMAIL'],
            "client_id": os.environ['CLIENT_ID'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ['CLIENT_X509_CERT_URL']
        }
        self.cred = credentials.Certificate(config_values)
        self.firebase_admin = firebase_admin.initialize_app(self.cred, {'databaseURL': os.environ['INITIALIZE_APP']})
        self.ref = db.reference('/')

    def add_new_user(self, user_obj):
        self.ref = db.reference("/users")
        self.ref.child(str(user_obj.id)).set(user_obj.encode_user())

    def add_spy_stock(self, stock):
        self.ref = db.reference("/spy_stocks")
        self.ref.push().set(stock.encode_stock())

    def get_spy_stocks(self):
        self.ref = db.reference("/spy_stocks")
        stocks = []
        data = self.ref.get()

        if data is not None:
            for stock_data_ in data:
                if data[stock_data_] is None:
                    continue
                current_stock = self.get_spy_stock_p(stock_data_)
                if current_stock:
                    stocks.append(current_stock)
                else:
                    continue
        return stocks

    def get_spy_stock_p(self, path):
        self.ref = db.reference("/spy_stocks/" + str(path))
        stock_data = self.ref.get()
        if stock_data is None:
            return 0
        else:
            current_stock = user.SpyStock(stock_data["user_id"], stock_data["key"], stock_data["country"],
                                          stock_data["goal"], stock_data["active_type"])
            return current_stock

    def delete_spy_stock(self, stock):
        self.ref = db.reference("/spy_stocks")
        data = self.ref.get()

        for stock_data_ in data:
            if data[stock_data_] is None:
                continue
            current_stock = self.get_spy_stock_p(stock_data_)
            if current_stock == stock:
                self.ref = db.reference("/spy_stocks/" + str(stock_data_))
                self.ref.set({})

    def get_users(self):
        self.ref = db.reference("/users")
        users = []
        data = self.ref.get()

        for user_data_ in data:
            if data[user_data_] is None:
                continue
            current_user = self.get_user(user_data_)
            users.append(current_user)
        return users

    def get_user(self, user_id):
        self.ref = db.reference("/users/" + str(user_id))
        user_data = self.ref.get()
        if user_data is None:
            return 0
        else:
            current_user = user.User(user_data["id"], user_data["alerts"], user_data["subscription"],
                                     user_data["purchases"], user_data["sales"])

            if len(user_data["sp_stock_id"]) == 1 and user_data["sp_stock_id"][0] == '-' \
                    and len(user_data["stock_id"]) == 1 and user_data["stock_id"][0] == '-':
                return current_user

            if not (len(user_data["sp_stock_id"]) == 1 and user_data["sp_stock_id"][0] == '-'):
                for index in range(0, len(user_data["sp_stock_id"])):
                    current_stock = user.SupportedStock(user_data["sp_stock_id"][index],
                                                        user_data["sp_stock_key"][index],
                                                        user_data["sp_stock_buying_price"][index],
                                                        user_data["sp_stock_volume"][index],
                                                        user_data["sp_stock_country"][index],
                                                        user_data["sp_stock_tracking"][index],
                                                        user_data["sp_stock_state"][index],
                                                        user_data["sp_stock_profit_margin"][index],
                                                        user_data["sp_stock_loss_limit"][index],
                                                        user_data["sp_stock_last_price"][index],
                                                        user_data["sp_stock_currency"][index], )
                    current_user.add_new_sp_stock(current_stock)

            if not (len(user_data["stock_id"]) == 1 and user_data["stock_id"][0] == '-'):
                for index in range(0, len(user_data["stock_id"])):
                    current_stock = user.CustomStock(user_data["stock_id"][index],
                                                        user_data["stock_key"][index],
                                                        user_data["stock_buying_price"][index],
                                                        user_data["stock_volume"][index],
                                                        user_data["stock_country"][index],
                                                        user_data["stock_currency"][index],
                                                        user_data["stock_last_price"][index])
                    current_user.add_new_stock(current_stock)
            return current_user

    def user_in_base(self, user_id):
        self.ref = db.reference("/users/" + str(user_id))
        user_data = self.ref.get()
        if user_data is None:
            return False
        return True

    def change_user(self, user_obj):
        if not self.user_in_base(user_obj.id):
            self.add_new_user(user_obj)
            return

        self.ref = db.reference("/users/" + str(user_obj.id))
        self.ref.update(user_obj.encode_user())
        return

    def update_users(self, users_obj):
        for user_obj in users_obj:
            self.change_user(user_obj)

    def get_admins(self):
        self.ref = db.reference("/admins_list/")
        admins = self.ref.get()
        admin_list = []
        for ad in admins:
            admin_list.append(int(ad))
        return admin_list

    def get_price_info(self, country, name_of_active):
        self.ref = db.reference("/price_info/stocks/" + country + '/' + name_of_active)
        data = self.ref.get()
        active = user.PriceActive(data['key'], data['prices'], data['difference_daily'],
                                  data['difference_weekly'], data['difference_monthly'])
        return active

    def get_prices_info(self, country, product_type):
        self.ref = db.reference("/price_info/" + str(product_type) + '/' + country)
        data = self.ref.get()
        actives = []
        for data_ in data:
            actives.append(user.PriceActive(data[data_]['key'], data[data_]['prices'], data[data_]['difference_daily'],
                                            data[data_]['difference_weekly'], data[data_]['difference_monthly']))
        return actives

    def add_price_data(self):
        """Используется для объявления"""
        self.ref = db.reference("/price_info/stocks/united states")
        import investpy as ip
        data_ = ip.stocks.get_stocks_overview('united states', n_results=1000)
        data_ = data_.drop(columns=['name', 'country', 'turnover', 'change', 'change_percentage', 'high', 'low'])
        index = 0
        for symbol in data_['symbol']:
            price = [round(float(data_['last'][index]), 2)]
            difference_day = 0.0
            difference_week = 0.0
            difference_month = 0.0
            active = user.PriceActive(symbol, price, difference_day, difference_week, difference_month)
            self.ref.child(str(active.key)).set(active.encode_active())
            index += 1

    def push_price_data(self, price_data, country):
        self.ref = db.reference("/price_info/stocks/" + str(country))
        index = 0
        set_symbols = set(price_data['symbol'])
        for symbol in price_data['symbol']:
            if country == 'russia' and symbol == 'AFKS':
                index += 1
                continue

            if country == 'united states' and symbol == 'BA':
                index += 1
                continue

            active_old = self.get_price_info(country, symbol)
            active_old.prices.append(round(float(price_data['last'][index]), 2))
            if len(active_old.prices) > 1:
                try:
                    active_old.differences_daily = round(((active_old.prices[-1] / active_old.prices[-2]) * 100) -
                                                         100.0, 2)
                except ZeroDivisionError:
                    active_old.differences_daily = 0.0
            if len(active_old.prices) > 7:
                try:
                    active_old.differences_weekly = round(((active_old.prices[-1] / active_old.prices[-8]) * 100) -
                                                          100.0, 2)
                except ZeroDivisionError:
                    active_old.differences_weekly = 0.0
            if len(active_old.prices) > 30:
                try:
                    active_old.differences_monthly = round(((active_old.prices[-1] / active_old.prices[-31]) * 100) -
                                                           100.0, 2)
                except ZeroDivisionError:
                    active_old.differences_monthly = 0.0

            if len(active_old.prices) == 32:
                active_old.prices.pop(0)

            self.ref = db.reference("/price_info/stocks/" + str(country) + '/' + str(active_old.key))
            self.ref.update(active_old.encode_active())
            index += 1

