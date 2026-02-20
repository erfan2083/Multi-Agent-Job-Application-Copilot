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


def test_llm_requires_login():
    resp = client.post('/llm/generate', json={"prompt": "hi"})
    assert resp.status_code == 401


def test_login_then_llm_access():
    login = client.post('/auth/login', json={"username": "admin", "password": "admin"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    llm_resp = client.post('/llm/generate', json={"prompt": "hi"}, headers={"Authorization": f"Bearer {token}"})
    assert llm_resp.status_code == 200
