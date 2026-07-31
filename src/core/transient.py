import http

TRANSIENT_HTTP_STATUS_CODES = {
    http.HTTPStatus.TOO_MANY_REQUESTS,  # 429
    http.HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
    http.HTTPStatus.BAD_GATEWAY,  # 502
    http.HTTPStatus.SERVICE_UNAVAILABLE,  # 503
    http.HTTPStatus.GATEWAY_TIMEOUT,  # 504
}


def is_transient_http_status_code(status_code: int | None) -> bool:
    """Return True for transient HTTP statuses or missing responses."""
    return status_code is None or status_code in TRANSIENT_HTTP_STATUS_CODES
