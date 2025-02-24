from typing import List, Optional


class Item:

    def __init__(self,
                 name: str,
                 qty: float,
                 price: float):

        self.name = name
        self.qty = qty
        self.price = price
        self.amount: float = qty * price


class Promotion:

    def __init__(self,
                 name: str,
                 percent: int):

        self.name = name
        self.percent = percent

    def __repr__(self):
        return "{}: {}%".format(self.name, self.percent)


class Order:

    def __init__(self):

        self.order_id: str = ""
        self.client: str = ""
        self.delivery_point: str = ""
        self.date: str = ""
        self.items: List[Item] = []
        self.consigns: List[Item] = []
        self.promotion: Optional[Promotion] = None

    def get_total_price(self) -> float:

        res: float = 0
        for item in self.items:
            res += item.amount
        return res

    def get_to_pay(self) -> float:

        res = self.get_total_price()
        if self.promotion is not None:
            return res * (100 - self.promotion.percent) / 100
        else:
            return res

    def get_total_consigns(self) -> float:

        res: float = 0
        for item in self.consigns:
            res += item.amount
        return res

    def get_total_all(self) -> float:

        return self.get_to_pay() + self.get_total_consigns()
