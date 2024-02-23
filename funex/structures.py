from typing import Any, Optional, Union
from pydantic import BaseModel, PositiveInt, PositiveFloat
from datetime import datetime
import os
from sortedcontainers import SortedList
from enum import Enum, auto


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


ID_GENERATOR = OrderIdGenerator()


class OrderStatus(Enum):
    CREATED = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    MODIFIED = auto()
    CANCELLED = auto()
    RESTORED = auto()
    EXPIRED = auto()

    @property
    def is_active(self):
        return self in {
            OrderStatus.CREATED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.MODIFIED,
            OrderStatus.RESTORED,
        }


class OrderType(Enum):
    ASK = "ask"
    BID = "bid"


class Order(BaseModel):
    id: PositiveInt
    order_type: OrderType
    price: PositiveFloat
    volume: PositiveInt
    owner_id: PositiveInt
    status: Optional[OrderStatus] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    listed: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.status is None:
            self.status = OrderStatus.CREATED
        now = datetime.now()
        if self.created is None:
            self.created = now
        if self.updated is None:
            self.updated = now

    def __setattr__(self, name: str, value: Any) -> None:
        if name != "updated":
            super().__setattr__("updated", datetime.now())
        return super().__setattr__(name, value)

    def __lt__(self, other: Union[int, float, "Order"]):
        if isinstance(other, (int, float)):
            return self.price < other
        if isinstance(other, Order):
            return self.price < other.price
        return NotImplemented

    def __gt__(self, other: Union[int, float, "Order"]):
        if isinstance(other, (int, float)):
            return self.price > other
        if isinstance(other, Order):
            return self.price > other.price
        return NotImplemented

    def __le__(self, other: Union[int, float, "Order"]):
        if isinstance(other, (int, float)):
            return self.price <= other
        if isinstance(other, Order):
            return self.price <= other.price
        return NotImplemented

    def __ge__(self, other: Union[int, float, "Order"]):
        if isinstance(other, (int, float)):
            return self.price >= other
        if isinstance(other, Order):
            return self.price >= other.price
        return NotImplemented


class OrderList:
    def __init__(self, order_list=None, order_type=None):
        self.__order_list = SortedList()
        self.__ids = {}
        self.otype = order_type
        if order_list:
            for order in order_list:
                self.add(order)

    def add(self, order, tolist=True):
        if not self.otype:
            self.otype = order.order_type
        if order.order_type != self.otype:
            raise ValueError("Order type must be the same as the list type")
        if tolist:
            self.__order_list.add(order)
        self.__ids[order.id] = order

    def bisect_left(self, order, right=True):
        cid = self.__order_list.bisect_left(order)
        if right:
            return self.__order_list[cid:]
        else:
            return self.__order_list[:cid]

    def bisect_right(self, order, left=True):
        cid = self.__order_list.bisect_right(order)
        if left:
            return self.__order_list[:cid]
        else:
            return self.__order_list[cid:]

    def relist(self, order=None, order_id=None):
        if not order and order_id is None:
            raise ValueError("Order or order_id must be provided")
        if order_id and order:
            print("Warning: both order and order_id are provided. Using order_id.")
        if order_id:
            pass
        elif order:
            order_id = order.id
        try:
            order = self.__ids[order_id]
        except KeyError:
            raise ValueError("Order with provided id not found")
        if order.status == OrderStatus.CANCELLED or order.status == OrderStatus.EXPIRED:
            order.listed = time.time()
            self.__order_list.add(order)
        else:
            raise ValueError("Order is active.")

    def remove(self, order=None, order_id=None):
        if not order and order_id is None:
            raise ValueError("Order or order_id must be provided")
        if order_id and order:
            print("Warning: both order and order_id are provided. Using order_id.")
        if order_id:
            pass
        elif order:
            order_id = order.id
        try:
            self.__order_list.remove(order)
        except ValueError:
            pass
        del self.__ids[order_id]

    def unlist(self, order=None, order_id=None, status=OrderStatus.EXPIRED):
        if not order and order_id is None:
            raise ValueError("Order or order_id must be provided")
        if order_id and order:
            print("Warning: both order and order_id are provided. Using order_id.")
        if order_id:
            pass
        elif order:
            order_id = order.id
        order = self.__ids[order_id]
        if (
            order.status == OrderStatus.CANCELLED
            or order.status == OrderStatus.EXPIRED
            or order.status == OrderStatus.FILLED
        ):
            raise ValueError("Order is not active.")
        else:
            order.status = status
            self.__order_list.remove(order)

    def clear(self):
        self.__order_list.clear()
        self.__ids.clear()

    def get(self, order_id):
        return self.__ids[order_id]

    def __getitem__(self, order_id):
        return self.__ids[order_id]

    def __iter__(self):
        return iter(self.__order_list)

    def __len__(self):
        return len(self.__order_list)

    def __repr__(self):
        return str(self.__order_list)
