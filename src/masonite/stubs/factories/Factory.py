from masoniteorm.factories import Factory

from __model_module__ import __model__


class __class__:
    """Factory for the __model__ model.

    Call `__class__.register()` once during app bootstrap (for example
    from a service provider's `boot` method) to make this factory
    available to `Factory(__model__).create()` / `.make()` in tests and
    seeders.
    """

    @staticmethod
    def register():
        Factory.register(__model__, __class__.definition)

    @staticmethod
    def definition(faker):
        return {}
