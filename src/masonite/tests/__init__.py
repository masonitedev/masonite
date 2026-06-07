from .MockInput import MockInput
from .HttpTestResponse import HttpTestResponse
from .DatabaseTransactions import DatabaseTransactions


def __getattr__(name):
    # TestCase is imported lazily so that the framework can boot without
    # pytest installed (pytest only ships with the "test" extra).
    if name == "TestCase":
        from .TestCase import TestCase as test_case_class

        # rebind explicitly: importing the submodule sets the package
        # attribute to the MODULE (same name as the class), which would
        # shadow the class on every subsequent import.
        globals()["TestCase"] = test_case_class
        return test_case_class
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
