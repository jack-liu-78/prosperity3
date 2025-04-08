from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List, Any, Dict
import jsonpickle
import json


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


POSITION_LIMIT = 50

def get_position(state: TradingState, product: str) -> int:
    return state.position.get(product, 0)

def compute_imbalance(order_depth: OrderDepth) -> float:
    best_bid_vol = order_depth.buy_orders[max(order_depth.buy_orders)] if order_depth.buy_orders else 0
    best_ask_vol = order_depth.sell_orders[min(order_depth.sell_orders)] if order_depth.sell_orders else 0
    total_vol = best_bid_vol + best_ask_vol
    if total_vol == 0:
        return 0.0
    return (best_bid_vol - best_ask_vol) / total_vol

def get_best_prices(order_depth: OrderDepth):
    best_bid = max(order_depth.buy_orders) if order_depth.buy_orders else None
    best_ask = min(order_depth.sell_orders) if order_depth.sell_orders else None
    return best_bid, best_ask

def place_squid_orders(state: TradingState) -> List[Order]:
    product = "SQUID_INK"
    orders = []
    order_depth = state.order_depths[product]
    position = get_position(state, product)
    best_bid, best_ask = get_best_prices(order_depth)
    imbalance = compute_imbalance(order_depth)

    if best_bid is None or best_ask is None:
        return orders

    fair_price = (best_bid + best_ask) / 2
    spread = best_ask - best_bid

    IMBALANCE_THRESHOLD = 0.5
    ORDER_SIZE = 10

    if imbalance > IMBALANCE_THRESHOLD:
        if position + ORDER_SIZE <= POSITION_LIMIT:
            orders.append(Order(product, best_ask, ORDER_SIZE))
        if position + ORDER_SIZE <= POSITION_LIMIT:
            orders.append(Order(product, best_bid, ORDER_SIZE))

    elif imbalance < -IMBALANCE_THRESHOLD:
        if position - ORDER_SIZE >= -POSITION_LIMIT:
            orders.append(Order(product, best_bid, -ORDER_SIZE))
        if position - ORDER_SIZE >= -POSITION_LIMIT:
            orders.append(Order(product, best_ask, -ORDER_SIZE))

    else:
        if position + ORDER_SIZE <= POSITION_LIMIT:
            orders.append(Order(product, best_bid, ORDER_SIZE))
        if position - ORDER_SIZE >= -POSITION_LIMIT:
            orders.append(Order(product, best_ask, -ORDER_SIZE))

    return orders

def place_kelp_orders(state: TradingState) -> List[Order]:
    product = "KELP"
    orders = []
    order_depth = state.order_depths[product]
    position = get_position(state, product)
    best_bid, best_ask = get_best_prices(order_depth)
    imbalance = compute_imbalance(order_depth)

    if best_bid is None or best_ask is None:
        return orders

    fair_price = (best_bid + best_ask) / 2
    spread = best_ask - best_bid

    IMBALANCE_THRESHOLD = 0.5
    ORDER_SIZE = 10

    if imbalance > IMBALANCE_THRESHOLD:
        if position + ORDER_SIZE <= POSITION_LIMIT:
            orders.append(Order(product, best_ask, ORDER_SIZE))
        if position + ORDER_SIZE <= POSITION_LIMIT:
            orders.append(Order(product, best_bid, ORDER_SIZE))

    elif imbalance < -IMBALANCE_THRESHOLD:
        if position - ORDER_SIZE >= -POSITION_LIMIT:
            orders.append(Order(product, best_bid, -ORDER_SIZE))
        if position - ORDER_SIZE >= -POSITION_LIMIT:
            orders.append(Order(product, best_ask, -ORDER_SIZE))

    else:
        if position + ORDER_SIZE <= POSITION_LIMIT:
            orders.append(Order(product, best_bid, ORDER_SIZE))
        if position - ORDER_SIZE >= -POSITION_LIMIT:
            orders.append(Order(product, best_ask, -ORDER_SIZE))

    return orders

def place_resin_orders(state: TradingState) -> List[Order]:
    product = "RAINFOREST_RESIN"
    orders = []
    order_depth = state.order_depths[product]
    position = get_position(state, product)
    best_bid, best_ask = get_best_prices(order_depth)

    if best_bid is None or best_ask is None:
        return orders

    FAIR_VALUE = 10000
    ORDER_SIZE = 15

    if best_bid < FAIR_VALUE and position + ORDER_SIZE <= POSITION_LIMIT:
        orders.append(Order(product, best_bid, ORDER_SIZE))
    if best_ask > FAIR_VALUE and position - ORDER_SIZE >= -POSITION_LIMIT:
        orders.append(Order(product, best_ask, -ORDER_SIZE))

    return orders

class Trader:
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        traderObject = {}
        if state.traderData != None and state.traderData != "":
            traderObject = jsonpickle.decode(state.traderData)

        # if "SQUID_INK" in state.order_depths:
        #     result["SQUID_INK"] = place_squid_orders(state)
        # if "KELP" in state.order_depths:
        #     result["KELP"] = place_kelp_orders(state)
        if "RAINFOREST_RESIN" in state.order_depths:
            result["RAINFOREST_RESIN"] = place_resin_orders(state)

        conversions = 1
        traderData = jsonpickle.encode(traderObject)

        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
