from core.rate_limit import TokenBucketRateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_token_bucket_allows_burst_then_refills():
    clock = FakeClock()
    limiter = TokenBucketRateLimiter(capacity=2, refill_per_second=0.5, clock=clock)

    assert limiter.allow("user") is True
    assert limiter.allow("user") is True
    assert limiter.allow("user") is False
    clock.now = 2
    assert limiter.allow("user") is True
    assert limiter.allow("user") is False


def test_token_bucket_keeps_users_independent():
    clock = FakeClock()
    limiter = TokenBucketRateLimiter(capacity=1, refill_per_second=1, clock=clock)

    assert limiter.allow("one") is True
    assert limiter.allow("one") is False
    assert limiter.allow("two") is True
