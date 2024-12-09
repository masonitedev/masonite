import datetime
import pickle
import time

import pendulum
from ...utils.console import HasColoredOutput
from ...utils.time import parse_human_time


class RedisDriver(HasColoredOutput):
    def __init__(self, application):
        self.options = None
        self.application = application
        self.connection = None

        self.started_time = None

    def set_options(self, options):
        self.options = options
        return self

    def get_queue_namespace(self) -> str:
        namespace = self.options.get("namespace", "")
        namespace += ":" if namespace else ""
        return f"{namespace}queue:"

    def get_queue_name(self) -> str:
        return f"{self.get_queue_namespace()}{self.options.get('queue', 'default')}"

    def push(self, *jobs, args=(), **kwargs):
        _connection = self.get_connection()

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
                    "available_at": available_at.timestamp(),
                    "attempts": 0
                }
            )

            _connection.rpush(self.get_queue_name(), payload)

    def consume(self, **options):
        self.started_time = datetime.datetime.now()

        self.success(
            '[*] Waiting to process jobs on the "{}" queue. To exit press CTRL+C'.format(
                self.options.get("queue", "default")
            )
        )

        # this will allow to limit the queue runtime
        #
        # _max_allowed_run_time = int(self.options.get('max-time', 3600))

        _connection = self.get_connection()

        while True:
            time.sleep(int(self.options.get("poll", 0.5)))

            # if _max_allowed_run_time:
            #     if (datetime.datetime.now() - self.started_time).seconds > _max_allowed_run_time:
            #         self.success(
            #             '[*] Exiting the process jobs on "{}".'.format(
            #                 self.options.get("queue", "default")
            #             )
            #         )
            #         return

            item = _connection.lpop(self.get_queue_name())
            if not item:
                continue

            _payload = pickle.loads(bytes(item))

            current_time = pendulum.now()

            if current_time >= pendulum.from_timestamp(_payload['available_at']):
                self.work(_payload)
            else:
                _connection.rpush(self.get_queue_name(), item)

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
        except Exception as e:
            self.danger(
                f"[{pendulum.now(tz=self.options.get('tz', 'UTC')).to_datetime_string()}] Job Failed"
            )

            payload["attempts"] = int(payload["attempts"])
            if payload["attempts"] + 1 < int(self.options.get("attempts", 1)):
                payload["attempts"] += 1
                self.get_connection().rpush(self.get_queue_name(), pickle.dumps(payload))
            elif payload["attempts"] + 1 >= int(
                    self.options.get("attempts", 1)
            ) and not self.options.get("failed_table"):
                if hasattr(obj, "failed"):
                    getattr(obj, "failed")(unserialized, str(e))
            elif self.options.get("failed_table"):
                self.add_to_failed_queue_table(
                    self.application.make("builder").new(), payload["name"], pickle.dumps(unserialized), str(e)
                )

                if hasattr(obj, "failed"):
                    getattr(obj, "failed")(unserialized, str(e))

                self.danger(
                    f"[{pendulum.now(tz=self.options.get('tz', 'UTC')).to_datetime_string()}] Job Added to Failed Jobs Table"
                )
            else:
                self.get_connection().rpush(self.get_queue_name(), pickle.dumps(payload))

    def retry(self, **options):
        builder = (
            self.application.make("builder")
            .new()
            .table(self.options.get("failed_table", "failed_jobs"))
        )
        jobs = (
            builder
            .where({
                "queue": self.options.get("queue", "default"),
                "driver": "redis"
            })
            .get()
        )

        if len(jobs) == 0:
            self.success("No failed jobs found.")
            return

        available_at = parse_human_time("now")
        for job in jobs:
            payload = pickle.dumps(
                {
                    "name": str(job['name']),
                    "payload": pickle.loads(job['payload']),
                    "available_at": available_at.timestamp(),
                    "attempts": 0
                }
            )
            self.get_connection().rpush(self.get_queue_name(), payload)

        self.success(f"Added {len(jobs)} failed jobs back to the queue")

        builder.where_in(
            "id", [x["id"] for x in jobs]
        ).delete()

    def add_to_failed_queue_table(self, builder, name, payload, exception):
        builder.table(self.options.get("failed_table", "failed_jobs")).create(
            {
                "driver": "redis",
                "queue": self.options.get("queue", "default"),
                "name": name,
                "connection": self.options.get("connection"),
                "created_at": pendulum.now(tz=self.options.get("tz", "UTC")).to_datetime_string(),
                "exception": exception,
                "payload": payload,
                "failed_at": pendulum.now(tz=self.options.get("tz", "UTC")).to_datetime_string(),
            }
        )

    def get_connection(self):
        try:
            import redis
        except ImportError:
            raise ModuleNotFoundError(
                "Could not find the 'redis' library. Run 'pip install redis' to fix this."
            )

        if not self.connection:
            self.connection = redis.Redis(
                **self.options.get("options", {}),
                host=self.options.get("host"),
                port=self.options.get("port", 6379),
                password=self.options.get("password", None),
                decode_responses=False
            )
        return self.connection
