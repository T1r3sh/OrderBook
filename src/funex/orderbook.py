from order_structs import OrderList, OrderStatus, Order, OrderIdGenerator
import time


class OrderBook:
    def __init__(self):

        self.ask = OrderList()
        self.bid = OrderList()
        self.order_sources = {"ask": self.ask, "bid": self.bid}
        self.tape = []

    def add(self, order):
        order.listed = time.time()
        self.order_sources[order.order_type].add(order, tolist=False)
        matched = self.match(order)
        self.fill(order, matched)

    def get_order(self, order_id, order_type=None):
        if order_type in self.order_sources:
            return self.order_sources[order_type].get(order_id)
        else:
            try:
                return self.ask.get(order_id)
            except ValueError:
                try:
                    return self.bid.get(order_id)
                except ValueError:
                    raise ValueError("Order not found")

    def cancel(self, order_id, order_type=None):
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

    def fill(self, order, counter_orders):
        if not counter_orders:
            print("Warning: No counter orders were provided.")
            self.order_sources[order.order_type].add(order)
            return
        source = self.order_sources[counter_orders[0].order_type]
        exit_flag = False
        for c_order in counter_orders:
            price = c_order.price
            volume = c_order.volume
            if c_order.volume >= order.volume:
                volume = order.volume
                c_order.volume -= order.volume
                # filling order is already unlisted so no need to unlist it again
                order.volume = 0
                order.status = OrderStatus.FILLED
                if c_order.volume == 0:
                    source.unlist(order_id=c_order.id, status=OrderStatus.FILLED)
                else:
                    c_order.status = OrderStatus.PARTIALLY_FILLED
                exit_flag = True
            else:
                order.volume -= c_order.volume
                source.unlist(order_id=c_order.id, status=OrderStatus.FILLED)
            self.tape.append(
                {
                    "order": order.id,
                    "contr_order": c_order.id,
                    "price": price,
                    "volume": volume,
                    "time": time.time(),
                }
            )
            if exit_flag:
                break
        if order.volume > 0:
            self.order_sources[order.order_type].add(order)

    def match(self, order):
        matched = []
        if order.order_type == "ask":
            matched = self.bid.bisect_left(order)
        else:
            matched = self.ask.bisect_right(order)
        matched.sort(key=lambda x: x.listed)
        return matched

    def proceede(self):
        order_tape = self.tape.copy()
        self.tape.clear()
        return order_tape

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
