from tests import TestCase
from unittest.mock import patch
from src.masonite.notification import Notification, Notifiable, Sms, Textable
from src.masonite.exceptions import NotificationException

from masoniteorm.models import Model


class User(Model, Notifiable):
    """User Model"""

    __fillable__ = ["name", "email", "password", "phone"]

    def route_notification_for_vonage(self):
        return "+33123456789"


class WelcomeUserNotification(Notification, Textable):
    def to_vonage(self, notifiable):
        return self.text_message("Welcome !").from_("123456")

    def via(self, notifiable):
        return ["vonage"]


class WelcomeNotification(Notification):
    def to_vonage(self, notifiable):
        return Sms().text("Welcome !").from_("123456")

    def via(self, notifiable):
        return ["vonage"]

    def should_send(self):
        return True


class OtherNotification(Notification):
    def to_vonage(self, notifiable):
        return Sms().text("Welcome !")

    def via(self, notifiable):
        return ["vonage"]


class TestVonageDriver(TestCase):
    def setUp(self):
        super().setUp()
        self.notification = self.application.make("notification")

    def test_sending_without_credentials(self):
        with self.assertRaises(NotificationException) as e:
            self.notification.route("vonage", "+33123456789").send(
                WelcomeNotification()
            )
        error_message = str(e.exception)
        self.assertIn("Vonage Error", error_message)
        self.assertIn("error code", error_message)

    def test_send_to_anonymous(self):
        with patch("vonage.Vonage") as MockVonageClass:
            self.notification.route("vonage", "+33123456789").send(
                WelcomeNotification()
            )
            MockVonageClass.return_value.sms.send.assert_called_once()

    def test_send_to_notifiable(self):
        with patch("vonage.Vonage") as MockVonageClass:
            user = User.find(1)
            user.notify(WelcomeUserNotification())
            MockVonageClass.return_value.sms.send.assert_called_once()

    def test_send_to_notifiable_with_route_notification_for(self):
        with patch("vonage.Vonage") as MockVonageClass:
            user = User.find(1)
            user.notify(WelcomeNotification())
            MockVonageClass.return_value.sms.send.assert_called_once()

    def test_global_send_from_is_used_when_not_specified(self):
        notifiable = self.notification.route("vonage", "+33123456789")
        sms = self.notification.get_driver("vonage").build(
            notifiable, OtherNotification()
        )
        self.assertEqual(sms._from, "+33000000000")

    def test_build_message_maps_sms_component_options(self):
        from vonage_sms import SmsMessage

        driver = self.notification.get_driver("vonage")
        sms = (
            Sms()
            .text("Welcome !")
            .from_("123456")
            .to("+33123456789")
            .client_ref("my-ref")
        )
        message = driver.build_message(sms.get_options())

        self.assertIsInstance(message, SmsMessage)
        dumped = message.model_dump(by_alias=True, exclude_none=True)
        self.assertEqual(dumped["to"], "+33123456789")
        self.assertEqual(dumped["from"], "123456")
        self.assertEqual(dumped["text"], "Welcome !")
        self.assertEqual(dumped["client-ref"], "my-ref")

    def test_invalid_phone_number_raises(self):
        with self.assertRaises(NotificationException) as e:
            self.notification.route("vonage", "not-a-number").send(
                WelcomeNotification()
            )
        self.assertIn("Invalid phone number", str(e.exception))
