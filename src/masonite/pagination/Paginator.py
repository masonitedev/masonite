from urllib.parse import urlencode


class Paginator:
    """Wraps one of masoniteorm's paginators (LengthAwarePaginator or
    SimplePaginator) with request awareness: it knows the current path and
    query string, so it can expose a `links` block (first/prev/next/last)
    alongside the `data`/`meta` the ORM paginator already builds.
    """

    def __init__(self, paginator, path, query_params=None, page_name="page"):
        # `paginator` is the raw masoniteorm paginator returned by
        # Model.paginate()/simple_paginate() -- it already holds the page of
        # results plus current/next/previous page numbers.
        self.paginator = paginator
        # `path` and `query_params` are the current request's path and
        # other query string values, so links can be built without the
        # caller having to reconstruct the URL themselves.
        self.path = path
        self.query_params = dict(query_params or {})
        self.page_name = page_name

    def url_for_page(self, page):
        """Build the path + query string for the given page number, keeping
        every other query parameter the current request had. Returns None
        when there is no such page (e.g. no next page)."""
        if not page:
            return None

        # Every other query param (sort, filters, ...) is preserved as-is;
        # only the page number itself is swapped out.
        params = {**self.query_params, self.page_name: page}
        return f"{self.path}?{urlencode(params)}"

    @property
    def current_page(self):
        return self.paginator.current_page

    @property
    def last_page(self):
        # Only LengthAwarePaginator knows the total row count, so it is the
        # only one that can say which page is last; SimplePaginator has no
        # concept of a last page at all.
        return getattr(self.paginator, "last_page", None)

    @property
    def previous_page(self):
        return self.paginator.previous_page

    @property
    def next_page(self):
        return self.paginator.next_page

    def has_more_pages(self):
        return self.paginator.has_more_pages()

    def links(self):
        """The `links` block of the JSON contract: first/prev/next/last as
        full path+query URLs. Any entry with no corresponding page (e.g.
        `last` for a SimplePaginator, or `next` on the last page) is None."""
        return {
            "first": self.url_for_page(1),
            "prev": self.url_for_page(self.previous_page),
            "next": self.url_for_page(self.next_page),
            "last": self.url_for_page(self.last_page),
        }

    def serialize(self, *args, **kwargs):
        # Response.view() auto-JSON-serializes anything with a .serialize()
        # method, so returning a Paginator straight from a controller already
        # produces the full {data, meta, links} envelope for free.
        payload = self.paginator.serialize(*args, **kwargs)
        payload["links"] = self.links()
        return payload

    def to_json(self, *args, **kwargs):
        import json

        return json.dumps(self.serialize(*args, **kwargs))

    def __iter__(self):
        # Lets templates/controllers loop over the current page's rows
        # directly: `for user in paginator`.
        return iter(self.paginator)

    def __len__(self):
        return len(self.paginator.result)
