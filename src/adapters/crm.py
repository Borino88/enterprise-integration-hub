import logging
from typing import Dict, Any
from src.core.retry import retry_engine

logger = logging.getLogger("EnterpriseHub.CRMAdapter")

class CRMAdapter:
    """
    Salesforce / HubSpot CRM Integration Adapter with data transformation and retry resilience.
    """
    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure
        self.processed_records: Dict[str, Dict[str, Any]] = {}

    def push_event(self, event_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        def _operation():
            if self.simulate_failure:
                raise ConnectionError("CRM API Gateway Timeout (504 Gateway Timeout)")
            
            # Map canonical hub payload to CRM Customer Profile schema
            crm_record = {
                "crm_id": f"crm_{event_id}",
                "account_name": payload.get("customer_name", "Unknown Account"),
                "email": payload.get("email", "no-email@domain.com"),
                "status": "ACTIVE",
                "synced_timestamp": payload.get("timestamp")
            }
            self.processed_records[event_id] = crm_record
            return crm_record

        return retry_engine.execute_with_retry("CRMAdapter", _operation, event_id)

crm_adapter = CRMAdapter()
