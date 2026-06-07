"""Vonage notification driver."""
from ....exceptions import NotificationException
from ..BaseDriver import BaseDriver


class VonageDriver(BaseDriver):
    def __init__(self, application):
        self.app = application
        self.options = {}

    def set_options(self, options):
        self.options = options
        return self

    def build(self, notifiable, notification):
        """Build SMS payload sent to Vonage API."""
        sms = self.get_data("vonage", notifiable, notification)
        if not sms._from:
            sms = sms.from_(self.options.get("sms_from"))
        if not sms._to:
            recipients = notifiable.route_notification_for("vonage")
            sms = sms.to(recipients)
        return sms

    def get_client(self):
        try:
            from vonage import Auth, Vonage
        except ImportError:
            raise ModuleNotFoundError(
                "Could not find the 'vonage' library. Run 'pip install vonage' to fix this."
            )
        return Vonage(
            Auth(
                api_key=self.options.get("key"),
                api_secret=self.options.get("secret"),
            )
        )

    def build_message(self, options):
        """Build the Vonage SmsMessage from the Sms component options."""
        from vonage_sms import SmsMessage

        message_options = {
            "to": options["to"],
            "from_": options["from"],
            "text": options["text"],
            "type": options["type"],
        }
        if options.get("client-ref"):
            message_options["client_ref"] = options["client-ref"]
        return SmsMessage(**message_options)

    def send(self, notifiable, notification):
        """Used to send the SMS."""
        from vonage import VonageError

        sms = self.build(notifiable, notification)
        client = self.get_client()
        recipients = sms._to
        if not isinstance(recipients, list):
            recipients = [recipients]
        response = None
        for recipient in recipients:
            if not self.is_valid_phone_number(recipient):
                raise NotificationException(f"Invalid phone number: {recipient}")
            message = self.build_message(sms.to(recipient).build().get_options())
            try:
                response = client.sms.send(message)
            except VonageError as e:
                raise NotificationException(
                    "Vonage Error: {0}. Please refer to API documentation for more details.".format(
                        str(e)
                    )
                )
        return response

    def is_valid_phone_number(self, phone_number):
        import phonenumbers

        try:
            parsed_number = phonenumbers.parse(phone_number, None)
            return phonenumbers.is_valid_number(parsed_number)
        except phonenumbers.NumberParseException:
            return False
