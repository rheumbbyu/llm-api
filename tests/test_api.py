import pytest #quality control tests
from fastapi.testclient import TestClient #pretend patient
from app.main import app 
from app.limiter import limiter

@pytest.fixture
def client():
    limiter.reset() #wipes the signin sheet clean before each test
    with TestClient(app) as c:
        yield c

def test_health(client):
    r=client.get("/health")
    assert r.status_code == 200 #must be true or flag as FAILED 
    assert r.json()["status"] == "ok"

def test_generate_echo(client): #positive control 
    r = client.post("/v1/generate", json={"prompt": "Hello World", "max_tokens": 50})
    assert r.status_code == 200
    body = r.json() #reads the report 
    assert "request_id" in body  #checks if the barcode or PIN exists
    assert body["generated_text"] == "[ECHO] Hello World"
    assert body["total_tokens"] > 0 
    
def test_empty_prompt_rejected(client): #negative control. an empty tube is rejected
    r = client.post("/v1/generate", json={"prompt": "   "})
    assert r.status_code == 422
    
def test_rate_limit(client): #over quota 
    statuses = [] #empty results sheet
    for _ in range(6): 
        r = client.post("/v1/generate", json={"prompt": "hi"})
        statuses.append(r.status_code)
    assert statuses[:5] == [200] * 5 #first entries / samples accepted 
    assert statuses[5] == 429 #6th entry or sample is rejected