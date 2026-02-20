from fastapi.testclient import TestClient
from apps.api.main import app


client = TestClient(app)


def test_health():
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


def test_jobs_search_smoke():
    resp = client.post('/jobs/search', json={"resume_text":"Jane\npython fastapi", "preferences":{"remote_only": True}})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
