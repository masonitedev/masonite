import json

from tests import TestCase
from src.masonite.routes import Route
from src.masonite.request import Request
from src.masonite.utils.http import generate_wsgi
from tests.integrations.app.User import User


class TestPagination(TestCase):
    """Covers issue #27: framework-level pagination with a JSON contract
    (data/meta/links) and a view helper for server-rendered pages.

    The test client's self.get()/self.post() helpers don't support query
    strings (generate_wsgi() bakes the raw path straight into PATH_INFO, so
    a "?page=2" suffix never reaches QUERY_STRING and the router 404s
    before the controller even runs). So page/per_page reading is proven
    against a real Request built with an actual query string, and the
    HTTP round-trip is proven with the default page/per_page instead.
    """

    def setUp(self):
        super().setUp()
        # Ad-hoc routes for these tests only; nothing touches the shared
        # routes/web.py file.
        self.addRoutes(
            Route.get("/paginate/users", "WelcomeController@paginate_users"),
            Route.get(
                "/paginate/users/view", "WelcomeController@paginate_users_view"
            ),
        )
        # The seeder already creates 1 user; add 5 more so per_page=2 gives 3
        # full pages (6 total) to paginate through.
        self.extra_user_ids = []
        for i in range(5):
            user = User.create(
                {
                    "name": f"Extra {i}",
                    "email": f"extra{i}@example.com",
                    "password": "secret",
                }
            )
            self.extra_user_ids.append(user.id)

    def tearDown(self):
        # Leave the shared test database exactly as we found it.
        for user_id in self.extra_user_ids:
            User.where("id", user_id).delete()
        super().tearDown()

    # -- Real HTTP round-trip (default page/per_page) --------------------
    # Proves the controller -> request.paginate() -> Response auto-JSON
    # wiring actually works end-to-end, not just that the pieces look right
    # in isolation.

    def test_http_response_is_a_json_envelope_with_data_meta_and_links(self):
        response = self.get("/paginate/users")
        response.assertOk()
        payload = json.loads(response.content)

        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertIn("links", payload)
        # Defaults: page=1, per_page=2 (set in WelcomeController.paginate_users)
        self.assertEqual(payload["meta"]["current_page"], 1)
        self.assertEqual(payload["meta"]["total"], 6)
        self.assertEqual(len(payload["data"]), 2)
        # First page: no previous link, a next link pointing at page 2.
        self.assertIsNone(payload["links"]["prev"])
        self.assertIn("page=2", payload["links"]["next"])

    def test_http_view_renders_pagination_links_for_the_first_page(self):
        response = self.get("/paginate/users/view")
        response.assertOk()
        html = response.get_content()

        # Page 1 of 3: a "next" link, an active marker, but no "prev" link.
        self.assertIn('rel="next"', html)
        self.assertIn('aria-current="page"', html)
        self.assertNotIn('rel="prev"', html)

    # -- Request.paginate() reading page/per_page from a query string ----
    # Built directly against a real WSGI environ (not the HTTP test client,
    # see class docstring), so this still exercises the actual production
    # code path: Request.paginate() -> masoniteorm's Model.paginate() ->
    # Paginator.serialize()/links() against the real test database.

    def _request(self, query_string):
        environ = generate_wsgi(path="/paginate/users", query_string=query_string)
        return Request(environ)

    def test_reads_page_and_per_page_from_the_query_string(self):
        paginator = self._request("page=2&per_page=3").paginate(User, per_page=2)

        self.assertEqual(paginator.current_page, 2)
        self.assertEqual(len(paginator), 3)
        self.assertEqual(paginator.last_page, 2)

    def test_links_preserve_other_query_params_and_point_to_correct_pages(self):
        paginator = self._request("page=2&sort=name").paginate(User, per_page=2)
        links = paginator.links()

        self.assertIn("page=1", links["first"])
        self.assertIn("page=1", links["prev"])
        self.assertIn("sort=name", links["prev"])
        self.assertIn("page=3", links["next"])
        self.assertIn("sort=name", links["next"])
        self.assertIn("page=3", links["last"])

    def test_last_page_has_no_next_link(self):
        paginator = self._request("page=3").paginate(User, per_page=2)

        self.assertIsNone(paginator.links()["next"])
        self.assertIsNotNone(paginator.links()["prev"])

    def test_simple_paginate_has_no_last_page_or_last_link(self):
        # SimplePaginator never counts the total, so there is no "last page"
        # to point a "last" link at.
        #
        # Note: masoniteorm's own SimplePaginator.has_more_pages() checks
        # `len(result) > per_page`, but QueryBuilder.simple_paginate() only
        # ever fetches exactly `per_page` rows (it would need `per_page + 1`
        # to peek ahead), so `next` can never actually be set today. That is
        # a pre-existing issue in masonitedev/orm, not something to route
        # around here -- this test documents the current, real behavior.
        paginator = self._request("page=1").paginate(User, per_page=2, simple=True)

        self.assertIsNone(paginator.last_page)
        self.assertIsNone(paginator.links()["last"])
        self.assertIsNone(paginator.links()["next"])
