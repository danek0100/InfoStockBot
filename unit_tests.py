# Base unit-test without test-framework

import user


def user_test(test_user, id_, alerts_=1, subscription_=0, general_purchases_=None, general_sales_=None,
              supported_stock_=None, unsupported_stock_=None):

    if general_purchases_ is None:
        general_purchases_ = {'RUB': 0.0, 'USD': 0.0}
    if general_sales_ is None:
        general_sales_ = {'RUB': 0.0, 'USD': 0.0}
    if unsupported_stock_ is None:
        unsupported_stock_ = []
    if supported_stock_ is None:
        supported_stock_ = []

    assert (test_user.id == id_)
    assert (test_user.alerts == alerts_)
    assert (test_user.subscription == subscription_)
    assert (test_user.general_purchases == general_purchases_)
    assert (test_user.general_sales == general_sales_)
    assert (test_user.supported_stocks == supported_stock_)
    assert (test_user.unsupported_stocks == unsupported_stock_)


def supported_stock_test(supported_stock, id_, key_, buying_price_, volume_, country_, tracking_, state_='-',
                            profit_margin_='-', loss_limit_='-', last_price_='-', currency_='-'):
    assert (supported_stock.id == id_)
    assert (supported_stock.key == key_)
    assert (supported_stock.buying_price == buying_price_)
    assert (supported_stock.volume == volume_)
    assert (supported_stock.country == country_)
    assert (supported_stock.tracking == tracking_)
    assert (supported_stock.currency == currency_)
    if last_price_ == '-':
        assert (supported_stock.last_price == buying_price_)
    else:
        assert (supported_stock.last_price == float(last_price_))
    assert (supported_stock.state == state_)
    if profit_margin_ == '-':
        assert (supported_stock.profit_margin == profit_margin_)
    else:
        assert (supported_stock.profit_margin == float(profit_margin_))
    if loss_limit_ == '-':
        assert (supported_stock.loss_limit == loss_limit_)
    else:
        assert (supported_stock.loss_limit == float(loss_limit_))


def custom_stock_test(custom_stock, id_, key_, buying_price_, volume_, country_, currency_, last_price_='-'):
    assert (custom_stock.id == id_)
    assert (custom_stock.key == key_)
    assert (custom_stock.buying_price == buying_price_)
    assert (custom_stock.volume == volume_)
    assert (custom_stock.country == country_)
    assert (custom_stock.currency == currency_)
    if last_price_ == '-':
        assert (custom_stock.last_price == buying_price_)
    else:
        assert (custom_stock.last_price == float(last_price_))


def spy_stock_test(spy_stock, user_id_, key_, country_, goal_, active_type_):
    assert (spy_stock.user_id == user_id_)
    assert (spy_stock.key == key_)
    assert (spy_stock.country == country_)
    assert (spy_stock.goal == goal_)
    assert (spy_stock.active_type == active_type_)


def User_tests():
    # Constructor tests
    user_test(user.User(1), 1)
    user_test(user.User(2, 0), 2, 0)
    user_test(user.User(3, 1, 1), 3, 1, 1)
    user_test(user.User(4, 0, 0, {'RUB': 100.0, 'USD': 10.0}), 4, 0, 0, {'RUB': 100.0, 'USD': 10.0})
    user_test(user.User(5, 1, 0, {'RUB': 120.0, 'USD': 30.0}, {'RUB': 0.0, 'USD': 1.0}), 5, 1, 0,
              {'RUB': 120.0, 'USD': 30.0}, {'RUB': 0.0, 'USD': 1.0})
    
    # Setter tests
    test_user = user.User(6, 0, 1)
    user_test(test_user, 6, 0, 1)
    test_user.set_alerts(1)
    test_user.set_subscription(0)
    user_test(test_user, 6, 1, 0)

    # Simple stock test
    test_user.add_new_sp_stock("SP_TEST")
    test_user.add_new_sp_stock("SP_TEST_2")
    assert (len(test_user.supported_stocks) == 2)
    test_user.add_new_stock("STOCK_TEST_1")
    test_user.add_new_stock("STOCK_TEST_2")
    assert (len(test_user.unsupported_stocks) == 2)
    test_user.delete_stock("STOCK_TEST_2")
    assert (len(test_user.unsupported_stocks) == 1)
    test_user.delete_stock("STOCK_TEST_1")
    assert (len(test_user.unsupported_stocks) == 0)
    test_user.delete_sp_stock("SP_TEST_2")
    test_user.delete_sp_stock("SP_TEST")
    assert (len(test_user.supported_stocks) == 0)

    # to_json test
    assert(test_user.encode_user() == {'id': '6',
                                       'alerts': '1',
                                       'subscription': '0',
                                       'purchases': {'RUB': 0.0, 'USD': 0.0},
                                       'sales': {'RUB': 0.0, 'USD': 0.0},
                                       'sp_stock_id': ['-'],
                                       'sp_stock_key': ['-'],
                                       'sp_stock_buying_price': ['-'],
                                       'sp_stock_volume': ['-'],
                                       'sp_stock_country': ['-'],
                                       'sp_stock_tracking': ['-'],
                                       'sp_stock_currency': ['-'],
                                       'sp_stock_last_price': ['-'],
                                       'sp_stock_state': ['-'],
                                       'sp_stock_profit_margin': ['-'],
                                       'sp_stock_loss_limit': ['-'],
                                       'stock_id': ['-'],
                                       'stock_key': ['-'],
                                       'stock_buying_price': ['-'],
                                       'stock_volume': ['-'],
                                       'stock_country': ['-'],
                                       'stock_last_price': ['-']})

    print("User tests - Passed!")


def Stocks_test():
    # Constructor test
    supported_stock_test(user.SupportedStock(1, "T", 123.2, "3", "Russia", 1, 1, 125, 120, 110), 1, "T", 123.2, 3,
                         "Russia", 1, 1, "125", "120", "110")
    # eq test
    sp_stock_1 = user.SupportedStock(1, "Key", 123, 1, "Russia", 1)
    sp_stock_2 = user.SupportedStock(1, "Key", 123, 1, "Russia", 1)
    assert (sp_stock_1.__eq__(sp_stock_2))
    sp_stock_2.id = 2
    assert (not sp_stock_1.__eq__(sp_stock_2))

    # Hash test
    assert (sp_stock_1.__hash__() != sp_stock_2.__hash__())
    sp_stock_2.id = 1
    assert (sp_stock_1.__hash__() == sp_stock_2.__hash__())

    print("SupportedStock tests - Passed!")

    # Constructor test
    custom_stock_test(user.CustomStock(1, "T", 123.2, 3, "Russia", 1, 123), 1, "T", 123.2, 3,
                         "Russia", 1, "123")
    # eq test
    cs_stock_1 = user.CustomStock(1, "Key", 123, 1, "Russia", 1)
    cs_stock_2 = user.CustomStock(1, "Key", 123, 1, "Russia", 1)
    assert (cs_stock_1.__eq__(cs_stock_2))
    cs_stock_2.id = 2
    assert (not cs_stock_1.__eq__(cs_stock_2))

    # Hash test
    assert (cs_stock_1.__hash__() != cs_stock_2.__hash__())
    cs_stock_2.id = 1
    assert (cs_stock_1.__hash__() == cs_stock_2.__hash__())

    print("CustomStock tests - Passed!")

    # Constructor test
    spy_stock_test(user.SpyStock(1, "T", "Russia", 125.0, "Stock"), 1, "T", "Russia", 125.0, "Stock")
    # eq test
    spy_stock_1 = user.SpyStock(1, "Key", "Russia", 123, "Stock")
    spy_stock_2 = user.SpyStock(1, "Key", "Russia", 123, "Stock")
    assert (spy_stock_1.__eq__(spy_stock_2))
    spy_stock_2.user_id = 2
    assert (not spy_stock_1.__eq__(spy_stock_2))

    # Hash test
    assert (spy_stock_1.__hash__() != spy_stock_2.__hash__())
    spy_stock_2.user_id = 1
    assert (spy_stock_1.__hash__() == spy_stock_2.__hash__())

    assert (spy_stock_1.encode_stock() == {'user_id': '1',
                                           'key': 'Key',
                                           'goal': '123.0',
                                           'country': 'Russia',
                                           'active_type': 'Stock'})
    print("SpyStock tests - Passed!")


def FireBase_tests():
    # Connection to bd needed
    return


def Server_tests():
    # Mock for VkApi needed
    return


User_tests()
Stocks_test()
FireBase_tests()
Server_tests()
