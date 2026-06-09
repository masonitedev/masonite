from masonite.routes import Route

from app.controllers.WelcomeController import WelcomeController

ROUTES = [
    Route.get("/", WelcomeController.show).name("welcome"),
]
