"""E-mails storage."""


import datetime
import functools
import hashlib

from truestory import app, mail as mail_util, settings
from truestory.models.base import BaseModel, ndb


def render_template(path, **kwargs):
    template = app.jinja_env.get_template(path)
    return template.render(**kwargs)


class SubscriberModel(BaseModel):

    """Subscriber e-mail got from the landing page."""

    mail = ndb.StringProperty(required=True)
    hashsum = ndb.StringProperty(required=True)
    subscribed = ndb.BooleanProperty(default=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.hashsum is None:
            date = datetime.datetime.utcnow()
            string = f"{self.mail}_{date.isoformat()}"
            self.hashsum = hashlib.md5(string.encode(settings.ENCODING)).hexdigest()

    def send_greetings(self, site):
        """Sends greetings e-mail to our new subscriber."""
        party_url = f"/static/img/party.png"
        unsubscribe_url = f"/unsubscribe/{self.hashsum}"
        render = functools.partial(
            render_template,
            site=site,
            party_url=party_url,
            unsubscribe_url=unsubscribe_url,
        )
        text_content, html_content = map(
            lambda ext: render(f"mail/greetings.{ext}"), ["txt", "html"]
        )
        mail_util.send_mail(
            self.mail, "Subscribed to TrueStory",
            text_content=text_content, html_content=html_content
        )
