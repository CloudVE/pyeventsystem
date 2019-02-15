import bisect
import fnmatch
import logging
import re

from .interfaces import EventDispatcher
from .interfaces import EventHandler
from .interfaces import HandlerException

log = logging.getLogger(__name__)


class BaseEventHandler(EventHandler):

    def __init__(self, event_pattern, priority, callback):
        self.__dispatcher = None
        self.__event_pattern = event_pattern
        self.__priority = priority
        self.__callback = callback

    def __lt__(self, other):
        # This is required for the bisect module to insert
        # event handlers sorted by priority
        return self.priority < other.priority

    def _get_next_handler(self, event):
        handler_list = self.dispatcher.get_handlers_for_event(event)
        # find position of this handler
        pos = bisect.bisect_left(handler_list, self)
        assert handler_list[pos] == self
        if pos < len(handler_list)-1:
            return handler_list[pos+1]
        else:
            return None

    @property
    def event_pattern(self):
        return self.__event_pattern

    @property
    def priority(self):
        return self.__priority

    @property
    def callback(self):
        return self.__callback

    @callback.setter
    def callback(self, value):
        self.__callback = value

    @property
    def dispatcher(self):
        return self.__dispatcher

    @dispatcher.setter
    # pylint:disable=arguments-differ
    def dispatcher(self, value):
        self.__dispatcher = value

    def unsubscribe(self):
        if self.dispatcher:
            self.dispatcher.unsubscribe(self)
        self.dispatcher = None


class InterceptingEventHandler(BaseEventHandler):

    def __init__(self, event_pattern, priority, callback):
        super(InterceptingEventHandler, self).__init__(event_pattern, priority,
                                                       callback)

    def invoke(self, event_args, *args, **kwargs):
        next_handler = self._get_next_handler(event_args.get('event'))
        event_args['next_handler'] = next_handler
        # callback is responsible for invoking the next_handler and
        # controlling the result value
        result = self.callback(event_args, *args, **kwargs)
        # Remove handler specific callback info
        event_args.pop('next_handler', None)
        return result


class ObservingEventHandler(BaseEventHandler):

    def __init__(self, event_pattern, priority, callback):
        super(ObservingEventHandler, self).__init__(event_pattern, priority,
                                                    callback)

    def invoke(self, event_args, *args, **kwargs):
        # Observers shouldn't pass a next_handler
        event_args.pop('next_handler', None)
        next_handler = self._get_next_handler(event_args.get('event'))
        # Notify listener. Ignore result from observable handler
        self.callback(event_args, *args, **kwargs)
        # Kick off the remaining handler chain
        if next_handler:
            return next_handler.invoke(event_args, *args, **kwargs)
        else:
            return None


class ImplementingEventHandler(BaseEventHandler):

    def __init__(self, event_pattern, priority, callback):
        super(ImplementingEventHandler, self).__init__(event_pattern, priority,
                                                       callback)

    def invoke(self, event_args, *args, **kwargs):
        result = self.callback(*args, **kwargs)
        next_handler = self._get_next_handler(event_args.get('event'))
        if next_handler:
            event_args['next_handler'] = next_handler
            event_args['result'] = result
            next_handler.invoke(event_args, *args, **kwargs)
            event_args.pop('result', None)
            event_args.pop('next_handler', None)
        return result


class PlaceHoldingEventHandler(object):

    def __init__(self, event_pattern, priority, callback, handler_class):
        self.event_pattern = event_pattern
        self.priority = priority
        self.callback = callback
        self.handler_class = handler_class


class SimpleEventDispatcher(EventDispatcher):

    def __init__(self):
        # The dict key is event_pattern.
        # The dict value is a list of handlers for the event pattern, sorted
        # by event priority
        self.__events = {}
        self.__handler_cache = {}

    def get_handlers_for_event(self, event):
        handlers = self.__handler_cache.get(event)
        if handlers is None:
            self.__handler_cache[event] = self._create_handler_cache(
                event)
            return self.__handler_cache.get(event)
        else:
            return handlers

    def _create_handler_cache(self, event):
        cache_list = []
        # Find all patterns matching event
        for key in self.__events.keys():
            if re.search(fnmatch.translate(key), event):
                cache_list.extend(self.__events[key])
        cache_list.sort(key=lambda h: h.priority)

        # Make sure all priorities are unique
        priority_list = [h.priority for h in cache_list]
        if len(set(priority_list)) != len(priority_list):
            guilty_prio = None
            for prio in priority_list:
                if prio == guilty_prio:
                    break
                guilty_prio = prio

            # guilty_prio should never be none since we checked for
            # duplicates before iterating
            guilty_names = [h.callback.__name__ for h in cache_list
                            if h.priority == guilty_prio]

            message = "Event '{}' has multiple subscribed handlers " \
                      "at priority '{}', with function names [{}]. " \
                      "Each priority must only have a single " \
                      "corresponding handler." \
                .format(event, guilty_prio, ", ".join(guilty_names))
            raise HandlerException(message)
        return cache_list

    def _invalidate_cache(self, event_pattern):
        # Only invalidate events that are affected by the pattern
        for key in list(self.__handler_cache.keys()):
            if re.search(fnmatch.translate(event_pattern), key):
                del self.__handler_cache[key]

    def subscribe(self, event_handler):
        event_handler.dispatcher = self
        handler_list = self.__events.get(event_handler.event_pattern, [])
        handler_list.append(event_handler)
        self.__events[event_handler.event_pattern] = handler_list
        self._invalidate_cache(event_handler.event_pattern)

    def unsubscribe(self, event_handler):
        handler_list = self.__events.get(event_handler.event_pattern, [])
        handler_list.remove(event_handler)
        event_handler.dispatcher = None
        self._invalidate_cache(event_handler.event_pattern)

    def observe(self, event_pattern, priority, callback):
        handler = ObservingEventHandler(event_pattern, priority, callback)
        self.subscribe(handler)
        return handler

    def intercept(self, event_pattern, priority, callback):
        handler = InterceptingEventHandler(event_pattern, priority, callback)
        self.subscribe(handler)
        return handler

    def implement(self, event_pattern, priority, callback):
        handler = ImplementingEventHandler(event_pattern, priority, callback)
        self.subscribe(handler)
        return handler

    def dispatch(self, sender, event, *args, **kwargs):
        handlers = self.get_handlers_for_event(event)

        if handlers:
            # only kick off first handler in chain
            event_args = {'event': event, 'sender': sender}
            return handlers[0].invoke(event_args, *args, **kwargs)
        else:
            message = "Event '{}' has no subscribed handlers.".\
                format(event)
            log.warning(message)
            return None
