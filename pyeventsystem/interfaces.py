from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty


class EventDispatcher(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def observe(self, event_pattern, priority, callback):
        """
        Register a callback to be invoked when a given event occurs. `observe`
        will allow you to listen to events as they occur, but not modify the
        event chain or its parameters. If you need to modify an event, use
        the `intercept` method. `observe` is a simplified case of `intercept`,
        and receives a simpler list of parameters in its callback.

        :type event_pattern: str
        :param event_pattern: The name or pattern of the event to which you are
            subscribing the callback function. The pattern may contain glob
            wildcard parameters to be notified on any matching event name.

        :type priority: int
        :param priority: The priority that this handler should be given.
            When the event is emitted, all handlers will be run in order of
            priority.

        :type callback: function
        :param callback: The callback function that should be invoked. The
            callback must have a signature of the form:
            `def callback(event_args, *args, **kwargs)`
            Where the first positional argument is always event_args, which
            is a dict value containing information about the event.
            `event_args` includes the following keys:
            'event': The name of the event
            'sender': The object which raised the event
            The event_args dict can also be used to convey additional info to
            downstream event handlers.
            The rest of the arguments to the callback can be any combination
            of positional or keyword arguments as desired.

        :rtype: :class:`.EventHandler`
        :return:  An object of class EventHandler. The EventHandler will
            already be subscribed to the dispatcher, and need not be manually
            subscribed. The returned event handler can be used to unsubscribe
            from future events when required.
        """
        pass  # pragma: no cover

    @abstractmethod
    def intercept(self, event_pattern, priority, callback):
        """
        Register a callback to be invoked when a given event occurs. Intercept
        will allow you to both observe events and modify the event chain and
        its parameters. If you only want to observe an event, use the `observe`
        method. Intercept and `observe` only differ in what parameters the
        callback receives, with intercept receiving additional parameters to
        allow controlling the event chain.

        :type event_pattern: str
        :param event_pattern: The name or pattern of the event to which you are
            subscribing the callback function. The pattern may contain glob
            wildcard parameters to be notified on any matching event name.

        :type priority: int
        :param priority: The priority that this handler should be given.
            When the event is emitted, all handlers will be run in order of
            priority.

        :type callback: function
        :param callback: The callback function that should be invoked. The
            callback must have a signature of the form:
            `def callback(event_args, *args, **kwargs)`
            Where the first positional argument is always event_args, which
            is a dict value containing information about the event.
            `event_args` includes the following keys:
            'event': The name of the event
            'sender': The object which raised the event
            'event_handler': The next event handler in the chain
                             (only for intercepting handlers)
            The event_args dict can also be used to convey additional info to
            downstream event handlers.
            The rest of the arguments to the callback can be any combination
            of positional or keyword arguments as desired.

        :rtype: :class:`.EventHandler`
        :return:  An object of class EventHandler. The EventHandler will
            already be subscribed to the dispatcher, and need not be manually
            subscribed. The returned event handler can be used to unsubscribe
            from future events when required.
        """
        pass  # pragma: no cover

    @abstractmethod
    def dispatch(self, sender, event, *args, **kwargs):
        """
        Raises an event, which will trigger all handlers that are registered
        for this event. The return value of the emit function is the return
        value of the highest priority handler (i.e. the first handler in the
        event chain). The first event handlers is responsible for calling the
        next handler in the event chain, and so on, propagating arguments
        and return values as desired.

        :type event: str
        :param event: The name of the event which is being raised.

        :type sender: object
        :param sender: The object which is raising the event

        All additional positional and keyword arguments are passed through
        to the callback functions for the event as is. Refer to the c
        """
        pass  # pragma: no cover

    @abstractmethod
    def subscribe(self, event_handler):
        """
        Register an event handler with this dispatcher. The observe and
        intercept methods will construct an event handler and subscribe it for
        you automatically, and therefore, there is usually no need to invoke
        subscribe directly unless you have a special type of event handler.

        :type event_handler: :class:`.EventHandler`
        :param event_handler: An object of class EventHandler.
        """
        pass  # pragma: no cover

    @abstractmethod
    def unsubscribe(self, event_handler):
        """
        Unregister an event handler from this dispatcher. The event handler
        will no longer be notified on events.

        :type event_handler: :class:`.EventHandler`
        :param event_handler: An object of class EventHandler.
        """
        pass  # pragma: no cover

    @abstractmethod
    def get_handlers_for_event(self, event):
        """
        Returns a list of all registered handlers for a given event, sorted
        in order of priority.

        :type event: str
        :param event: The name of the event
        """
        pass  # pragma: no cover


class EventHandler(object):

    __metaclass__ = ABCMeta

    @abstractproperty
    def event_pattern(self):
        """
        The event pattern that this handler is listening to. May include glob
        patterns, in which case, any matching event name will trigger this
        handler.
        e.g.
            provider.storage.*
            provider.storage.volumes.list
        """
        pass  # pragma: no cover

    @abstractproperty
    def priority(self):
        """
        The priority of this handler. When a matching event occurs, handlers
        are invoked in order of priority.
        The priorities ranges from 0-1000 and 2000-3000 and >4000 are reserved
        for use by cloudbridge.
        Users should listen on priorities between 1000-2000 for pre handlers
        and 2000-3000 for post handlers.
        e.g.
            provider.storage.*
            provider.storage.volumes.list
        """
        pass  # pragma: no cover

    @abstractproperty
    def callback(self):
        """
        The callback that will be triggered when this event handler is invoked.
        The callback signature must accept *args and **kwargs and pass them
        through.
        The callback must have a signature of the form:
        `def callback(event_args, *args, **kwargs)`
        where the first positional argument is always event_args, which
        is a dict value containing information about the event.
        `event_args` includes the following keys:
        'event': The name of the event
        'sender': The object which raised the event
        'event_handler': The next event handler in the chain
                         (only for intercepting handlers)
        The event_args dict can also be used to convey additional info to
        downstream event handlers.
        The rest of the arguments to the callback can be any combination
        of positional or keyword arguments as desired.
        """
        pass  # pragma: no cover

    @abstractmethod
    def invoke(self, event_args, *args, **kwargs):
        """
        Executes this event handler's callback

        :type event_args: dict
        :param event_args: The first positional argument is always event_args,
           which is a dict value containing information about the event.
           `event_args` includes the following keys:
           'event': The name of the event
           'sender': The object which raised the event
           'event_handler': The next event handler in the chain
                            (only for intercepting handlers)
           The event_args dict can also be used to convey additional info to
           downstream event handlers.
        """
        pass  # pragma: no cover

    @abstractmethod
    def unsubscribe(self):
        """
        Unsubscribes from currently subscribed events.
        """
        pass  # pragma: no cover

    @abstractproperty
    def dispatcher(self):
        """
        Get or sets the dispatcher currently associated with this event handler
        """
        pass  # pragma: no cover


class Middleware(object):
    """
    Provides a mechanism for grouping related event handlers together, to
    provide logically cohesive middleware. The middleware class allows event
    handlers to subscribe to events through the install method, and unsubscribe
    through the uninstall method. This allows event handlers to be added and
    removed as a group. The event handler implementations will also typically
    live inside the middleware class. For example, LoggingMiddleware may
    register multiple event handlers to log data before and after calls.
    ResourceTrackingMiddleware may track all objects that are created or
    deleted.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def install(self, provider):
        """
        Use this method to subscribe all event handlers that are part of this
        middleware. The install method will be called when the middleware is
        first added to a MiddleWareManager.

        :type provider: :class:`.Provider`
        :param provider: The provider that this middleware belongs to
        """
        pass  # pragma: no cover

    @abstractmethod
    def uninstall(self, provider):
        """
        Use this method to unsubscribe all event handlers for this middleware.
        """
        pass  # pragma: no cover


class MiddlewareManager(object):
    """
    Provides a mechanism for tracking a list of installed middleware
    """

    __metaclass__ = ABCMeta

    @abstractproperty
    def events(self):
        """
        Use this property to get the EventDispatcher associated with
        this middleware manager.

        :rtype: :class:`.EventDispatcher`
        :return:  An object of class EventDispatcher.
        """

    @abstractmethod
    def add(self, middleware):
        """
        Use this method to add middleware to this middleware manager.

        :type middleware: :class:`.Middleware`
        :param middleware: The middleware implementation
        """
        pass  # pragma: no cover

    @abstractmethod
    def remove(self, middleware):
        """
        Use this method to remove this middleware from the middleware manager.
        """
        pass  # pragma: no cover


class HandlerException(Exception):
    """
    Marker interface for event handler exceptions.
    """
    pass  # pragma: no cover
