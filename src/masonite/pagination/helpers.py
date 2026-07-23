from markupsafe import Markup, escape


def paginate_links(paginator, window=2):
    """Render Previous / numbered pages / Next links for a Paginator as a
    safe HTML fragment, meant to be dropped straight into a template.

    Registered as a shared view global in HelpersProvider, so it is callable
    from any template as `{{ paginate_links(paginator) }}` without an import.
    """
    current = paginator.current_page
    # last is None for SimplePaginator (it never counts the total), in which
    # case we simply can't render numbered page links -- only Previous/Next.
    last = paginator.last_page

    parts = []

    # Previous link, only if there is a previous page.
    prev_url = paginator.url_for_page(paginator.previous_page)
    if prev_url:
        parts.append(f'<a href="{escape(prev_url)}" rel="prev">Previous</a>')

    # Numbered page links within `window` pages of the current one, e.g.
    # window=2 on page 5 of 10 shows pages 3 4 [5] 6 7.
    if last:
        start = max(1, current - window)
        end = min(last, current + window)
        for page in range(start, end + 1):
            if page == current:
                parts.append(f'<span aria-current="page">{page}</span>')
            else:
                url = paginator.url_for_page(page)
                parts.append(f'<a href="{escape(url)}">{page}</a>')

    # Next link, only if there is a next page.
    next_url = paginator.url_for_page(paginator.next_page)
    if next_url:
        parts.append(f'<a href="{escape(next_url)}" rel="next">Next</a>')

    return Markup('<nav class="pagination">' + " ".join(parts) + "</nav>")
