.. image:: https://travis-ci.org/CloudVE/pyeventsystem.svg?branch=master
   :target: https://travis-ci.org/CloudVE/pyeventsystem
   :alt: build status

.. image:: https://codecov.io/gh/CloudVE/pyeventsystem/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/CloudVE/pyeventsystem
   :alt: coverage status

pyeventsystem
=============

pyeventsystem is an event-driven middleware library for Python. In addition to
providing a mechanism for subscribing and listening to events, it also provides
a mechanism for intercepting functions, thus making it suitable for writing
middleware. By intercepting functions, middleware can be injected before, after
or even replacing the original function. It also provides capabilities for
grouping related event handlers into middleware classes, making it easier to
manage installable middleware.

Simple Example
==============

.. code-block:: python

    from pyeventsystem.middleware import SimpleMiddlewareManager
    from pyeventsystem.middleware import dispatch
    from pyeventsystem.middleware import observe


    class MyMiddleWare(object):

        def __init__(self, event_dispatcher):
            self.events = event_dispatcher

        @dispatch("a.series.of.unfortunate.events", priority=2500)
        def perform_villainy(self, name):
            return "Drop ACME Anvil on " + name

        @observe("a.series.of.unfortunate.events", priority=2400)
        def pre_log_villainy(self, event_args, name):
            print("Prepping for villainy: " + name)

        @observe("*.unfortunate.events", priority=2600)
        def post_log_villainy(self, event_args, name):
            print("Result of villainy: {0}".format(event_args['result']))


    manager = SimpleMiddlewareManager()
    myobj = MyMiddleWare(manager.events)
    manager.add(myobj)
    myobj.perform_villainy("RoadRunner")

In this example, we have intercepted the `perform_villainy` function, and
observed the function both before and after execution.

The output is:

.. code-block:: console

    Prepping for villainy: RoadRunner
    Result of villainy: Drop ACME Anvil on RoadRunner
