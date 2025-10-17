"""
Test Factory to make fake objects for testing
"""

from datetime import date, timedelta
import factory
from service.models import Promotion


class PromotionFactory(factory.Factory):
    """Creates fake promotions for testing"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to data model"""

        model = Promotion

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("catch_phrase")
    promotion_type = factory.Faker("random_element", elements=("Percentage off", "Buy One Get One", "Fixed amount off"))
    value = factory.Faker("random_int", min=1, max=99)
    product_id = factory.Faker("random_int", min=1, max=1000)
    start_date = factory.LazyFunction(date.today)
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
