import os
import time

from dataclasses import dataclass, field
from enum import Enum, auto
from SortedContainers import SortedList


class OrderStatus(Enum):
    CREATED = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()


class OrderIdGenerator:
    def __init__(self):
        self.filepath = os.path.join(os.getcwd(), "current_state.txt")
        self.id_counter = self.load_state()
        self.iterations_since_last_save = 0
        self.save_frequency = 100

    def __iter__(self):
        return self

    def __next__(self):
        current_id = self.id_counter
        self.id_counter += 1
        self.iterations_since_last_save += 1
        if self.iterations_since_last_save >= self.save_frequency:
            self.save_state()
            self.iterations_since_last_save = 0

        return current_id

    def save_state(self):
        with open(self.filepath, "w") as f:
            f.write(str(self.id_counter))

    def load_state(self):
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath, "r") as f:
            saved_state = f.read()
            return int(saved_state)

    def reset_state(self):
        self.id_counter = 0
        self.save_state()


@dataclass
class Order:
    order_type: str = field(compare=False)
    security_name: str = field(compare=False)
    price: float = field(compare=True)
    volume: int = field(compare=False)
    owner_id: int = field(compare=False)
    status: int = field(compare=False, default=OrderStatus.CREATED)
    id: int = field(compare=False, default_factory=g_obj.__next__)
    time_created: float = field(compare=False, default_factory=time.time)
    last_update: float = field(compare=False, default_factory=time.time)

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return self.price == other
        if isinstance(other, Order):
            return self.price == other.price
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, (int, float)):
            return self.price < other
        if isinstance(other, Order):
            return self.price < other.price
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, (int, float)):
            return self.price > other
        if isinstance(other, Order):
            return self.price > other.price
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, float)):
            return self.price <= other
        if isinstance(other, Order):
            return self.price <= other.price
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, float)):
            return self.price >= other
        if isinstance(other, Order):
            return self.price >= other.price
        return NotImplemented

    def __repr__(self):
        return (
            f"Order № {self.id} \n"
            f"Order Type {self.order_type} \n"
            f"Security: {self.security_name} \n"
            f"Price: {self.price} \n"
            f"Volume: {self.volume} \n"
            f"Owner: {self.owner_id} \n"
            f"Status: {self.status} \n"
            f"Created: {self.time_created} \n"
            f"Last update: {self.last_update} \n"
        )

    def __post_init__(self):
        if self.volume <= 0:
            raise ValueError("Volume must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.order_type not in ["ask", "bid"]:
            raise ValueError("Order type must be 'ask' or 'bid'")
        if self.status not in OrderStatus:
            raise ValueError("Invalid order status")

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key != "last_update":  # Избегаем рекурсивного вызова
            super().__setattr__("last_update", time.time())

    def json(self):
        return {
            "order_type": self.order_type,
            "security_name": self.security_name,
            "price": self.price,
            "volume": self.volume,
            "owner_id": self.owner_id,
            "status": self.status,
            "id": self.id,
            "time_created": self.time_created,
            "last_update": self.last_update,
        }


class OrderList:
    def __init__(self, order_list=None):
        self.__order_list = SortedList()
        self.__ids = {}
        if order_list:
            for order in order_list:
                self.add(order)

    def add(self, order):
        self.__order_list.add(order)
        self.__ids[order.id] = order

    def bisect_left(self, order):
        return self.__order_list.bisect_left(order)

    def bisect_right(self, order):
        return self.__order_list.bisect_right(order)

    def pop(self, index=-1):
        order = self.__order_list.pop(index)
        del self.__ids[order.id]
        return order

    def pop_by_id(self, order_id):
        order = self.__ids[order_id]
        self.remove(order)
        return order

    def remove(self, order):
        self.__order_list.remove(order)
        del self.__ids[order.id]

    def clear(self):
        self.__order_list.clear()
        self.__ids.clear()

    def get(self, order_id):
        return self.__ids.get(order_id)

    def __getitem__(self, index):
        return self.__order_list[index]

    def __delitem__(self, index):
        del self.__order_list[index]

    def __len__(self):
        return len(self.__order_list)

    def __repr__(self):
        return str(self.__order_list)


class OrderBook:
    def __init__(self):
        self.ask = OrderList()

        self.bid = OrderList()
        self.tape = []

    def add(self, order):
        matched = []
        if order.order_type == "ask":
            matched = self.bid.bisect_left(order)
        else:
            matched = self.ask.bisect_right(order)
        matched.sort(key=lambda x: x.modified)
        while order.volume > 0 and matched:
            current = matched.pop(0)
            deal_price = current.price
            self.fill(order, current, deal_price)
        if order.volume > 0:
            if order.order_type == "ask":
                self.ask.add(order)
            elif order.order_type == "bid":
                self.bid.add(order)
            else:
                raise ValueError("Order type must be 'ask' or 'bid'")

    def fill(self, order, matched_order, price):
        volume = 0
        if matched_order.volume >= order.volume:
            matched_order.volume -= order.volume
            volume = order.volume
            order.volume = 0
            order.status = OrderStatus.FILLED
            if matched_order.volume == 0:
                self.remove_order(matched_order)
            else:
                self.get_order(matched_order).volume = matched_order.volume
        else:
            order.volume -= matched_order.volume
            self.remove_order(matched_order)
            volume = matched_order.volume
        self.tape.append(
            {
                "order": order.id,
                "contr_order": matched_order.id,
                "price": price,
                "volume": volume,
                "time": time.time(),
            }
        )

    def find_by_id(self, order_id):
        if order_id in self.ask:
            return self.ask[order_id]
        elif order_id in self.bid:
            return self.bid[order_id]
        else:
            raise ValueError("Order with such id doesn't exist")

    def get_order(self, order):
        if order.order_type == "ask":
            return self.ask[order.id]
        elif order.order_type == "bid":
            return self.bid[order.id]
        else:
            raise ValueError("Order type must be 'ask' or 'bid'")

    def remove_order(self, order):
        if order.order_type == "ask":
            self.ask.remove(order)
        elif order.order_type == "bid":
            self.bid.remove(order)
        else:
            raise ValueError("Order type must be 'ask' or 'bid'")

    def cancel(self, order):
        self.get_order(order).status = OrderStatus.CANCELLED
        self.remove_order(order)

    def modify(self, order, price):
        self.get_order(order).price = price

    def proceede(self):
        order_tape = self.order_tape.copy()
        self.order_tape.clear()
        return order_tape
