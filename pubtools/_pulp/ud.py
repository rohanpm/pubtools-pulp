import threading
import requests
import os
import logging

from more_executors import Executors
from more_executors.futures import f_map

LOG = logging.getLogger("pubtools-pulp")


class UdCacheClient(object):
    def __init__(self, url, **kwargs):
        self._url = url
        self._tls = threading.local()

        retry_args = {}
        # Allow to customize max sleep time when retrying; only for autotests
        if "max_sleep" in kwargs:
            retry_args["max_sleep"] = kwargs.pop("max_sleep")

        self._session_attrs = kwargs
        self._executor = (
            Executors.thread_pool()
            .with_map(self._check_http_response)
            .with_retry(**retry_args)
        )

    @staticmethod
    def _check_http_response(response):
        response.raise_for_status()

    @property
    def _session(self):
        if not hasattr(self._tls, "session"):
            self._tls.session = requests.Session()
            for (key, value) in self._session_attrs.items():
                setattr(self._tls.session, key, value)
        return self._tls.session

    def _get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)

    def _on_failure(self, object_type, object_id, exception):
        LOG.error("Invalidating %s %s failed: %s", object_type, object_id, exception)
        raise exception

    def _flush_object(self, object_type, object_id):
        url = os.path.join(
            self._url, "internal/rcm/flush-cache", object_type, object_id
        )

        LOG.info("Invalidating %s %s", object_type, object_id)

        # This is pretty odd, but yes, an HTTP *GET* here is used to flush cache.
        out = self._executor.submit(self._get, url)

        # Wrap with logging on failure
        out = f_map(
            out, error_fn=lambda ex: self._on_failure(object_type, object_id, ex)
        )

        return out

    def flush_product(self, product_id):
        return self._flush_object("eng-product", product_id)

    def flush_repo(self, repo_id):
        return self._flush_object("repo", repo_id)
