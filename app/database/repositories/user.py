from ._base import BaseRepository
from ..models import (
    SubscriptionModel,
    UserModel,
    AlertSettingModel,
    TriggeredAlertModel,
)


class UserRepository(BaseRepository[UserModel]):
    model = UserModel


class SubscriptionRepository(BaseRepository[SubscriptionModel]):
    model = SubscriptionModel


class AlertSettingRepository(BaseRepository[AlertSettingModel]):
    model = AlertSettingModel


class TrigeredAlertRepository(BaseRepository[SubscriptionModel]):
    model = TriggeredAlertModel
