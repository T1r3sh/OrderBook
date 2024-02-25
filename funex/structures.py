import os
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional, Union, List
from pydantic import BaseModel, PositiveInt, PositiveFloat
from sortedcontainers import SortedList


class OrderIdGenerator:
    """
    A class that generates unique order IDs.

    Attributes:
        filepath (str): The file path to store the current state of the ID counter.
        id_counter (int): The current value of the ID counter.
        iterations_since_last_save (int): The number of iterations since the last state save.
        save_frequency (int): The frequency at which the state should be saved.

    Methods:
        __iter__(): Returns the iterator object itself.
        __next__(): Returns the next unique order ID.
        save_state(): Saves the current state of the ID counter to a file.
        load_state(): Loads the previous state of the ID counter from a file.
        reset_state(): Resets the ID counter to 0 and saves the state.
    """

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

    def save_state(self) -> None:
        """
        Saves the current state of the ID counter to a file.
        """
        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write(str(self.id_counter))

    def load_state(self) -> None:
        """
        Loads the previous state of the ID counter from a file.
        """
        if not os.path.exists(self.filepath):
            return 0
        with open(self.filepath, "r", encoding="utf-8") as f:
            saved_state = f.read()
            return int(saved_state)

    def reset_state(self) -> None:
        """
        Resets the state of the object by setting the id_counter to 0 and saving the state.
        """
        self.id_counter = 0
        self.save_state()


# ID_GENERATOR = OrderIdGenerator()


class OrderStatus(Enum):
    """
    Enum representing the status of an order.

    Attributes:
        CREATED: The order has been created.
        PARTIALLY_FILLED: The order has been partially filled.
        FILLED: The order has been completely filled.
        MODIFIED: The order has been modified.
        CANCELLED: The order has been cancelled.
        RESTORED: The order has been restored.
        EXPIRED: The order has expired.

    Methods:
        is_active(): Checks if the order status is active.

    """

    CREATED = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    MODIFIED = auto()
    CANCELLED = auto()
    RESTORED = auto()
    EXPIRED = auto()

    @property
    def is_active(self):
        """
        Checks if the order status is active.

        Returns:
            bool: True if the order status is active, False otherwise.
        """
        return self in {
            OrderStatus.CREATED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.MODIFIED,
            OrderStatus.RESTORED,
        }


class OrderType(Enum):
    """
    Enum representing the type of an order.

    Attributes:
        ASK (str): Represents an ask order.
        BID (str): Represents a bid order.
    """

    ASK = "ask"
    BID = "bid"


class Order(BaseModel):
    """
    Represents an order in the order book.

    :param id: The unique identifier of the order.
    :type id: int
    :param order_type: The type of the order (buy or sell).
    :type order_type: OrderType
    :param price: The price of the order.
    :type price: float
    :param volume: The volume of the order.
    :type volume: int
    :param owner_id: The ID of the owner of the order.
    :type owner_id: int
    :param status: The status of the order (optional).
    :type status: OrderStatus, optional
    :param created: The timestamp when the order was created (optional).
    :type created: datetime, optional
    :param updated: The timestamp when the order was last updated (optional).
    :type updated: datetime, optional
    :param listed: The timestamp when the order was listed (optional).
    :type listed: datetime, optional
    """

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

    def get(self, order_id: int) -> Optional[Order]:
        """
        Gets an order by its ID.

        :param order_id: The ID of the order to retrieve.
        :type order_id: int
        :return: The order with the specified ID, if found; otherwise, None.
        :rtype: Optional[Order]
        """
        return self.__ids.get(order_id)

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

    def unlist(self, order: Union[Order, int], order_status: OrderStatus) -> None:
        """
        Unlists the provided order by changing its status to the specified order_status.

        :param order: The order to be unlisted. It can be either an Order object or an integer representing the order ID.
        :type order: Union[Order, int]
        :param order_status: The status to which the order will be changed.
        :type order_status: OrderStatus
        :raises ValueError: If the provided order ID is not found.
        :raises ValueError: If the order type is invalid.
        :raises ValueError: If the order is not active.
        :raises ValueError: If the order_status is active.
        """
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")
        if not order.status.is_active:
            raise ValueError("Order is not active.")
        if order_status.is_active:
            raise ValueError("Order cannot be unlisted with active status.")
        self.__order_list.remove(order)
        order.status = order_status

    def relist(
        self, order: Union[Order, int], order_status: OrderStatus = OrderStatus.RESTORED
    ) -> None:
        """
        Relist an order with the specified order status.

        :param order: The order to relist. Can be either an instance of Order or an order ID.
        :type order: Union[Order, int]
        :param order_status: The status to set for the relisted order, defaults to OrderStatus.RESTORED
        :type order_status: OrderStatus, optional
        :raises ValueError: If the provided order ID is not found.
        :raises ValueError: If an invalid order type is provided.
        :raises ValueError: If an active order is given a non-active status.
        """

        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")
        if not order_status.is_active:
            raise ValueError("Active order cannot have non-active status")
        order.status = order_status
        order.listed = datetime.now()
        self.__order_list.add(order)

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
        """
        Expire an order.

        :param order: The order to expire. It can be either an Order object or an order ID.
        :type order: Union[Order, int]
        :raises ValueError: If the provided order ID is not found.
        :raises ValueError: If the order type is invalid.
        :raises ValueError: If the order is not active.
        """
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")
        if not order.status.is_active:
            raise ValueError("Order is not active.")
        self.__order_list.remove(order)
        order.status = OrderStatus.EXPIRED

    def cancel(self, order: Union[Order, int]) -> None:
        """
        Cancels an order.

        :param order: The order to be cancelled. It can be either an instance of the Order class or an integer representing the order ID.
        :type order: Union[Order, int]
        :raises ValueError: If the provided order ID is not found.
        :raises ValueError: If an invalid order type is provided.
        :raises ValueError: If the order is not active.
        """
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")
        if not order.status.is_active:
            raise ValueError("Order is not active.")
        self.__order_list.remove(order)
        order.status = OrderStatus.CANCELLED

    def fill(self, order: Union[Order, int], volume: int) -> None:
        """
        Fill the order with the specified volume.

        :param order: The order to be filled. It can be either an Order object or an order ID (int).
        :type order: Union[Order, int]
        :param volume: The volume to be filled.
        :type volume: int
        :raises ValueError: If the volume is not positive.
        :raises ValueError: If the provided order ID is not found.
        :raises ValueError: If the order type is invalid.
        :raises ValueError: If the order is not active.
        :raises ValueError: If the volume is greater than the order volume.
        """
        if volume <= 0:
            raise ValueError("Volume must be positive")
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")
        if not order.status.is_active:
            raise ValueError("Order is not active.")
        if volume > order.volume:
            raise ValueError("Volume is greater than order volume")
        order.volume -= volume
        if order.volume == 0:
            self.unlist(order, OrderStatus.FILLED)
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

    def modify(
        self,
        order: Union[Order, int],
        price: Optional[float] = None,
        volume: Optional[int] = None,
        relist: bool = True,
    ) -> None:
        """
        Modify an order by updating its price and/or volume.

        :param order: The order to modify. Can be an instance of Order or an order ID.
        :type order: Union[Order, int]
        :param price: The new price for the order, defaults to None.
        :type price: Optional[float], optional
        :param volume: The new volume for the order, defaults to None.
        :type volume: Optional[int], optional
        :param relist: Whether to relist the order after modification, defaults to True.
        :type relist: bool, optional
        :raises ValueError: If price or volume is not positive.
        :raises ValueError: If the provided order ID is not found.
        :raises ValueError: If the order type is invalid.
        """
        if any([price <= 0, volume <= 0]):
            raise ValueError("Price and volume must be positive")
        if isinstance(order, int):
            order = self.__ids.get(order)
            if order is None:
                raise ValueError("Provided order ID not found")
        elif not isinstance(order, Order):
            raise ValueError("Invalid order type")

        if relist:
            if order.status.is_active:
                self.__order_list.remove(order)
            else:
                print("Warning: Order is not active, it will not be relisted")
                relist = False
        order = self.__ids[order.id]
        if price is not None:
            order.price = price
        if volume is not None:
            order.volume = volume
        if relist:
            order.status = OrderStatus.MODIFIED
            self.__order_list.add(order)

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
