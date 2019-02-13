import functools
import operator


def skipIfPython(op, major, minor):
    """
    A decorator for skipping tests if the python
    version doesn't match
    """
    def stringToOperator(op):
        op_map = {
            "=": operator.eq,
            "==": operator.eq,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }
        return op_map.get(op)

    def wrap(func):
        """
        The actual wrapper
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            op_func = stringToOperator(op)
            if op_func(sys.version_info, (major, minor)):
                self.skipTest(
                    "Skipping test because python version {0} is {1} expected"
                    " version {2}".format(sys.version_info[:2],
                                          op, (major, minor)))
            func(self, *args, **kwargs)
        return wrapper
    return wrap
