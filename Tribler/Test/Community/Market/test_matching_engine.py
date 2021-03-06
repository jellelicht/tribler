from twisted.internet.defer import inlineCallbacks

from Tribler.Test.test_as_server import AbstractServer
from Tribler.community.market.core.matching_engine import MatchingEngine, PriceTimeStrategy
from Tribler.community.market.core.message import TraderId, MessageNumber, MessageId
from Tribler.community.market.core.message_repository import MemoryMessageRepository
from Tribler.community.market.core.order import Order, OrderId, OrderNumber
from Tribler.community.market.core.orderbook import OrderBook
from Tribler.community.market.core.price import Price
from Tribler.community.market.core.quantity import Quantity
from Tribler.community.market.core.tick import Ask, Bid
from Tribler.community.market.core.timeout import Timeout
from Tribler.community.market.core.timestamp import Timestamp
from Tribler.dispersy.util import blocking_call_on_reactor_thread


class PriceTimeStrategyTestSuite(AbstractServer):
    """Price time strategy test cases."""

    @blocking_call_on_reactor_thread
    @inlineCallbacks
    def setUp(self, annotate=True):
        yield super(PriceTimeStrategyTestSuite, self).setUp(annotate=annotate)
        # Object creation
        self.ask = Ask(MessageId(TraderId('0'), MessageNumber('1')), OrderId(TraderId('0'), OrderNumber(1)),
                       Price(100, 'BTC'), Quantity(30, 'MC'), Timeout(100), Timestamp.now())
        self.ask2 = Ask(MessageId(TraderId('1'), MessageNumber('1')), OrderId(TraderId('1'), OrderNumber(2)),
                        Price(100, 'BTC'), Quantity(30, 'MC'), Timeout(100), Timestamp.now())
        self.ask3 = Ask(MessageId(TraderId('3'), MessageNumber('1')), OrderId(TraderId('0'), OrderNumber(3)),
                        Price(200, 'BTC'), Quantity(200, 'MC'), Timeout(100), Timestamp.now())
        self.ask4 = Ask(MessageId(TraderId('4'), MessageNumber('1')), OrderId(TraderId('1'), OrderNumber(4)),
                        Price(50, 'BTC'), Quantity(200, 'MC'), Timeout(100), Timestamp.now())
        self.ask5 = Ask(MessageId(TraderId('4'), MessageNumber('1')), OrderId(TraderId('1'), OrderNumber(4)),
                        Price(100, 'A'), Quantity(30, 'MC'), Timeout(100), Timestamp.now())
        self.ask6 = Ask(MessageId(TraderId('4'), MessageNumber('1')), OrderId(TraderId('1'), OrderNumber(4)),
                        Price(100, 'BTC'), Quantity(30, 'A'), Timeout(100), Timestamp.now())

        self.bid = Bid(MessageId(TraderId('5'), MessageNumber('2')), OrderId(TraderId('0'), OrderNumber(5)),
                       Price(100, 'BTC'), Quantity(30, 'MC'), Timeout(100), Timestamp.now())
        self.bid2 = Bid(MessageId(TraderId('6'), MessageNumber('2')), OrderId(TraderId('0'), OrderNumber(6)),
                        Price(200, 'BTC'), Quantity(30, 'MC'), Timeout(100), Timestamp.now())
        self.bid3 = Bid(MessageId(TraderId('7'), MessageNumber('2')), OrderId(TraderId('0'), OrderNumber(7)),
                        Price(50, 'BTC'), Quantity(200, 'MC'), Timeout(100), Timestamp.now())
        self.bid4 = Bid(MessageId(TraderId('8'), MessageNumber('2')), OrderId(TraderId('0'), OrderNumber(8)),
                        Price(100, 'BTC'), Quantity(200, 'MC'), Timeout(100), Timestamp.now())

        self.ask_order = Order(OrderId(TraderId('9'), OrderNumber(11)), Price(100, 'BTC'), Quantity(30, 'MC'),
                               Timeout(100), Timestamp.now(), True)
        self.ask_order2 = Order(OrderId(TraderId('9'), OrderNumber(12)), Price(10, 'BTC'), Quantity(60, 'MC'),
                                Timeout(100), Timestamp.now(), True)

        self.bid_order = Order(OrderId(TraderId('9'), OrderNumber(13)), Price(100, 'BTC'), Quantity(30, 'MC'),
                               Timeout(100), Timestamp.now(), False)
        self.bid_order2 = Order(OrderId(TraderId('9'), OrderNumber(14)), Price(100, 'BTC'), Quantity(60, 'MC'),
                                Timeout(100), Timestamp.now(), False)
        self.order_book = OrderBook(MemoryMessageRepository('0'))
        self.price_time_strategy = PriceTimeStrategy(self.order_book)

    @blocking_call_on_reactor_thread
    @inlineCallbacks
    def tearDown(self, annotate=True):
        self.order_book.cancel_all_pending_tasks()
        yield super(PriceTimeStrategyTestSuite, self).tearDown(annotate=annotate)

    def test_empty_match_order(self):
        # Test for match order with an empty order book
        self.assertEquals([], self.price_time_strategy.match_order(self.bid_order))
        self.assertEquals([], self.price_time_strategy.match_order(self.ask_order))

    def test_match_order_other_price(self):
        """
        Test whether two ticks with different price types are not matched
        """
        self.order_book.insert_ask(self.ask5)
        self.assertEqual([], self.price_time_strategy.match_order(self.bid_order))

    def test_match_order_other_quantity(self):
        """
        Test whether two ticks with different quantity types are not matched
        """
        self.order_book.insert_ask(self.ask6)
        self.assertEqual([], self.price_time_strategy.match_order(self.bid_order))

    def test_match_order_ask(self):
        # Test for match order
        self.order_book.insert_bid(self.bid)
        proposed_trades = self.price_time_strategy.match_order(self.ask_order)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Price(100, 'BTC'), proposed_trades[0].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[0].quantity)

    def test_match_order_bid(self):
        # Test for match order
        self.order_book.insert_ask(self.ask)
        proposed_trades = self.price_time_strategy.match_order(self.bid_order)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Price(100, 'BTC'), proposed_trades[0].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[0].quantity)

    def test_match_order_divided(self):
        # Test for match order divided over two ticks
        self.order_book.insert_ask(self.ask)
        self.order_book.insert_ask(self.ask2)
        proposed_trades = self.price_time_strategy.match_order(self.bid_order2)
        self.assertEquals(2, len(proposed_trades))
        self.assertEquals(Price(100, 'BTC'), proposed_trades[0].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[0].quantity)
        self.assertEquals(Price(100, 'BTC'), proposed_trades[1].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[1].quantity)

    def test_match_order_partial_ask(self):
        """
        Test partial matching of a bid order with the matching engine
        """
        self.ask._quantity = Quantity(20, 'MC')
        self.order_book.insert_ask(self.ask)
        proposed_trades = self.price_time_strategy.match_order(self.bid_order2)
        self.assertEquals(1, len(proposed_trades))

    def test_match_order_partial_bid(self):
        """
        Test partial matching of an ask order with the matching engine
        """
        self.bid._quantity = Quantity(20, 'MC')
        self.order_book.insert_bid(self.bid)
        proposed_trades = self.price_time_strategy.match_order(self.ask_order2)
        self.assertEquals(1, len(proposed_trades))

    def test_match_order_different_price_level(self):
        # Test for match order given an ask order and bid in different price levels
        self.order_book.insert_bid(self.bid2)
        proposed_trades = self.price_time_strategy.match_order(self.ask_order)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Price(200, 'BTC'), proposed_trades[0].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[0].quantity)

    def test_search_for_quantity_in_order_book_partial_ask_low(self):
        # Test for protected search for quantity in order book partial ask when price is too low
        self.order_book.insert_bid(self.bid)
        self.order_book.insert_bid(self.bid2)
        self.order_book.insert_bid(self.bid3)
        self.order_book.insert_bid(self.bid4)
        quantity_to_trade, proposed_trades = self.price_time_strategy._search_for_quantity_in_order_book_partial_ask(
            Price(100, 'BTC'), Quantity(30, 'MC'), [],
            self.ask_order2)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Quantity(0, 'MC'), quantity_to_trade)

    def test_search_for_quantity_in_order_book_partial_ask(self):
        # Test for protected search for quantity in order book partial ask
        self.order_book.insert_bid(self.bid)
        self.order_book.insert_bid(self.bid2)
        self.order_book.insert_bid(self.bid3)
        self.order_book.insert_bid(self.bid4)
        quantity_to_trade, proposed_trades = self.price_time_strategy._search_for_quantity_in_order_book_partial_ask(
            Price(100, 'BTC'), Quantity(30, 'MC'), [],
            self.ask_order)
        self.assertEquals(0, len(proposed_trades))
        self.assertEquals(Quantity(30, 'MC'), quantity_to_trade)

    def test_search_for_quantity_in_order_book_partial_bid_high(self):
        # Test for protected search for quantity in order book partial bid when price is too high
        self.order_book.insert_ask(self.ask)
        self.order_book.insert_ask(self.ask2)
        self.order_book.insert_ask(self.ask3)
        self.order_book.insert_ask(self.ask4)
        quantity_to_trade, proposed_trades = self.price_time_strategy._search_for_quantity_in_order_book_partial_bid(
            Price(100, 'BTC'), Quantity(30, 'MC'), [],
            self.bid_order)
        self.assertEquals(0, len(proposed_trades))
        self.assertEquals(Quantity(30, 'MC'), quantity_to_trade)

    def test_search_for_quantity_in_order_book_partial_bid(self):
        # Test for protected search for quantity in order book partial bid
        self.order_book.insert_ask(self.ask)
        self.order_book.insert_ask(self.ask2)
        self.order_book.insert_ask(self.ask3)
        self.order_book.insert_ask(self.ask4)
        quantity_to_trade, proposed_trades = self.price_time_strategy._search_for_quantity_in_order_book_partial_bid(
            Price(50, 'BTC'), Quantity(30, 'MC'), [],
            self.bid_order)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Quantity(0, 'MC'), quantity_to_trade)

    def test_search_for_quantity_in_price_level(self):
        """
        Test searching within a price level
        """
        self.bid_order._order_id = self.ask.order_id
        self.order_book.insert_ask(self.ask)
        self.order_book.insert_ask(self.ask2)
        _, trades = self.price_time_strategy._search_for_quantity_in_price_level(
            None, Quantity(10, 'MC'), self.bid_order)
        self.assertFalse(trades)

        _, trades = self.price_time_strategy._search_for_quantity_in_price_level(
            self.order_book.get_tick(self.bid_order.order_id), Quantity(10, 'MC'), self.bid_order)
        self.assertFalse(trades)

        self.bid_order2.reserve_quantity_for_tick(self.ask2.order_id, Quantity(60, 'MC'))
        _, trades = self.price_time_strategy._search_for_quantity_in_price_level(
            self.order_book.get_tick(self.ask2.order_id), Quantity(10, 'MC'), self.bid_order2)
        self.assertFalse(trades)


class MatchingEngineTestSuite(AbstractServer):
    """Matching engine test cases."""

    @blocking_call_on_reactor_thread
    @inlineCallbacks
    def setUp(self, annotate=True):
        yield super(MatchingEngineTestSuite, self).setUp(annotate=annotate)
        # Object creation
        self.ask = Ask(MessageId(TraderId('1'), MessageNumber('message_number1')),
                       OrderId(TraderId('2'), OrderNumber(1)), Price(100, 'BTC'), Quantity(30, 'MC'),
                       Timeout(30), Timestamp.now())
        self.bid = Bid(MessageId(TraderId('3'), MessageNumber('message_number2')),
                       OrderId(TraderId('4'), OrderNumber(2)), Price(100, 'BTC'), Quantity(30, 'MC'),
                       Timeout(30), Timestamp.now())
        self.ask_order = Order(OrderId(TraderId('5'), OrderNumber(3)), Price(100, 'BTC'), Quantity(30, 'MC'),
                               Timeout(30), Timestamp.now(), True)
        self.bid_order = Order(OrderId(TraderId('6'), OrderNumber(4)), Price(100, 'BTC'), Quantity(30, 'MC'),
                               Timeout(30), Timestamp.now(), False)
        self.order_book = OrderBook(MemoryMessageRepository('0'))
        self.matching_engine = MatchingEngine(PriceTimeStrategy(self.order_book))

    @blocking_call_on_reactor_thread
    @inlineCallbacks
    def tearDown(self, annotate=True):
        self.order_book.cancel_all_pending_tasks()
        yield super(MatchingEngineTestSuite, self).tearDown(annotate=annotate)

    def test_empty_match_order_empty(self):
        # Test for match order with an empty order book
        self.assertEquals([], self.matching_engine.match_order(self.bid_order))
        self.assertEquals([], self.matching_engine.match_order(self.ask_order))

    def test_match_order_bid(self):
        # Test for match bid order
        self.order_book.insert_ask(self.ask)
        proposed_trades = self.matching_engine.match_order(self.bid_order)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Price(100, 'BTC'), proposed_trades[0].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[0].quantity)

    def test_match_order_ask(self):
        # Test for match ask order
        self.order_book.insert_bid(self.bid)
        proposed_trades = self.matching_engine.match_order(self.ask_order)
        self.assertEquals(1, len(proposed_trades))
        self.assertEquals(Price(100, 'BTC'), proposed_trades[0].price)
        self.assertEquals(Quantity(30, 'MC'), proposed_trades[0].quantity)
