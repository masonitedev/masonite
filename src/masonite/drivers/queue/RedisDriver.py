import pickle
import time

import pendulum

from ...utils.console import HasColoredOutput
from ...utils.time import parse_human_time


class RedisDriver(HasColoredOutput):
    def __init__(self, application):
        self.application = application
        self.connection = None
        self.options = {}

    def set_options(self, options):
        self.options = options
        return self

    def get_queue_namespace(self):
        namespace = self.options.get("namespace", "")
        namespace += ":" if namespace else ""
        return f"{namespace}queue:"

    def get_queue_name(self):
        return f"{self.get_queue_namespace()}{self.options.get('queue', 'default')}"

    def get_delayed_queue_name(self):
        return f"{self.get_queue_name()}:delayed"

    def push(self, *jobs, args=(), **kwargs):
        connection = self.get_connection()

        available_at = parse_human_time(kwargs.get("delay", "now"))

        for job in jobs:
            payload = pickle.dumps(
                {
                    "name": str(job),
                    "payload": {
                        "obj": job,
                        "args": args,
                        "kwargs": kwargs,
                        "callback": self.options.get("callback", "handle"),
                    },
                    "attempts": 0,
                }
            )

            if available_at <= pendulum.now(tz=self.options.get("tz", "UTC")):
                connection.rpush(self.get_queue_name(), payload)
            else:
                connection.zadd(
                    self.get_delayed_queue_name(),
                    {payload: available_at.timestamp()},
                )

    def consume(self):
        self.success(
            '[*] Waiting to process jobs on the "{}" queue. To exit press CTRL+C'.format(
                self.options.get("queue", "default")
            )
        )

        connection = self.get_connection()
        poll = float(self.options.get("poll", 1) or 1)

        while True:
            self.enqueue_ready_delayed_jobs()

            item = connection.lpop(self.get_queue_name())
            if item is None:
                time.sleep(poll)
                continue

            try:
                payload = pickle.loads(bytes(item))
            except Exception as e:  # skipcq
                # a poison message should not bring the worker down
                self.danger(f"Could not deserialize job payload, discarding it. ({e})")
                continue

            self.work(payload)

    def enqueue_ready_delayed_jobs(self):
        """Move delayed jobs whose time has come onto the main queue."""
        connection = self.get_connection()
        now = pendulum.now(tz=self.options.get("tz", "UTC")).timestamp()

        for item in connection.zrangebyscore(
            self.get_delayed_queue_name(), "-inf", now
        ):
            # zrem returns 1 only for the worker that removed it, so a job
            # is enqueued exactly once even with multiple workers polling.
            if connection.zrem(self.get_delayed_queue_name(), item):
                connection.rpush(self.get_queue_name(), item)

    def work(self, payload):
        unserialized = payload["payload"]
        obj = unserialized["obj"]
        args = unserialized["args"]
        callback = unserialized["callback"]

        try:
            try:
                getattr(obj, callback)(*args)
            except AttributeError:
                if callable(obj):
                    obj(*args)

            self.success(
                f"[{pendulum.now(tz=self.options.get('tz', 'UTC')).to_datetime_string()}] Job Successfully Processed"
            )
        except Exception as e:  # skipcq
            self.danger(
                f"[{pendulum.now(tz=self.options.get('tz', 'UTC')).to_datetime_string()}] Job Failed"
            )

            attempts = int(payload.get("attempts", 0))

            if attempts + 1 < int(self.options.get("attempts", 1)):
                payload["attempts"] = attempts + 1
                self.get_connection().rpush(
                    self.get_queue_name(), pickle.dumps(payload)
                )
                return

            if self.options.get("failed_table"):
                self.add_to_failed_queue_table(
                    self.application.make("builder").new(),
                    payload["name"],
                    pickle.dumps(unserialized),
                    str(e),
                )

                self.danger(
                    f"[{pendulum.now(tz=self.options.get('tz', 'UTC')).to_datetime_string()}] Job Added to Failed Jobs Table"
                )

            if hasattr(obj, "failed"):
                getattr(obj, "failed")(unserialized, str(e))

    def retry(self):
        builder = (
            self.application.make("builder")
            .new()
            .on(self.options.get("connection"))
            .table(self.options.get("failed_table", "failed_jobs"))
        )

        jobs = (
            builder.where("queue", self.options.get("queue", "default"))
            .where("driver", "redis")
            .get()
        )

        if len(jobs) == 0:
            self.success("No failed jobs found.")
            return

        connection = self.get_connection()

        for job in jobs:
            payload = pickle.dumps(
                {
                    "name": str(job["name"]),
                    "payload": pickle.loads(job["payload"]),
                    "attempts": 0,
                }
            )
            connection.rpush(self.get_queue_name(), payload)

        self.success(f"Added {len(jobs)} failed job(s) back to the queue")

        builder.where_in("id", [x["id"] for x in jobs]).delete()

    def add_to_failed_queue_table(self, builder, name, payload, exception):
        builder.table(self.options.get("failed_table", "failed_jobs")).create(
            {
                "driver": "redis",
                "queue": self.options.get("queue", "default"),
                "name": name,
                "connection": self.options.get("connection"),
                "created_at": pendulum.now(
                    tz=self.options.get("tz", "UTC")
                ).to_datetime_string(),
                "exception": exception,
                "payload": payload,
                "failed_at": pendulum.now(
                    tz=self.options.get("tz", "UTC")
                ).to_datetime_string(),
            }
        )

    def get_connection(self):
        if self.connection:
            return self.connection

        try:
            from redis import Redis
        except ImportError:
            raise ModuleNotFoundError(
                "Could not find the 'redis' library. Run 'pip install redis' to fix this."
            )

        self.connection = Redis(
            **self.options.get("options", {}),
            host=self.options.get("host", "127.0.0.1"),
            port=int(self.options.get("port", 6379)),
            password=self.options.get("password") or None,
            decode_responses=False,
        )

        return self.connection
