import datetime
from typing import Callable, Optional

import orders


DEFAULT_BEGIN_TAG = "<<"
DEFAULT_END_TAG = ">>"


class Token:

    def __init__(self, name : str):
        self.name = name

    def get_label(self, 
                  begin_tag : Optional[str] = DEFAULT_BEGIN_TAG, 
                  end_tag : Optional[str] = DEFAULT_END_TAG) -> str:
        return begin_tag + self.name + end_tag
    
    def replace(self, data : str, 
                content : str,
                begin_tag : Optional[str] = DEFAULT_BEGIN_TAG, 
                end_tag : Optional[str] = DEFAULT_END_TAG) -> str:
        return data.replace( self.get_label(begin_tag, end_tag), content )


class General_Token(Token):

    def __init__(self, name : str, func : Callable[[Optional[str]], str]):
        super().__init__(name)
        self.func = func

    def replace_data(self, data : str, 
                input : str,
                begin_tag : Optional[str] = DEFAULT_BEGIN_TAG, 
                end_tag : Optional[str] = DEFAULT_END_TAG) -> str :
        if not input:
            self.replace(data, "", begin_tag, end_tag)
        return self.replace(data, self.func(input), begin_tag, end_tag)


class Time_Token(General_Token):

    def __init__(self, name : str):
        super().__init__(name, lambda s : datetime.datetime.now().strftime(s))


class Order_Token(Token):

    def __init__(self, name : str, func : Callable[[orders.Order], str]):
        super().__init__(name)
        self.func = func

    def replace_order(self, data : str, 
                order : Optional[orders.Order],
                begin_tag : Optional[str] = DEFAULT_BEGIN_TAG, 
                end_tag : Optional[str] = DEFAULT_END_TAG) -> str :
        if order is None:
            self.replace(data, "", begin_tag, end_tag)
        return self.replace(data, self.func(order), begin_tag, end_tag)


class Item_Token(Token):

    def __init__(self, name : str, func : Callable[[orders.Item], str]):
        super().__init__(name)
        self.func = func

    def replace_item(self, data : str, 
                item : Optional[orders.Item],
                begin_tag : Optional[str] = DEFAULT_BEGIN_TAG, 
                end_tag : Optional[str] = DEFAULT_END_TAG) -> str :
        if item is None:
            self.replace(data, "", begin_tag, end_tag)
        return self.replace(data, self.func(item), begin_tag, end_tag)


AMOUNT = Item_Token("AMOUNT", lambda i : str(i.amount))
CONSIGNS = Token("CONSIGNS")
CLIENT = Order_Token("CLIENT", lambda o : o.client)
DATE = Time_Token("DATE")
DELIVERY_POINT = Order_Token("DELIVERY_POINT", lambda o : o.delivery_point)
ITEMS = Token("ITEMS")
NAME = Item_Token("NAME", lambda i : i.name)
MODEL_FOLDER = Token("MODEL_FOLDER")
ORDER_DATE = Order_Token("ORDER_DATE", lambda o : o.date)
ORDER_ID = Order_Token("ORDER_ID", lambda o : o.order_id)
PRICE = Item_Token("PRICE", lambda i : str(i.price))
PROMOTION = Token("PROMOTION")
QTY = Item_Token("QTY", lambda i : str(i.qty))
TIME = Time_Token("TIME")
TODAY = Time_Token("TODAY")
TO_PAY = Order_Token("TO_PAY", lambda o : str(o.get_to_pay()))
TOTAL = Order_Token("TOTAL", lambda o : str(o.get_total_all())) 
TOTAL_CONSIGNS = Order_Token("TOTAL_CONSIGNS", lambda o : str(o.get_total_consigns()))
TOTAL_SALES = Order_Token("TOTAL_SALES", lambda o : str(o.get_total_price()))
