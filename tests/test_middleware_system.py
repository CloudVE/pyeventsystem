import unittest

from pyeventsystem.events import SimpleEventDispatcher
from pyeventsystem.interfaces import HandlerException
from pyeventsystem.interfaces import Middleware
from pyeventsystem.middleware import BaseMiddleware
from pyeventsystem.middleware import SimpleMiddlewareManager
from pyeventsystem.middleware import dispatch
from pyeventsystem.middleware import implement
from pyeventsystem.middleware import intercept
from pyeventsystem.middleware import observe


class MiddlewareSystemTestCase(unittest.TestCase):

    def test_basic_middleware(self):

        class DummyMiddleWare(Middleware):

            def __init__(self):
                self.invocation_order = ""

            def install(self, event_manager):
                self.event_manager = event_manager
                self.invocation_order += "install_"

            def uninstall(self):
                self.invocation_order += "uninstall"

        dispatcher = SimpleEventDispatcher()
        manager = SimpleMiddlewareManager(dispatcher)
        middleware = DummyMiddleWare()
        manager.add(middleware)

        self.assertEqual(middleware.invocation_order, "install_",
                         "install should be called when adding new middleware")

        manager.remove(middleware)
        self.assertEqual(middleware.invocation_order, "install_uninstall",
                         "uninstall should be called when removing middleware")

    def test_middleware_dispatcher(self):

        dispatcher = SimpleEventDispatcher()
        manager = SimpleMiddlewareManager(dispatcher)
        assert manager.events == dispatcher

        # If a dispatcher is not provided, a new one should be created
        manager2 = SimpleMiddlewareManager()
        assert manager2.events != dispatcher

        # dispatching should work
        manager2.events.dispatch(self, "dummyevent")

    def test_base_middleware(self):
        EVENT_NAME = "some.event.occurred"

        class DummyMiddleWare(BaseMiddleware):

            def __init__(self):
                self.invocation_order = ""

            @intercept(event_pattern="some.event.*", priority=900)
            def my_callback_intcpt(self, event_args, *args, **kwargs):
                self.invocation_order += "intcpt_"
                assert 'first_pos_arg' in args
                assert kwargs.get('a_keyword_arg') == "something"
                next_handler = event_args.get('next_handler')
                return next_handler.invoke(event_args, *args, **kwargs)

            @implement(event_pattern="some.event.*", priority=950)
            def my_callback_impl(self, *args, **kwargs):
                self.invocation_order += "impl_"
                assert 'first_pos_arg' in args
                assert kwargs.get('a_keyword_arg') == "something"
                return "hello"

            @observe(event_pattern="some.event.*", priority=1000)
            def my_callback_obs(self, event_args, *args, **kwargs):
                self.invocation_order += "obs"
                assert 'first_pos_arg' in args
                assert event_args['result'] == "hello"
                assert kwargs.get('a_keyword_arg') == "something"

        dispatcher = SimpleEventDispatcher()
        manager = SimpleMiddlewareManager(dispatcher)
        middleware = DummyMiddleWare()
        manager.add(middleware)
        dispatcher.dispatch(self, EVENT_NAME, 'first_pos_arg',
                            a_keyword_arg='something')

        self.assertEqual(middleware.invocation_order, "intcpt_impl_obs")
        self.assertListEqual(
            [middleware.my_callback_intcpt, middleware.my_callback_impl,
             middleware.my_callback_obs],
            [handler.callback for handler
             in dispatcher.get_handlers_for_event(EVENT_NAME)])

        manager.remove(middleware)

        self.assertListEqual([], dispatcher.get_handlers_for_event(EVENT_NAME))

    def test_multiple_middleware(self):
        EVENT_NAME = "some.really.interesting.event.occurred"

        class DummyMiddleWare1(BaseMiddleware):

            @observe(event_pattern="some.really.*", priority=1000)
            def my_obs1_3(self, *args, **kwargs):
                pass

            @implement(event_pattern="some.*", priority=970)
            def my_impl1_2(self, *args, **kwargs):
                return "hello"

            @intercept(event_pattern="some.*", priority=900)
            def my_intcpt1_1(self, event_args, *args, **kwargs):
                next_handler = event_args.get('next_handler')
                return next_handler.invoke(event_args, *args, **kwargs)

        class DummyMiddleWare2(BaseMiddleware):

            @observe(event_pattern="some.really.*", priority=1050)
            def my_obs2_3(self, *args, **kwargs):
                pass

            @intercept(event_pattern="*", priority=950)
            def my_intcpt2_2(self, event_args, *args, **kwargs):
                next_handler = event_args.get('next_handler')
                return next_handler.invoke(event_args, *args, **kwargs)

            @implement(event_pattern="some.really.*", priority=920)
            def my_impl2_1(self, *args, **kwargs):
                pass

        dispatcher = SimpleEventDispatcher()
        manager = SimpleMiddlewareManager(dispatcher)
        middleware1 = DummyMiddleWare1()
        middleware2 = DummyMiddleWare2()
        manager.add(middleware1)
        manager.add(middleware2)
        dispatcher.dispatch(self, EVENT_NAME)

        # Callbacks in both middleware classes should be registered
        self.assertListEqual(
            [middleware1.my_intcpt1_1, middleware2.my_impl2_1,
             middleware2.my_intcpt2_2, middleware1.my_impl1_2,
             middleware1.my_obs1_3, middleware2.my_obs2_3],
            [handler.callback for handler
             in dispatcher.get_handlers_for_event(EVENT_NAME)])

        manager.remove(middleware1)

        # Only middleware2 callbacks should be registered
        self.assertListEqual(
            [middleware2.my_impl2_1, middleware2.my_intcpt2_2,
             middleware2.my_obs2_3],
            [handler.callback for handler in
             dispatcher.get_handlers_for_event(EVENT_NAME)])

        # add middleware back to check that internal state is properly handled
        manager.add(middleware1)

        # should one again equal original list
        self.assertListEqual(
            [middleware1.my_intcpt1_1, middleware2.my_impl2_1,
             middleware2.my_intcpt2_2, middleware1.my_impl1_2,
             middleware1.my_obs1_3, middleware2.my_obs2_3],
            [handler.callback for handler
             in dispatcher.get_handlers_for_event(EVENT_NAME)])

    def test_automatic_middleware(self):
        EVENT_NAME = "another.interesting.event.occurred"

        class SomeDummyClass(object):

            @observe(event_pattern="another.really.*", priority=1000)
            def not_a_match(self, *args, **kwargs):
                pass

            @intercept(event_pattern="another.*", priority=900)
            def my_callback_intcpt2(self, *args, **kwargs):
                pass

            def not_an_event_handler(self, *args, **kwargs):
                pass

            @observe(event_pattern="another.interesting.*", priority=1000)
            def my_callback_obs1(self, *args, **kwargs):
                pass

            @implement(event_pattern="another.interesting.*", priority=1050)
            def my_callback_impl(self, *args, **kwargs):
                pass

        dispatcher = SimpleEventDispatcher()
        manager = SimpleMiddlewareManager(dispatcher)
        some_obj = SomeDummyClass()
        middleware = manager.add(some_obj)
        dispatcher.dispatch(self, EVENT_NAME)

        # Middleware should be discovered even if class containing interceptors
        # doesn't inherit from Middleware
        self.assertListEqual(
            [some_obj.my_callback_intcpt2, some_obj.my_callback_obs1,
             some_obj.my_callback_impl],
            [handler.callback for handler
             in dispatcher.get_handlers_for_event(EVENT_NAME)])

        manager.remove(middleware)

        # Callbacks should be correctly removed
        self.assertListEqual(
            [],
            [handler.callback for handler in
             dispatcher.get_handlers_for_event(EVENT_NAME)])

    def test_event_decorator(self):
        EVENT_NAME = "some.event.occurred"

        class SomeDummyClass(object):

            def __init__(self):
                self.invocation_order = ""
                self.events = SimpleEventDispatcher()

            @intercept(event_pattern="some.event.*", priority=900)
            def my_callback_intcpt(self, event_args, *args, **kwargs):
                self.invocation_order += "intcpt_"
                assert 'first_pos_arg' in args
                assert kwargs.get('a_keyword_arg') == "something"
                next_handler = event_args.get('next_handler')
                return next_handler.invoke(event_args, *args, **kwargs)

            @observe(event_pattern="some.event.*", priority=3000)
            def my_callback_obs(self, event_args, *args, **kwargs):
                self.invocation_order += "obs"
                assert 'first_pos_arg' in args
                assert event_args['result'] == "hello"
                assert kwargs.get('a_keyword_arg') == "something"

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                self.invocation_order += "impl_"
                assert 'first_pos_arg' in args
                assert kwargs.get('a_keyword_arg') == "something"
                return "hello"

        obj = SomeDummyClass()
        manager = SimpleMiddlewareManager(obj.events)
        middleware = manager.add(obj)

        # calling my_implementation should trigger all events
        result = obj.my_callback_impl(
            'first_pos_arg', a_keyword_arg='something')

        self.assertEqual(result, "hello")
        self.assertEqual(obj.invocation_order, "intcpt_impl_obs")
        callbacks = [handler.callback for handler
                     in middleware.events.get_handlers_for_event(EVENT_NAME)]

        self.assertNotIn(
            obj.my_callback_impl, callbacks,
            "The event impl callback should not be directly contained"
            " in callbacks to avoid a circular dispatch")

        self.assertEqual(
            len(set(callbacks).difference(
                set([obj.my_callback_intcpt,
                     obj.my_callback_obs]))),
            1,
            "The event impl callback should be included in the list of"
            "  callbacks indirectly")

        manager.remove(middleware)

        # At this point, the my_callback_impl function is no longer registered
        # with the event system, so calling it should simply result in invoking
        # the original function
        result = obj.my_callback_impl(
            'first_pos_arg', a_keyword_arg='something')

        self.assertEqual(result, "hello")

    def test_event_decorator_no_event_property(self):
        EVENT_NAME = "some.event.occurred"

        class SomeDummyClass(object):

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                assert 'first_pos_arg' in args
                assert kwargs.get('a_keyword_arg') == "something"
                return "hello"

        obj = SomeDummyClass()
        events = SimpleEventDispatcher()
        manager = SimpleMiddlewareManager(events)
        manager.add(obj)

        # calling my_implementation should raise an exception
        with self.assertRaises(HandlerException):
            obj.my_callback_impl('first_pos_arg', a_keyword_arg='something')

        obj.events = events
        result = obj.my_callback_impl('first_pos_arg',
                                      a_keyword_arg='something')
        self.assertEqual(result, "hello")

    def test_middleware_inheritance_override(self):
        EVENT_NAME = "some.event.occurred"
        invocation_order = [""]

        manager = SimpleMiddlewareManager()

        class ParentMiddlewareClass(object):

            @property
            def events(self):
                return manager.events

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                invocation_order[0] += "base_"

        class ChildMiddlewareClass(ParentMiddlewareClass):

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                invocation_order[0] += "child"

        obj = ChildMiddlewareClass()
        manager.add(obj)

        obj.my_callback_impl()
        self.assertEqual(invocation_order[0], "child")

    def test_middleware_inheritance_super(self):
        EVENT_NAME = "some.event.occurred"
        invocation_order = [""]

        manager = SimpleMiddlewareManager()

        class ParentMiddlewareClass(object):

            @property
            def events(self):
                return manager.events

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                invocation_order[0] += "base_"

        class ChildMiddlewareClass(ParentMiddlewareClass):

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                super(ChildMiddlewareClass, self).my_callback_impl(
                    *args, **kwargs)
                invocation_order[0] += "child"

        obj = ChildMiddlewareClass()
        manager.add(obj)

        obj.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_child")

    def test_middleware_inheritance_multiple_middleware(self):
        EVENT_NAME = "some.event.occurred"
        invocation_order = [""]

        manager = SimpleMiddlewareManager()

        class SimpleMiddlewareClass(object):

            @property
            def events(self):
                return manager.events

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                invocation_order[0] += "base_"

        class SpecializedMiddlewareClass(SimpleMiddlewareClass):

            @dispatch(event=EVENT_NAME, priority=3500)
            def my_callback_impl(self, *args, **kwargs):
                super(SpecializedMiddlewareClass, self).my_callback_impl(
                    *args, **kwargs)
                invocation_order[0] += "child"

        obj_simple = SimpleMiddlewareClass()
        obj_specialized = SpecializedMiddlewareClass()
        m_simple = manager.add(obj_simple)
        m_specialized = manager.add(obj_specialized)

        obj_simple.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_base_child")
        invocation_order[0] = ""
        obj_specialized.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_base_child")

        # simply emitting the event should also cause both to get invoked
        invocation_order[0] = ""
        manager.events.dispatch(self, EVENT_NAME)
        self.assertEqual(invocation_order[0], "base_base_child")

        # Removed middleware should no longer trigger an event
        manager.remove(m_simple)
        invocation_order[0] = ""
        obj_simple.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_")

        invocation_order[0] = ""
        obj_specialized.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_child")

        # simply emitting the event should only cause the registered one
        # to get invoked
        invocation_order[0] = ""
        manager.events.dispatch(self, EVENT_NAME)
        self.assertEqual(invocation_order[0], "base_child")

        manager.remove(m_specialized)

        # Emitting the event now should register nothing, since all middleware
        # has been removed
        invocation_order[0] = ""
        manager.events.dispatch(self, EVENT_NAME)
        self.assertEqual(invocation_order[0], "")

        # calling the object directly should still work
        invocation_order[0] = ""
        obj_specialized.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_child")

    def test_unregistered_dispatch(self):
        # Test case for when the class has not been registered with middleware
        # at all, but the event property exists
        EVENT_NAME = "some.event.occurred"
        invocation_order = [""]

        class ParentMiddlewareClass(object):

            def __init__(self):
                self.__events = SimpleEventDispatcher()

            @property
            def events(self):
                return self.__events

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                invocation_order[0] += "base_"

        class ChildMiddlewareClass(ParentMiddlewareClass):

            @dispatch(event=EVENT_NAME, priority=2500)
            def my_callback_impl(self, *args, **kwargs):
                super(ChildMiddlewareClass, self).my_callback_impl(
                    *args, **kwargs)
                invocation_order[0] += "child"

        obj = ChildMiddlewareClass()
        obj.my_callback_impl()
        self.assertEqual(invocation_order[0], "base_child")
