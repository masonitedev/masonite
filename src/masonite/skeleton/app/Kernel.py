from masonite.auth import Sign
from masonite.configuration import Configuration, config
from masonite.environment import LoadEnvironment
from masonite.foundation import response_handler
from masonite.middleware import (
    ClearDumpsBetweenRequestsMiddleware,
    EncryptCookies,
    IpMiddleware,
    LoadUserMiddleware,
    MaintenanceModeMiddleware,
    SessionMiddleware,
    ShareErrorsInSessionMiddleware,
    ThrottleRequestsMiddleware,
)
from masonite.routes import Route
from masonite.storage import StorageCapsule
from masonite.utils.location import base_path
from masonite.utils.structures import load

from app.middlewares.AuthenticationMiddleware import AuthenticationMiddleware
from app.middlewares.VerifyCsrfToken import VerifyCsrfToken


class Kernel:

    http_middleware = [
        EncryptCookies,
        ClearDumpsBetweenRequestsMiddleware,
        IpMiddleware,
        MaintenanceModeMiddleware,
    ]

    route_middleware = {
        "web": [
            SessionMiddleware,
            ShareErrorsInSessionMiddleware,
            LoadUserMiddleware,
            VerifyCsrfToken,
        ],
        "auth": [AuthenticationMiddleware],
        "throttle": [ThrottleRequestsMiddleware],
    }

    def __init__(self, app):
        self.application = app

    def register(self):
        self.load_environment()
        self.register_configurations()
        self.register_middleware()
        self.register_routes()
        self.register_database()
        self.register_templates()
        self.register_storage()

    def load_environment(self):
        LoadEnvironment()

    def register_configurations(self):
        # load configuration
        self.application.bind("config.location", "config")
        configuration = Configuration(self.application)
        configuration.load()
        self.application.bind("config", configuration)
        key = config("application.key")
        self.application.bind("key", key)
        self.application.bind("sign", Sign(key))

        # set locations
        self.application.bind("controllers.location", "app/controllers")
        self.application.bind("jobs.location", "app/jobs")
        self.application.bind("requests.location", "app/requests")
        self.application.bind("mailables.location", "app/mailables")
        self.application.bind("providers.location", "app/providers")
        self.application.bind("listeners.location", "app/listeners")
        self.application.bind("validation.location", "app/validation")
        self.application.bind("tasks.location", "app/tasks")
        self.application.bind("events.location", "app/events")
        self.application.bind("policies.location", "app/policies")
        self.application.bind("notifications.location", "app/notifications")
        self.application.bind("resources.location", "resources")
        self.application.bind("models.location", "app/models")
        self.application.bind("observers.location", "app/observers")
        self.application.bind("commands.location", "app/commands")
        self.application.bind("middlewares.location", "app/middlewares")

    def register_middleware(self):
        self.application.make("middleware").add(self.route_middleware).add(
            self.http_middleware
        )

    def register_routes(self):
        Route.set_controller_locations(self.application.make("controllers.location"))

        self.application.bind("routes.location", "routes/web")
        self.application.make("router").add(
            Route.group(
                load(self.application.make("routes.location"), "ROUTES", []),
                middleware=["web"],
            )
        )
        self.application.bind("routes.api.location", "routes/api")

    def register_templates(self):
        self.application.bind("views.location", "templates")

    def register_database(self):
        from masoniteorm.query import QueryBuilder

        self.application.bind(
            "builder",
            QueryBuilder(connection_details=config("database.databases")),
        )

        self.application.bind("migrations.location", "databases/migrations")
        self.application.bind("seeds.location", "databases/seeds")
        self.application.bind("factories.location", "databases/factories")

        self.application.bind("resolver", config("database.db"))

    def register_storage(self):
        storage = StorageCapsule()
        storage.add_storage_assets(
            {
                # folder            # template alias
                "storage/static": "static/",
                "storage/compiled": "static/",
                "storage/uploads": "static/",
                "storage/public": "/",
            }
        )
        self.application.bind("storage_capsule", storage)

        self.application.set_response_handler(response_handler)
        self.application.use_storage_path(base_path("storage"))
