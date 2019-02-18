import functools
import inspect
import logging

from .events import ImplementingEventHandler
from .events import InterceptingEventHandler
from .events import ObservingEventHandler
from .events import PlaceHoldingEventHandler
from .events import SimpleEventDispatcher
from .interfaces import HandlerException
from .interfaces import Middleware
from .interfaces import MiddlewareManager

log = logging.getLogger(__name__)


def intercept(event_pattern, priority):
    def deco(f):
        # Mark function as having an event_handler so we can discover it
        # The callback cannot be set to f as it is not bound yet and will be
        # set during auto discovery
        f.__event_handler = PlaceHoldingEventHandler(
            event_pattern, priority, f, InterceptingEventHandler)
        return f
    return deco


def observe(event_pattern, priority):
    def deco(f):
        # Mark function as having an event_handler so we can discover it
        # The callback cannot be set to f as it is not bound yet and will be
        # set during auto discovery
        f.__event_handler = PlaceHoldingEventHandler(
            event_pattern, priority, f, ObservingEventHandler)
        return f
    return deco


def implement(event_pattern, priority):
    def deco(f):
        # Mark function as having an event_handler so we can discover it
        # The callback will be unbound since we do not have access to `self`
        # yet, and must be bound before invocation. This binding is done
        # during middleware auto discovery
        f.__event_handler = PlaceHoldingEventHandler(
            event_pattern, priority, f, ImplementingEventHandler)
        return f
    return deco


def _deepgetattr(obj, name, default=None):
    """Recurses through an attribute chain to get the ultimate value."""
    try:
        return functools.reduce(getattr, name.split('.'), obj)
    except AttributeError:
        return default


def dispatch(event, priority, dispatcher_attr='events'):
    """
    The event decorator combines the functionality of the implement decorator
    and a manual event dispatch into a single decorator.
    """
    def deco(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            dispatcher = _deepgetattr(self, dispatcher_attr, default=None)
            if dispatcher:
                bound_func = f.__get__(self)
                if any(h for h in dispatcher.get_handlers_for_event(event)
                       if h.callback == bound_func):
                    # This function is in the dispatcher list for this event,
                    # so dispatch it
                    return dispatcher.dispatch(self, event, *args, **kwargs)
                else:
                    # This function is either not registered with the
                    # dispatcher or has been overridden, so invoke the original
                    # function directly
                    return f(self, *args, **kwargs)
            else:
                raise HandlerException(
                    "Cannot dispatch event: {0}. The object {1} should "
                    "have a property named {2}, so that the "
                    "EventDispatcher can be accessed.".format(
                        event, self, dispatcher_attr or 'events'))
        # Mark function as having an event_handler so we can discover it
        # The callback f is unbound and will be bound during middleware
        # auto discovery
        wrapper.__event_handler = PlaceHoldingEventHandler(
            event, priority, f, ImplementingEventHandler)
        return wrapper
    return deco


class SimpleMiddlewareManager(MiddlewareManager):

    def __init__(self, event_manager=None):
        self.__events = event_manager or SimpleEventDispatcher()
        self.middleware_list = []

    @property
    def events(self):
        return self.__events

    def add(self, middleware):
        if isinstance(middleware, Middleware):
            m = middleware
        else:
            m = AutoDiscoveredMiddleware(middleware)
        m.install(self.events)
        self.middleware_list.append(m)
        return m

    def remove(self, middleware):
        middleware.uninstall()
        self.middleware_list.remove(middleware)


class BaseMiddleware(Middleware):

    def __init__(self):
        self.event_handlers = []
        self.events = None

    def install(self, event_manager):
        self.events = event_manager
        discovered_handlers = self.discover_handlers(self)
        self.add_handlers(discovered_handlers)

    def add_handlers(self, handlers):
        if not hasattr(self, "event_handlers"):
            # In case the user forgot to call super class init
            self.event_handlers = []
        for handler in handlers:
            self.events.subscribe(handler)
        self.event_handlers.extend(handlers)

    def uninstall(self):
        for handler in self.event_handlers:
            handler.unsubscribe()
        self.event_handlers = []
        self.events = None

    @staticmethod
    def discover_handlers(class_or_obj):

        # https://bugs.python.org/issue30533
        # simulating a getmembers_static to be easily replaced with the
        # function if they add it to inspect module
        def getmembers_static(obj, predicate=None):
            results = []
            for key in dir(obj):
                if not inspect.isdatadescriptor(getattr(obj.__class__,
                                                        key,
                                                        None)):
                    try:
                        value = getattr(obj, key)
                    except AttributeError:  # pragma: no cover
                        continue
                    if not predicate or predicate(value):
                        results.append((key, value))
            return results

        discovered_handlers = []
        for _, func in getmembers_static(class_or_obj, inspect.ismethod):
            handler = getattr(func, "__event_handler", None)
            if handler and isinstance(handler, PlaceHoldingEventHandler):
                # create a new handler that mimics the original one,
                # essentially deep-copying the handler, so that the bound
                # method is never stored in the function itself, preventing
                # further bonding
                new_handler = handler.handler_class(handler.event_pattern,
                                                    handler.priority,
                                                    handler.callback)
                # Bind the currently unbound method
                # and set the bound method as the callback
                new_handler.callback = (new_handler.callback
                                                   .__get__(class_or_obj))
                # Mark old handler as bound
                handler._is_bound = True
                discovered_handlers.append(new_handler)
        return discovered_handlers


class AutoDiscoveredMiddleware(BaseMiddleware):

    def __init__(self, class_or_obj):
        super(AutoDiscoveredMiddleware, self).__init__()
        self.obj_to_discover = class_or_obj

    def install(self, event_manager):
        super(AutoDiscoveredMiddleware, self).install(event_manager)
        discovered_handlers = self.discover_handlers(self.obj_to_discover)
        self.add_handlers(discovered_handlers)
