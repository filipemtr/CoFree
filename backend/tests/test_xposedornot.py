"""Contract and privacy tests for XposedOrNot's documented free API."""
import httpx
import pytest

from app.providers import xposedornot as provider


def fetch(payload, *, code=200, headers=None, email='user+test@example.com'):
    observed = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(code, json=payload, headers=headers)

    results = provider.find_breaches(
        email, transport=httpx.MockTransport(handler), limiter=lambda: None,
    )
    return results, observed


def test_nested_breaches_deduplicated_and_sorted():
    result, observed = fetch({
        'status': 'success', 'email': 'user+test@example.com',
        'breaches': [['LinkedIn', 'Adobe', 'Adobe'], ['Dropbox']],
    })
    assert result == ['Adobe', 'Dropbox', 'LinkedIn']
    assert observed[0].url.host == 'api.xposedornot.com'
    assert observed[0].url.scheme == 'https'
    assert observed[0].url.path.endswith('/user+test@example.com')
    assert 'hibp-api-key' not in observed[0].headers
    assert 'x-api-key' not in observed[0].headers


@pytest.mark.parametrize('code', [200, 404])
def test_documented_no_breach_payload_is_empty(code):
    result, _ = fetch({'Error': 'Not found', 'email': None}, code=code)
    assert result == []


def test_success_with_no_breaches():
    result, _ = fetch({'status': 'success', 'email': 'user+test@example.com', 'breaches': []})
    assert result == []


@pytest.mark.parametrize('payload,code', [
    ({'message': 'Not found'}, 404),
    ({'Error': 'Not found'}, 404),
    ({'status': 'error'}, 200),
    ({'Error': 'Internal server error', 'email': None}, 200),
    ({'status': 'success', 'email': 'someone@else.com', 'breaches': [['Adobe']]}, 200),
    ({'status': 'success', 'email': 'user+test@example.com', 'breaches': [{'Name': 'Adobe'}]}, 200),
    ([{'Name': 'Adobe'}], 200),
    ({'status': 'success', 'email': 'user+test@example.com', 'breaches': [[] , [None]]}, 200),
])
def test_malformed_or_unexpected_payload_never_clean(payload, code):
    with pytest.raises(provider.ProviderError):
        fetch(payload, code=code)


def test_http429_honors_retry_after_without_returning_clean():
    with pytest.raises(provider.ProviderError) as error:
        fetch({'message': 'Too Many Requests'}, code=429, headers={'Retry-After': '180'})
    assert error.value.retry_after == 180


@pytest.mark.parametrize('code', [401, 403, 500, 503, 302])
def test_other_http_errors_never_clean(code):
    with pytest.raises(provider.ProviderError):
        fetch({'message': 'unavailable'}, code=code)


def test_invalid_json_and_timeout_never_clean():
    def broken_json(request):
        return httpx.Response(200, text='not json')
    with pytest.raises(provider.ProviderError):
        provider.find_breaches('test@example.com', transport=httpx.MockTransport(broken_json), limiter=lambda: None)

    def timeout(request):
        raise httpx.ReadTimeout('down')
    with pytest.raises(provider.ProviderError):
        provider.find_breaches('test@example.com', transport=httpx.MockTransport(timeout), limiter=lambda: None)


def test_quota_denial_must_never_call_provider():
    invoked = []
    def limiter():
        raise provider.ProviderError('quota', retry_after=60)
    def handler(request):
        invoked.append(True)
        return httpx.Response(200, json={'status': 'success', 'email': 'a@b.com', 'breaches': []})
    with pytest.raises(provider.ProviderError) as error:
        provider.find_breaches('a@b.com', transport=httpx.MockTransport(handler), limiter=limiter)
    assert error.value.retry_after == 60
    assert invoked == []


def test_quota_uses_shared_redis(monkeypatch):
    redis = pytest.importorskip("redis")
    observed = []
    class FakeRedis:
        def eval(self, script, nkeys, key, now, nonce):
            observed.append((script, nkeys, key, now, nonce))
            return 0
    monkeypatch.setattr(redis.Redis, 'from_url', lambda *a, **kw: FakeRedis())
    provider._reserve_quota()
    assert len(observed) == 1
    assert observed[0][2] == 'cofree:provider:xon:check-email'
    assert '86400000' in observed[0][0]
    assert '3600000' in observed[0][0]
    assert '1000' in observed[0][0]


def test_quota_exceeded_and_redis_down(monkeypatch):
    redis = pytest.importorskip("redis")
    class Exceeded:
        def eval(self, *a):
            return 600
    monkeypatch.setattr(redis.Redis, 'from_url', lambda *a, **kw: Exceeded())
    with pytest.raises(provider.ProviderError) as error:
        provider._reserve_quota()
    assert error.value.retry_after == 600

    def broken(*args, **kwargs):
        raise redis.ConnectionError('down')
    monkeypatch.setattr(redis.Redis, 'from_url', broken)
    with pytest.raises(provider.ProviderError, match='Controle de limites'):
        provider._reserve_quota()
