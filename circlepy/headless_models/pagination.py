"""Small strict HTTP bridges used by explicit Member iterator methods."""

from ..pagination import NumberedPages, aiter_pages, iter_pages


def member_pages(
    resource, endpoint, params, *, pagination=None, method="GET", max_pages=None
):
    def fetch(request):
        options = {"json" if method == "POST" else "params": request.params}
        return resource._request(method, endpoint, _strict=True, **options)

    return iter_pages(
        fetch,
        pagination=pagination or NumberedPages(),
        params=params,
        max_pages=max_pages,
    )


def async_member_pages(
    resource, endpoint, params, *, pagination=None, method="GET", max_pages=None
):
    async def fetch(request):
        options = {"json" if method == "POST" else "params": request.params}
        return await resource._client._request(
            method, endpoint, _strict=True, **options
        )

    return aiter_pages(
        fetch,
        pagination=pagination or NumberedPages(),
        params=params,
        max_pages=max_pages,
    )
