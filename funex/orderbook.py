from datetime import datetime
from typing import List, Optional, Union

from structures import OrderList, OrderStatus, Order, OrderType


class OrderBook:
    """
    Represents a limit order book that stores and manages buy and sell orders.

    Attributes:
        ask (OrderList): The list of ask orders (sell orders).
        bid (OrderList): The list of bid orders (buy orders).
        order_sources (dict): A dictionary mapping order types to their respective order lists.
        tape (list): A list of filled orders with their details.

    Methods:
        add(order: Order) -> None: Adds a new order to the order book.
        match(order: Order) -> List[Order]: Matches an order with counter orders.
        fill(order: Order, counter_orders: List[Order]) -> None: Fills an order with counter orders.
        match_fill(order: Order) -> None: Matches and fills an order.
        get_order(order: Union[int, Order], order_type: OrderType) -> Optional[Order]: Retrieves an order from the order book.
        search_order(order: Union[Order, int], order_type: Optional[OrderType] = None): Searches for an order in the order book.
        cancel(order: Union[Order, int], order_type: Optional[OrderType] = None): Cancels an order.
        expire(order: Union[Order, int], order_type: Optional[OrderType] = None): Expires an order.
        restore(order: Union[Order, int], order_type: Optional[OrderType] = None): Restores a cancelled or expired order.
        remove_order(order: Union[Order, int], order_type: Optional[OrderType] = None): Removes an order from the order book.
        modify(order: Union[Order, int], order_type: Optional[OrderType] = None, price: Optional[float] = None, volume: Optional[float] = None): Modifies an order's price or volume.
        proceede() -> List[dict]: Retrieves the filled orders from the order book and clears the tape.

    """

    def __init__(self):

        self.ask = OrderList(order_type=OrderType.ASK)
        self.bid = OrderList(order_type=OrderType.BID)
        self.order_sources = {OrderType.ASK: self.ask, OrderType.BID: self.bid}
        self.tape = []

    def add(self, order_: Order) -> None:
        """
        Adds an order to the order book and matches/fills the order if possible.

        :param order_: The order to be added.
        :type order_: Order
        """
        order_.listed = datetime.now()
        self.order_sources[order_.order_type].add(order_)
        self.match_fill(order_)

    def match(self, order_: Order) -> List[Order]:
        """
        Matches the given order with the corresponding orders in the order book.

        :param order_: The order to be matched.
        :type order_: Order
        :return: A list of matched orders.
        :rtype: List[Order]
        """
        matched = []
        if order_.order_type == OrderType.ASK:
            matched = self.bid.bisect_left(order_)
        else:
            matched = self.ask.bisect_right(order_)
        matched.sort(key=lambda x: x.listed)
        return matched

    def fill(self, order_: Order, counter_orders: List[Order]) -> None:
        """
        Fills the given order with the counter orders.

        :param order_: The order to be filled.
        :type order_: Order
        :param counter_orders: The list of counter orders.
        :type counter_orders: List[Order]
        """
        if not counter_orders:
            return
        source = self.order_sources[order_.order_type]
        c_source = self.order_sources[counter_orders[0].order_type]
        for c_order in counter_orders:
            price_ = c_order.price
            volume_ = min(order_.volume, c_order.volume)
            source.fill(order_, volume_)
            c_source.fill(c_order, volume_)
            self.tape.append(
                {
                    "order": order_.id,
                    "contr_order": c_order.id,
                    "price": price_,
                    "volume": volume_,
                    "time": datetime.now(),
                }
            )
            if order_.status == OrderStatus.FILLED:
                break

    def match_fill(self, order: Order) -> None:
        """
        Matches the given order with existing orders in the order book and fills the order if there is a match.

        :param order: The order to be matched and filled.
        :type order: Order
        """
        matched = self.match(order)
        self.fill(order, matched)

    def get_order(
        self, order_: Union[int, Order], order_type_: OrderType
    ) -> Optional[Order]:
        """
        Get an order from the order book.

        :param order_: The order ID or the Order object.
        :type order_: Union[int, Order]
        :param order_type_: The type of the order.
        :type order_type_: OrderType
        :raises ValueError: If the order type is invalid.
        :raises ValueError: If the order is not found.
        :return: The order if found, otherwise None.
        :rtype: Optional[Order]
        """
        order_ = None
        if isinstance(order_, int):
            order_ = self.order_sources[order_type_].get(order_)
        elif isinstance(order_, Order):
            order_ = self.order_sources[order_.order_type].get(order_.id)
        else:
            raise ValueError("Invalid order type")
        if not order_:
            raise ValueError("Order not found")
        return order_

    def search_order(
        self,
        order_: Union[Order, int],
        order_type_: Optional[OrderType] = None,
    ) -> Optional[Order]:
        """
        Search for an order in the order book.

        :param order_: The order to search for. Can be an instance of `Order` or an integer representing the order ID.
        :type order_: Union[Order, int]
        :param order_type_: The type of order to search for. Defaults to None.
        :type order_type_: Optional[OrderType]
        :raises ValueError: If an invalid order type is provided.
        :raises ValueError: If the order is not found in any of the order sources.
        :return: The found order.
        :rtype: Order
        """
        if order_type_:
            return self.get_order(order_, order_type_)
        if isinstance(order_, Order):
            order_type_ = order_.order_type
            return self.get_order(order_, order_type_)
        if isinstance(order_, int):
            order_id = order_
        else:
            raise ValueError("Invalid order type")
        for source in self.order_sources.values():
            order_ = source.get(order_id)
            if order_:
                return order_
        raise ValueError("Order not found")

    def cancel(
        self, order_: Union[Order, int], order_type_: Optional[OrderType] = None
    ) -> None:
        """
        Cancels the specified order.

        :param order_: The order to be cancelled.
        :type order_: Union[Order, int]
        :param order_type_: The type of the order to be cancelled, defaults to None.
        :type order_type_: Optional[OrderType], optional
        :raises ValueError: If the order is already cancelled or expired.
        """
        order_ = self.search_order(order_, order_type_)
        if not order_.status.is_active:
            raise ValueError("Order is already cancelled or expired")
        source = self.order_sources[order_.order_type]
        source.cancel(order_)

    def expire(
        self, order_: Union[Order, int], order_type_: Optional[OrderType] = None
    ) -> None:
        """
        Expire the given order.

        :param order_: The order to expire.
        :type order_: Union[Order, int]
        :param order_type_: The type of the order to expire, defaults to None.
        :type order_type_: Optional[OrderType], optional
        :raises ValueError: If the order is already cancelled or expired.
        """
        order_ = self.search_order(order_, order_type_)
        if not order_.status.is_active:
            raise ValueError("Order is already cancelled or expired")
        source = self.order_sources[order_.order_type]
        source.expire(order_)

    def restore(
        self, order_: Union[Order, int], order_type_: Optional[OrderType] = None
    ) -> None:
        """
        Restores an order to the order book.

        :param order_: The order or order ID to be restored.
        :type order_: Union[Order, int]
        :param order_type_: The type of the order to be restored, defaults to None.
        :type order_type_: Optional[OrderType], optional
        :raises ValueError: If the order is already active.
        """

        order_ = self.search_order(order_, order_type_)
        if order_.status.is_active:
            raise ValueError("Order is already active")
        source = self.order_sources[order_.order_type]
        source.relist(order_)
        self.match_fill(order_)

    def remove_order(
        self, order_: Union[Order, int], order_type_: Optional[OrderType] = None
    ) -> None:
        """
        Remove an order from the order book.

        :param order_: The order to be removed. Can be an instance of `Order` or the order ID (int).
        :type order_: Union[Order, int]
        :param order_type_: The type of order to be removed. Defaults to None.
        :type order_type_: Optional[OrderType]
        """
        order_ = self.search_order(order_, order_type_)
        source = self.order_sources[order_.order_type]
        source.remove(order_)

    def modify(
        self,
        order_: Union[Order, int],
        order_type_: Optional[OrderType] = None,
        price_: Optional[float] = None,
        volume_: Optional[float] = None,
    ) -> None:
        """
        Modifies an existing order in the order book.

        :param order_: The order object or order ID to be modified.
        :type order_: Union[Order, int]
        :param order_type_: The new order type (buy/sell), defaults to None.
        :type order_type_: Optional[OrderType], optional
        :param price_: The new price of the order, defaults to None.
        :type price_: Optional[float], optional
        :param volume_: The new volume of the order, defaults to None.
        :type volume_: Optional[float], optional
        """
        order_ = self.search_order(order_, order_type_)
        source = self.order_sources[order_.order_type]
        source.modify(order_, price_, volume_)
        self.match_fill(order_)

    def proceede(self):

        tape = self.tape.copy()
        self.tape.clear()
        return tape


if __name__ == "__main__":
    order_book = OrderBook()
    import random
    from structures import OrderIdGenerator

    g_enj = OrderIdGenerator()
    next(g_enj)
    # Generate additional test data
    for _ in range(30):
        id_ = next(g_enj)
        order_type = random.choice([OrderType.ASK, OrderType.BID])
        price = random.randint(90, 110)
        volume = random.randint(5, 25)
        owner_id = random.randint(1, 10)
        # print(id_)
        order = Order(
            id=id_, order_type=order_type, price=price, volume=volume, owner_id=owner_id
        )
        order_book.add(order)
    import pprint

    pprint.pprint(order_book.tape)
    print("Number of bids:", len(order_book.bid))
    print("Number of asks:", len(order_book.ask))
    print("\n\n\n\n\n___________________\n asks:\n")
    for order in order_book.ask:
        pprint.pprint(order.dict())
    print("\n\n\n___________________\n bids:\n")
    for order in order_book.bid:
        pprint.pprint(order.dict())
