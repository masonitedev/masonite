import pickle
import time

import pendulum
import pytest

from src.masonite.queues import Queueable
from tests import TestCase


class CountingJob(Queueable):
    """Records how many times it ran by writing to a module-level register."""

    register = []

    def handle(self):
        CountingJob.register.append("handled")


class AlwaysFailsJob(Queueable):
    register = []

    def handle(self):
        raise Exception("I always fail")

    def failed(self, payload, error):
        AlwaysFailsJob.register.append(error)


class FakeRedis:
    """Tiny in-memory stand-in implementing the subset of redis-py used by the driver."""

    def __init__(self):
        self.lists = {}
        self.sorted_sets = {}

    def rpush(self, name, value):
        self.lists.setdefault(name, []).append(value)

    def lpop(self, name):
        items = self.lists.get(name)
        return items.pop(0) if items else None

    def zadd(self, name, mapping):
        self.sorted_sets.setdefault(name, {}).update(mapping)

    def zrangebyscore(self, name, min, max):
        max = float("inf") if max == "+inf" else float(max)
        min = float("-inf") if min == "-inf" else float(min)
        return [
            member
            for member, score in sorted(
                self.sorted_sets.get(name, {}).items(), key=lambda item: item[1]
            )
            if min <= score <= max
        ]

    def zrem(self, name, member):
        return 1 if self.sorted_sets.get(name, {}).pop(member, None) is not None else 0


class TestRedisDriver(TestCase):
    def setUp(self):
        super().setUp()
        CountingJob.register = []
        AlwaysFailsJob.register = []
        self.driver = self.application.make("queue").get_driver("redis").set_options(
            self.application.make("queue").get_config_options("redis")
        )
        self.driver.connection = FakeRedis()

    def tearDown(self):
        super().tearDown()
        self.driver.connection = None
        self.driver.set_options({})

    def test_queue_names_include_namespace(self):
        self.assertEqual(self.driver.get_queue_name(), "masonite4:queue:default")
        self.assertEqual(
            self.driver.get_delayed_queue_name(), "masonite4:queue:default:delayed"
        )

    def test_queue_name_without_namespace(self):
        self.driver.set_options({"queue": "invoices"})
        self.assertEqual(self.driver.get_queue_name(), "queue:invoices")

    def test_push_puts_job_on_the_queue(self):
        self.driver.push(CountingJob())

        item = self.driver.connection.lpop(self.driver.get_queue_name())
        self.assertIsNotNone(item)

        payload = pickle.loads(item)
        self.assertEqual(payload["name"], "CountingJob")
        self.assertEqual(payload["attempts"], 0)
        self.assertEqual(payload["payload"]["callback"], "handle")
        self.assertIsInstance(payload["payload"]["obj"], CountingJob)

    def test_push_with_delay_goes_to_delayed_queue(self):
        self.driver.push(CountingJob(), delay="10 minutes")

        self.assertIsNone(self.driver.connection.lpop(self.driver.get_queue_name()))

        delayed = self.driver.connection.zrangebyscore(
            self.driver.get_delayed_queue_name(), "-inf", "+inf"
        )
        self.assertEqual(len(delayed), 1)

    def test_delayed_job_is_not_enqueued_before_time(self):
        self.driver.push(CountingJob(), delay="10 minutes")

        self.driver.enqueue_ready_delayed_jobs()

        self.assertIsNone(self.driver.connection.lpop(self.driver.get_queue_name()))

    def test_ready_delayed_job_is_moved_to_the_queue(self):
        payload = pickle.dumps({"name": "CountingJob", "payload": {}, "attempts": 0})
        self.driver.connection.zadd(
            self.driver.get_delayed_queue_name(),
            {payload: pendulum.now().subtract(seconds=1).timestamp()},
        )

        self.driver.enqueue_ready_delayed_jobs()

        self.assertEqual(
            self.driver.connection.lpop(self.driver.get_queue_name()), payload
        )
        self.assertEqual(
            self.driver.connection.zrangebyscore(
                self.driver.get_delayed_queue_name(), "-inf", "+inf"
            ),
            [],
        )

    def test_work_runs_the_job(self):
        self.driver.work(
            {
                "name": "CountingJob",
                "payload": {"obj": CountingJob(), "args": (), "callback": "handle"},
                "attempts": 0,
            }
        )

        self.assertEqual(CountingJob.register, ["handled"])

    def test_failed_job_is_requeued_with_incremented_attempts(self):
        self.driver.set_options({"attempts": 3, "namespace": "masonite4"})

        self.driver.work(
            {
                "name": "AlwaysFailsJob",
                "payload": {"obj": AlwaysFailsJob(), "args": (), "callback": "handle"},
                "attempts": 0,
            }
        )

        item = self.driver.connection.lpop(self.driver.get_queue_name())
        self.assertIsNotNone(item)
        self.assertEqual(pickle.loads(item)["attempts"], 1)
        # the failed callback only runs once attempts are exhausted
        self.assertEqual(AlwaysFailsJob.register, [])

    def test_exhausted_job_calls_failed_callback(self):
        self.driver.set_options({"attempts": 1, "namespace": "masonite4"})

        self.driver.work(
            {
                "name": "AlwaysFailsJob",
                "payload": {"obj": AlwaysFailsJob(), "args": (), "callback": "handle"},
                "attempts": 0,
            }
        )

        self.assertIsNone(self.driver.connection.lpop(self.driver.get_queue_name()))
        self.assertEqual(AlwaysFailsJob.register, ["I always fail"])

    def test_push_through_queue_class(self):
        self.application.make("queue").push(CountingJob(), driver="redis")

        item = self.driver.connection.lpop("masonite4:queue:default")
        self.assertIsNotNone(item)
        self.assertEqual(pickle.loads(item)["name"], "CountingJob")

    def test_push_with_delay_through_queue_class(self):
        self.application.make("queue").push(
            CountingJob(), driver="redis", delay="10 minutes"
        )

        self.assertIsNone(self.driver.connection.lpop("masonite4:queue:default"))
        self.assertEqual(
            len(
                self.driver.connection.zrangebyscore(
                    "masonite4:queue:default:delayed", "-inf", "+inf"
                )
            ),
            1,
        )


@pytest.mark.integrations
class TestRedisDriverIntegration(TestCase):
    """Runs against a real Redis server on 127.0.0.1:6379."""

    def setUp(self):
        super().setUp()
        CountingJob.register = []
        self.driver = self.application.make("queue").get_driver("redis").set_options(
            self.application.make("queue").get_config_options("redis")
        )
        self.driver.connection = None
        self.connection = self.driver.get_connection()
        self.connection.delete(self.driver.get_queue_name())
        self.connection.delete(self.driver.get_delayed_queue_name())

    def tearDown(self):
        super().tearDown()
        self.connection.delete(self.driver.get_queue_name())
        self.connection.delete(self.driver.get_delayed_queue_name())
        self.driver.connection = None
        self.driver.set_options({})

    def test_push_and_work_roundtrip(self):
        self.driver.push(CountingJob())

        item = self.connection.lpop(self.driver.get_queue_name())
        self.assertIsNotNone(item)

        self.driver.work(pickle.loads(bytes(item)))
        self.assertEqual(CountingJob.register, ["handled"])

    def test_delayed_job_roundtrip(self):
        self.driver.push(CountingJob(), delay="1 second")

        self.assertIsNone(self.connection.lpop(self.driver.get_queue_name()))

        time.sleep(1.1)
        self.driver.enqueue_ready_delayed_jobs()

        item = self.connection.lpop(self.driver.get_queue_name())
        self.assertIsNotNone(item)
        self.driver.work(pickle.loads(bytes(item)))
        self.assertEqual(CountingJob.register, ["handled"])
