
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

    def get_rate(self):
        rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        if self.scope in rates and rates[self.scope]:
            return rates[self.scope]
        raise ImproperlyConfigured("No default throttle rate set for '%s' scope" % self.scope)