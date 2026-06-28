from __future__ import annotations

from datetime import UTC, datetime

from app.core.enums import DerivedSubscriptionStatus, SubscriptionStatus
from app.models import Subscription


def subscription_allows_write(subscription: Subscription | None) -> bool:
    if subscription is None:
        return False

    now = datetime.now(UTC)
    if subscription.status == SubscriptionStatus.ACTIVE.value:
        return subscription.expires_at is None or subscription.expires_at > now

    if subscription.status == SubscriptionStatus.TRIALING.value:
        return subscription.trial_ends_at is not None and subscription.trial_ends_at > now

    return False


def subscription_status(subscription: Subscription | None) -> str:
    if subscription is None:
        return DerivedSubscriptionStatus.MISSING.value

    if (
        subscription.status == SubscriptionStatus.TRIALING.value
        and not subscription_allows_write(subscription)
    ):
        return SubscriptionStatus.EXPIRED.value

    return subscription.status
