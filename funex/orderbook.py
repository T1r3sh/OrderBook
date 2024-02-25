from datetime import datetime
from typing import List, Optional, Union

from structures import OrderList, OrderStatus, Order, OrderType, OrderIdGenerator


class OrderBook:

    def __init__(self):

        self.ask = OrderList()
        self.bid = OrderList()
        self.order_sources = {OrderType.ASK: self.ask, OrderType.BID: self.bid}
        self.tape = []

    def add(self, order: Order) -> None:
        order.listed = datetime.now()
        self.order_sources[order.order_type].add(order)
        matched = self.match(order)
        self.fill(order, matched)

    def fill(self, order: Order, counter_orders: List[Order]) -> None:
        if not counter_orders:
            print("Warning: No counter orders were provided.")
            self.order_sources[order.order_type].add(order)
            return
        source = self.order_sources[order.order_type]
        c_source = self.order_sources[counter_orders[0].order_type]
        for c_order in counter_orders:
            price = c_order.price
            volume = min(order.volume, c_order.volume)
            source.fill(order, volume)
            c_source.fill(c_order, volume)
            self.tape.append(
                {
                    "order": order.id,
                    "contr_order": c_order.id,
                    "price": price,
                    "volume": volume,
                    "time": datetime.now(),
                }
            )
            if order.status == OrderStatus.FILLED:
                break

    def search_order(
        self, order: Union[Order, int], order_type: Optional[OrderType] = None
    ):
        pass

    def get_order(
        self, order: Union[int, Order], order_type: OrderType
    ) -> Optional[Order]:
        order_ = None
        if isinstance(order, int):
            order_ = self.order_sources[order_type].get(order)
        elif isinstance(order, Order):
            order_ = self.order_sources[order.order_type].get(order.id)
        else:
            raise ValueError("Invalid order type")
        if not order_:
            raise ValueError("Order not found")
        return order_

    def cancel(self, order: Union[Order, int], order_type: OrderType = None):
        order = self.get_order(order_id, order_type)
        if not order:
            raise ValueError("Order not found")
        if order.status == OrderStatus.CANCELLED or order.status == OrderStatus.EXPIRED:
            raise ValueError("Order is already cancelled or expired")
        source = self.order_sources[order.order_type]
        source.unlist(order_id=order_id, status=OrderStatus.CANCELLED)

    def expire(self, order_id, order_type=None):
        order = self.get_order(order_id, order_type)
        if not order:
            raise ValueError("Order not found")
        if order.status == OrderStatus.CANCELLED or order.status == OrderStatus.EXPIRED:
            raise ValueError("Order is already cancelled or expired")
        source = self.order_sources[order.order_type]
        source.unlist(order_id=order_id, status=OrderStatus.EXPIRED)

    def restore(self, order_id, order_type=None):
        order = self.get_order(order_id, order_type)
        if not order:
            raise ValueError("Order not found")
        if (
            order.status != OrderStatus.CANCELLED
            and order.status != OrderStatus.EXPIRED
        ):
            raise ValueError("Order is not cancelled or expired")
        order.listed = time.time()
        order.status = OrderStatus.RESTORED
        matched = self.match(order)
        self.fill(order, matched)

    def remove_order(self, order_id, order_type=None):
        order = self.get_order(order_id, order_type)
        if not order:
            raise ValueError("Order not found")
        if not order_type:
            order_type = order.order_type
        source = self.order_sources[order_type]
        source.remove(order_id)

    def update(self, order_id, order_type=None, params=None):
        order = self.get_order(order_id, order_type)
        if not order:
            raise ValueError("Order not found")
        if order.status == OrderStatus.CANCELLED or order.status == OrderStatus.EXPIRED:
            raise ValueError("Order is cancelled or expired.")
        if not params:
            print("Warning: No params provided.")
            return
        for key, value in params.items():
            if key not in ("price", "volume"):
                raise ValueError("Order type cannot be modified")
            setattr(order, key, value)
        order.listed = time.time()
        matched = self.match(order)
        self.fill(order, matched)

    def match(self, order: Order) -> List[Order]:
        matched = []
        if order.order_type == "ask":
            matched = self.bid.bisect_left(order)
        else:
            matched = self.ask.bisect_right(order)
        matched.sort(key=lambda x: x.listed)
        return matched

    def proceede(self):
        tape = self.tape.copy()
        self.tape.clear()
        return tape

    def pop_old(self, dtime):
        # remove order that epired or cancelled more than dtime ago
        curr_time = time.time()
        counter = 0
        for order in self.ask:
            if (
                order.status == OrderStatus.CANCELLED
                or order.status == OrderStatus.EXPIRED
                or order.status == OrderStatus.FILLED
            ):
                if curr_time - order.updated > dtime:
                    self.ask.remove(order)
                    counter += 1
        for order in self.bid:
            if (
                order.status == OrderStatus.CANCELLED
                or order.status == OrderStatus.EXPIRED
                or order.status == OrderStatus.FILLED
            ):
                if curr_time - order.updated > dtime:
                    self.bid.remove(order)
                    counter += 1
        print("Removed ", counter, " orders")


if __name__ == "__main__":
    # Generate test data
    # bids = [
    #     Order(order_type="bid", price=100, volume=10, owner_id=1),
    #     Order(order_type="bid", price=99, volume=5, owner_id=2),
    #     Order(order_type="bid", price=98, volume=7, owner_id=2),
    # ]

    # asks = [
    #     Order(order_type="ask", price=101, volume=8, owner_id=3),
    #     Order(order_type="ask", price=102, volume=6, owner_id=4),
    #     Order(order_type="ask", price=103, volume=4, owner_id=3),
    # ]

    # # Add bids and asks to the order book
    order_book = OrderBook()
    # for bid in bids:
    #     order_book.add(bid)
    # for ask in asks:
    #     order_book.add(ask)

    # # Print statistics
    # print("Number of bids:", len(order_book.bid))
    # print("Number of asks:", len(order_book.ask))
    # print("Total bid volume:", sum(order.volume for order in order_book.bid))
    # print("Total ask volume:", sum(order.volume for order in order_book.ask))
    import random

    # Generate additional test data
    for _ in range(30):
        order_type = random.choice(["bid", "ask"])
        price = random.randint(90, 110)
        volume = random.randint(5, 25)
        owner_id = random.randint(1, 10)
        order = Order(
            order_type=order_type, price=price, volume=volume, owner_id=owner_id
        )
        order_book.add(order)
    import pprint

    pprint.pprint(order_book.tape)
    print("Number of bids:", len(order_book.bid))
    print("Number of asks:", len(order_book.ask))

    pprint.pprint(order_book.bid)
    print("___________")
    pprint.pprint(order_book.ask)
