import pytest
from fastapi.testclient import TestClient
from src.api.main import app, EVENT_AUDIT_LOG
from src.core.dlq import dlq_service
from src.adapters.crm import crm_adapter
from src.adapters.erp import erp_adapter
from src.adapters.payment import payment_adapter
from src.models.schemas import EventType, TargetSystem

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_state():
    EVENT_AUDIT_LOG.clear()
    dlq_service.clear()
    crm_adapter.simulate_failure = False
    erp_adapter.simulate_failure = False
    payment_adapter.simulate_failure = False

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["dlq_depth"] == 0

def test_webhook_ingestion_success():
    payload = {
        "event_type": "ORDER_CREATED",
        "target_system": "ALL",
        "payload": {
            "order_id": "ORD-998811",
            "customer_name": "Acme Corp",
            "email": "billing@acmecorp.com",
            "amount": 4950.00,
            "items": ["SKU-ENT-SERVER"]
        }
    }
    response = client.post("/api/v1/webhooks/ingest", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert len(EVENT_AUDIT_LOG) == 1
    assert dlq_service.depth == 0

def test_webhook_idempotency_cache():
    payload = {
        "event_id": "evt_idempotent_test_01",
        "event_type": "INVOICE_PAID",
        "target_system": "PAYMENT",
        "payload": {"amount": 100.0, "currency": "USD"}
    }
    # First call
    res1 = client.post("/api/v1/webhooks/ingest", json=payload)
    assert res1.status_code == 202
    # Second call with same event_id
    res2 = client.post("/api/v1/webhooks/ingest", json=payload)
    assert res2.status_code == 202
    assert res2.json()["event_id"] == "evt_idempotent_test_01"
    assert len(EVENT_AUDIT_LOG) == 1

def test_dlq_routing_on_adapter_failure():
    # Force CRM adapter failure
    crm_adapter.simulate_failure = True

    payload = {
        "event_id": "evt_fail_crm_001",
        "event_type": "CUSTOMER_UPDATED",
        "target_system": "CRM",
        "payload": {"customer_name": "Broken Gateway Ltd"}
    }
    response = client.post("/api/v1/webhooks/ingest", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "DLQ_ROUTED"
    assert "CRM API Gateway Timeout" in data["error_message"]
    assert dlq_service.depth == 1

    # Verify DLQ endpoint inspection
    dlq_res = client.get("/api/v1/dlq/events")
    assert dlq_res.status_code == 200
    dlq_list = dlq_res.json()
    assert len(dlq_list) == 1
    assert dlq_list[0]["original_event_id"] == "evt_fail_crm_001"

def test_dlq_replay_recovery():
    # Force ERP adapter failure initially
    erp_adapter.simulate_failure = True

    payload = {
        "event_id": "evt_replay_test_01",
        "event_type": "INVENTORY_SYNC",
        "target_system": "ERP",
        "payload": {"order_id": "ORD-5544"}
    }
    client.post("/api/v1/webhooks/ingest", json=payload)
    assert dlq_service.depth == 1
    
    dlq_record = dlq_service.list_dlq_events()[0]
    dlq_id = dlq_record.dlq_id

    # Now replay event (replay handler automatically resets adapter simulated failure for test recovery)
    replay_res = client.post(f"/api/v1/dlq/replay/{dlq_id}")
    assert replay_res.status_code == 200
    replay_data = replay_res.json()
    assert replay_data["status"] == "SUCCESS"
    assert replay_data["new_status"] == "SUCCESS"
    assert dlq_service.depth == 0
    assert EVENT_AUDIT_LOG["evt_replay_test_01"].status == "SUCCESS"
