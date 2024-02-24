from typing import Any, Optional, Union, List
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
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(str(self.id_counter))

    def load_state(self):
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath, "r", encoding="utf-8") as f:
            saved_state = f.read()
            return int(saved_state)

    def reset_state(self):
        self.id_counter = 0
        self.save_state()


# ID_GENERATOR = OrderIdGenerator()


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
        # logging here
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
        # logging here
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
    """
    Order List is a collection of orders. It is used to store and manage orders.
    Active orders are stored in a sorted list with search complexity of O(log n) and insertion complexity of O(n).
    All orders are indexed by their id for O(1) access.
    Active orders can be reached through bisect operations.
    """

    def __init__(
        self,
        order_type: OrderType,
        order_list: Optional[List[Order]] = None,
    ) -> None:
        """
        Initializes a collection of orders of a specified type. All orders within the collection must share the same order type.

        :param order_type: The type of orders to be stored in the list, e.g., 'ask' or 'bid'. The specific types are defined in the OrderType enum.
        :type order_type: OrderType
        :param order_list: Initial list of orders to be added to the collection, defaults to None. Each order in the list is added to the collection using the 'add' method logic.
        :type order_list: Optional[List[Order]], optional
        """
        self.__order_list = SortedList()
        self.__ids = {}
        self.otype = order_type
        if order_list:
            for order in order_list:
                self.add(order)

    def add(self, order: Order, tolist: Union[bool, str] = "auto") -> None:
        """
        Adds an order to the collection. The order is only added to the sorted list if it meets the criteria defined by the 'tolist' parameter. By default ('auto'), active orders are added to the sorted list.

        :param order: The order to be added to the collection.
        :type order: Order
        :param tolist: Specifies how the order should be added to the list. 'auto' adds active orders automatically; True or 'y'/'yes' always adds; False or 'n'/'no' never adds. Defaults to 'auto'.
        :type tolist: Union[bool, str], optional
        :raises ValueError: If the order's type does not match the collection's type.
        :raises ValueError: If 'tolist' is given an invalid value.
        """
        if order.order_type != self.otype:
            raise ValueError("Order type must be the same as the list type")
        if tolist == "auto":
            if order.status.is_active:
                if order.listed is None:
                    order.listed = datetime.now()
                self.__order_list.add(order)
        elif tolist is True or tolist in ["y", "yes"]:
            self.__order_list.add(order)
        elif tolist is False or tolist in ["n", "no"]:
            pass
        else:
            raise ValueError("Invalid value for tolist")
        self.__ids[order.id] = order

    def bisect_left(
        self, order: Union[Order, float], include_right: bool = True
    ) -> List[Order]:
        """
        Performs a bisect left operation on the sorted list to find the position to insert 'order' or 'price'.
        Returns a segment of the list based on the bisect position.

        :param order: Either an Order object or a float price value to perform the bisect operation.
        :type order: Union[Order, float]
        :param include_right: If True, returns the segment of the list from the bisect position to the end (inclusive of the position).
                              If False, returns the segment up to the bisect position (exclusive).
                              Defaults to True.
        :type include_right: bool, optional
        :return: A list of Orders filtered based on the bisect operation.
        :rtype: List[Order]
        """
        cid = self.__order_list.bisect_left(order)
        if include_right:
            return self.__order_list[cid:]
        return self.__order_list[:cid]

    def bisect_right(
        self, order: Union[Order, float], include_left: bool = True
    ) -> List[Order]:
        """
        Performs a bisect right operation on the sorted list to find the position to insert 'order' or 'price'.
        Returns a segment of the list based on the bisect position.

        :param order: Either an Order object or a float price value to perform the bisect operation.
        :type order: Union[Order, float]
        :param include_left: If True, returns the segment of the list up to the bisect position (inclusive).
                             If False, returns the segment of the list from the bisect position to the end (exclusive).
                             Defaults to True.
        :type include_left: bool, optional
        :return: A list of Orders filtered based on the bisect operation.
        :rtype: List[Order]
        """
        cid = self.__order_list.bisect_right(order)
        if include_left:
            return self.__order_list[:cid]
        return self.__order_list[cid:]

    def modify(
        self,
        order: Union[Order, int],
        price: Optional[float] = None,
        volume: Optional[int] = None,
        order_status: Optional[OrderStatus] = None,
        force_relist: bool = False,
    ) -> None:
        """
        Modify an order based on provided parameters. Updates the order's price, volume, and/or status.
        Conditions for relisting in the sorted list:
        - If the order's status changes from active to non-active, it's removed.
        - If the order's status changes from non-active to active, it's added.
        - If the price changes and the order is active, it's re-added to update its position.
        - Force relist if specified, regardless of other changes, but only if the order remains or becomes active.

        :param order: The order or order ID to be modified.
        :param price: The new price of the order, defaults to None.
        :param volume: The new volume of the order, defaults to None.
        :param order_status: The new status of the order, defaults to None.
        :param force_relist: Forces the order to be re-added to the list, defaults to False.
        :raises ValueError: If the order or order ID is invalid or not found.
        """
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")

        needs_relist = False

        if volume is not None:
            order.volume = volume

        if order_status is not None and order_status != order.status:
            pre_status = order.status
            order.status = order_status

            if not order.status.is_active:
                if pre_status.is_active:
                    self.__order_list.remove(order)
            else:  # status is active
                needs_relist = True

        # Handle price change
        if price is not None and price != order.price:
            order.price = price
            if order.status.is_active:
                needs_relist = True

        # Relist if necessary
        if (needs_relist or force_relist) and order.status.is_active:
            # Ensure order is not already in the list due to prior operations
            if order in self.__order_list:
                self.__order_list.remove(order)
            order.listed = datetime.now()
            self.__order_list.add(order)

    def relist(self, order: Union[Order, int]) -> None:
        """
        Relist an order that is not active.

        :param order: order to be relisted, it can be either an order or an order id
        :type order: Union[Order, int]
        :raises ValueError: if provided order is invalid type
        :raises ValueError: if order is not found
        :raises ValueError: if order is active
        """
        try:
            self.modify(order, order_status=OrderStatus.RESTORED)
        except ValueError as e:
            raise ValueError("Provided order not found") from e

    def remove(self, order: Union[Order, int]) -> None:
        """
        Remove an order from the collection.

        :param order: order to be removed, it can be either an order or an order id
        :type order: Union[Order, int]
        :raises ValueError: if provided order is invalid type
        :raises ValueError: if order is not found
        """
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")

        if order.status.is_active:
            self.__order_list.remove(order)
        del self.__ids[order.id]

    def expire(self, order: Union[Order, int]) -> None:
        try:
            self.modify(order, order_status=OrderStatus.EXPIRED)
        except ValueError as e:
            raise ValueError("Provided order not found") from e

    def cancel(self, order: Union[Order, int]) -> None:
        try:
            self.modify(order, order_status=OrderStatus.CANCELLED)
        except ValueError as e:
            raise ValueError("Provided order not found") from e

    def fill(self, order: Union[Order, int]) -> None:
        try:
            self.modify(order, order_status=OrderStatus.FILLED)
        except ValueError as e:
            raise ValueError("Provided order not found") from e

    # def unlist(self, order: Union[Order, int], status=OrderStatus.EXPIRED) -> None:
    #     """
    #     Unlist an active order.

    #     :param order: order to be unlisted, it can be either an order or an order id
    #     :type order: Union[Order, int]
    #     :param status: status to change, defaults to OrderStatus.EXPIRED
    #     :type status: _type_, optional
    #     :raises ValueError: _description_
    #     :raises ValueError: _description_
    #     :raises ValueError: _description_
    #     """
    #     if isinstance(order, int):
    #         order_id = order
    #     elif isinstance(order, Order):
    #         order_id = order.id
    #     else:
    #         raise ValueError("Invalid order")
    #     try:
    #         order = self.__ids[order_id]
    #     except KeyError as e:
    #         raise ValueError("Provided order not found") from e
    #     if not order.status.is_active:
    #         raise ValueError("Order is not active.")
    #     else:
    #         order.status = status
    #         self.__order_list.remove(order)

    def clear(self) -> None:
        """
        Clears the collection of all orders.
        """
        self.__order_list.clear()
        self.__ids.clear()

    def __getitem__(self, order_id):
        return self.__ids[order_id]

    def __iter__(self):
        return iter(self.__order_list)

    def __len__(self):
        return len(self.__ids)

    def __repr__(self):
        return str(self.__order_list)
