from hashlib import md5


class User:
    def __init__(self, id_, alerts_=1, subscription_=0, general_purchases_=None, general_sales_=None):
        if general_sales_ is None:
            general_sales_ = {'RUB': 0.0, 'USD': 0.0}

        if general_purchases_ is None:
            general_purchases_ = {'RUB': 0.0, 'USD': 0.0}

        self.id = id_
        self.alerts = alerts_
        self.subscription = subscription_
        self.supported_stocks = []
        self.unsupported_stocks = []
        self.general_purchases = general_purchases_
        self.general_sales = general_sales_

    def add_new_sp_stock(self, stock):
        self.supported_stocks.append(stock)

    def add_new_stock(self, stock):
        self.unsupported_stocks.append(stock)

    def delete_sp_stock(self, stock):
        self.supported_stocks.remove(stock)

    def delete_stock(self, stock):
        self.unsupported_stocks.remove(stock)

    def set_alerts(self, flag):
        self.alerts = flag

    def set_subscription(self, date):
        self.subscription = date

    def encode_user(self):
        encode_id = str(self.id)
        encode_alerts = str(self.alerts)
        encode_subscription = str(self.subscription)
        encode_purchases = self.general_purchases
        encode_sales = self.general_sales

        encode_sp_stock_id = []
        encode_sp_stock_key = []
        encode_sp_stock_buying_price = []
        encode_sp_stock_volume = []
        encode_sp_stock_country = []
        encode_sp_stock_tracking = []
        encode_sp_stock_currency = []
        encode_sp_stock_last_price = []
        encode_sp_stock_state = []
        encode_sp_stock_profit_margin = []
        encode_sp_stock_loss_limit = []

        for stock in self.supported_stocks:
            encode_sp_stock_id.append(str(stock.id))
            encode_sp_stock_key.append(str(stock.key))
            encode_sp_stock_buying_price.append(str(stock.buying_price))
            encode_sp_stock_volume.append(str(stock.volume))
            encode_sp_stock_country.append(str(stock.country))
            encode_sp_stock_tracking.append(str(stock.tracking))
            encode_sp_stock_currency.append(str(stock.currency))
            encode_sp_stock_last_price.append(str(stock.last_price))
            encode_sp_stock_state.append(str(stock.state))
            encode_sp_stock_profit_margin.append(str(stock.profit_margin))
            encode_sp_stock_loss_limit.append(str(stock.loss_limit))

        if len(self.supported_stocks) == 0:
            encode_sp_stock_id.append(str('-'))
            encode_sp_stock_key.append(str('-'))
            encode_sp_stock_buying_price.append(str('-'))
            encode_sp_stock_volume.append(str('-'))
            encode_sp_stock_country.append(str('-'))
            encode_sp_stock_tracking.append(str('-'))
            encode_sp_stock_currency.append(str('-'))
            encode_sp_stock_last_price.append(str('-'))
            encode_sp_stock_state.append(str('-'))
            encode_sp_stock_profit_margin.append(str('-'))
            encode_sp_stock_loss_limit.append(str('-'))

        encode_stock_id = []
        encode_stock_key = []
        encode_stock_buying_price = []
        encode_stock_volume = []
        encode_stock_country = []
        encode_stock_last_price = []

        for stock in self.unsupported_stocks:
            encode_stock_id.append(str(stock.id))
            encode_stock_key.append(str(stock.key))
            encode_stock_buying_price.append(str(stock.buying_price))
            encode_stock_volume.append(str(stock.volume))
            encode_stock_country.append(str(stock.country))
            encode_stock_last_price.append(str(stock.last_price))

        if len(self.unsupported_stocks) == 0:
            encode_stock_id.append(str('-'))
            encode_stock_key.append(str('-'))
            encode_stock_buying_price.append(str('-'))
            encode_stock_volume.append(str('-'))
            encode_stock_country.append(str('-'))
            encode_stock_last_price.append(str('-'))

        to_json = {'id': encode_id, 'alerts': encode_alerts, 'subscription': encode_subscription,
                   'purchases': encode_purchases, 'sales': encode_sales, 'sp_stock_id': encode_sp_stock_id,
                   'sp_stock_key': encode_sp_stock_key, 'sp_stock_buying_price': encode_sp_stock_buying_price,
                   'sp_stock_volume': encode_sp_stock_volume, 'sp_stock_country': encode_sp_stock_country,
                   'sp_stock_tracking': encode_sp_stock_tracking, 'sp_stock_currency': encode_sp_stock_currency,
                   'sp_stock_last_price': encode_sp_stock_last_price,
                   'sp_stock_state': encode_sp_stock_state,
                   'sp_stock_profit_margin': encode_sp_stock_profit_margin,
                   'sp_stock_loss_limit': encode_sp_stock_loss_limit,
                   'stock_id': encode_stock_id, 'stock_key': encode_stock_key,
                   'stock_buying_price': encode_stock_buying_price, 'stock_volume': encode_stock_volume,
                   'stock_country': encode_stock_country, 'stock_last_price': encode_stock_last_price}
        return to_json


class SupportedStock:
    def __init__(self, id_, key_, buying_price_, volume_, country_, tracking_, state_='-',
                 profit_margin_='-', loss_limit_='-', last_price_='-', currency_='-'):

        try:
            self.id = int(id_)
            self.key = key_
            self.buying_price = float(buying_price_)
            self.volume = int(volume_)
            self.country = str(country_)
            self.tracking = int(tracking_)
            if currency_ == '-':
                self.currency = '-'
            else:
                self.currency = currency_

            if last_price_ == '-':
                self.last_price = float(buying_price_)
            else:
                self.last_price = float(last_price_)

            if state_ != '-':
                self.state = int(state_)
                self.profit_margin = float(profit_margin_)
                self.loss_limit = float(loss_limit_)
            else:
                self.state = state_
                self.profit_margin = profit_margin_
                self.loss_limit = loss_limit_

        except TypeError:
            raise TypeError

    def __eq__(self, other):
        if self.id == other.id \
                and self.key == other.key:
            return True
        else:
            return False

    def __hash__(self):
        enc_str = self.key + str(self.id) + self.country + str(self.volume) + str(self.buying_price)
        return int(md5(enc_str.encode()).hexdigest(), 16)


class CustomStock:
    def __init__(self, id_, key_, buying_price_, volume_, country_, currency_, last_price_='-'):
        try:
            self.id = int(id_)
            self.key = key_
            self.buying_price = float(buying_price_)
            self.volume = int(volume_)
            self.country = str(country_)
            self.currency = currency_

            if last_price_ == '-':
                self.last_price = float(buying_price_)
            else:
                self.last_price = float(last_price_)

        except TypeError:
            raise TypeError

    def __eq__(self, other):
        if self.id == other.id \
                and self.key == other.key:
            return True
        else:
            return False

    def __hash__(self):
        enc_str = self.key + str(self.id) + self.country + str(self.volume) + str(self.buying_price)
        return int(md5(enc_str.encode()).hexdigest(), 16)


class SpyStock:
    def __init__(self, user_id_, key_, country_, goal_, active_type_):
        self.user_id = user_id_
        self.key = key_
        self.goal = float(goal_)
        self.country = str(country_)
        self.active_type = active_type_

    def __eq__(self, other):
        if int(self.user_id) == int(other.user_id) \
                and self.key == other.key \
                and str(self.goal) == str(other.goal):
            return True
        else:
            return False

    def __hash__(self):
        enc_str = self.key + str(self.goal) + self.country + self.active_type + str(self.user_id)
        return int(md5(enc_str.encode()).hexdigest(), 16)

    def encode_stock(self):
        encode_user_id = str(self.user_id)
        encode_key = str(self.key)
        encode_goal = str(self.goal)
        encode_country = str(self.country)
        encode_active_type = str(self.active_type)

        to_json = {'user_id': encode_user_id, 'key': encode_key, 'goal': encode_goal,
                   'country': encode_country, 'active_type': encode_active_type}
        return to_json


class PriceActive:
    def __init__(self, key_, prices_, differences_daily_, differences_weekly_, differences_monthly_):
        self.key = key_
        self.prices = []
        for price in prices_:
            self.prices.append(float(price))

        self.differences_daily = float(differences_daily_)
        self.differences_weekly = float(differences_weekly_)
        self.differences_monthly = float(differences_monthly_)

    def encode_active(self):
        encode_key = str(self.key)
        encode_prices = []
        encode_differences_daily = str(self.differences_daily)
        encode_differences_weekly = str(self.differences_weekly)
        encode_differences_monthly = str(self.differences_monthly)

        for price in self.prices:
            encode_prices.append(str(price))

        to_json = {'key': encode_key, 'prices': encode_prices, 'difference_daily': encode_differences_daily,
                   'difference_weekly': encode_differences_weekly, 'difference_monthly': encode_differences_monthly}
        return to_json

    def __eq__(self, other):
        if self.key == other.key:
            return True
        else:
            return False
