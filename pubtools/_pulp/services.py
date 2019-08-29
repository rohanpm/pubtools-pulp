import logging
import os
import threading

from fastpurge import FastPurgeClient
from pushcollector import Collector
from pubtools.pulplib import Client

from .ud import UdCacheClient

LOG = logging.getLogger("pulp-task")
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"


class Services(object):
    def __init__(self):
        super(Services, self).__init__()

        self.__lock = threading.RLock()
        self.__pulp_client = None
        self.__fastpurge = None
        self.__udcache = None
        self.__collector = None

    @property
    def args(self):
        # Must be implemented in subclass
        raise NotImplementedError()

    @property
    def pulp_client(self):
        """Pulp client for the task

        returns the client if available
        else gets one using the info from parsed args
        Pulp password for the client can also be provided as
        environment variable PULP_PASSWORD
        """
        with self.__lock:
            if not self.__pulp_client:
                self.__pulp_client = self.__get_pulp_client()
        return self.__pulp_client

    @property
    def fastpurge_client(self):
        """Fast Purge client for the task, created on first use."""
        with self.__lock:
            if not self.__fastpurge:
                self.__fastpurge = self.__get_fastpurge()
        return self.__fastpurge

    @property
    def udcache_client(self):
        """UD cache client for the task, created on first use."""
        with self.__lock:
            if not self.__udcache:
                self.__udcache = self.__get_udcache()
        return self.__udcache

    @property
    def collector(self):
        """Push collector instance, created on first use."""
        with self.__lock:
            if not self.__collector:
                self.__collector = Collector.get()
        return self.__collector

    def __get_pulp_client(self):
        auth = None

        # checks if pulp password is available as enviornment variable
        if self.args.pulp_user:
            pulp_password = self.args.pulp_password or os.environ.get("PULP_PASSWORD")
            if not pulp_password:
                LOG.warning("No pulp password provided for %s", self.args.pulp_user)
            auth = (self.args.pulp_user, pulp_password)

        kwargs = {"auth": auth}

        if self.args.pulp_insecure:
            kwargs["verify"] = False

        return Client(self.args.pulp_url, **kwargs)

    def __get_fastpurge(self):
        fastpurge_args = {}

        for key in ["host", "client_secret", "client_token", "access_token"]:
            arg_name = "fastpurge_" + key
            arg_value = getattr(self.args, arg_name)
            if arg_value:
                fastpurge_args[key] = arg_value

        # If there's any argument provided, then we pass args to the client.
        # Otherwise, we pass None and we expect ~/.edgerc to be used.
        return FastPurgeClient(auth=(fastpurge_args or None))

    def __get_udcache(self):
        args = self.args
        if not args.udcache_url:
            return None

        return UdCacheClient(
            url=args.udcache_url, auth=(args.udcache_user, args.udcache_password)
        )
