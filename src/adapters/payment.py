import logging
from typing import Dict, Any
from src.core.retry import retry_engine

logger = logging.getLogger("EnterpriseHub.PaymentAdapter")

class PaymentAdapter:
    """
    Stripe / Adyen Payment Gateway Adapter with idempotency enforcement.
    """
    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure
        self.processed_transactions: Dict[str, Dict[str, Any]] = {}

    def settle_payment(self, event_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Idempotency check: prevent double billing if event previously processed
        if event_id in self.processed_transactions:
            logger.info(f"[PaymentAdapter] Idempotent hit for {event_id}. Returning cached ledger record.")
            return {"status": "IDEMPOTENT_CACHE", "data": self.processed_transactions[event_id]}

        def _operation():
            if self.simulate_failure:
                raise ValueError("Payment Gateway SSL Handshake Rejection (Code 401)")
            
            txn_record = {
                "gateway_id": f"pay_{event_id}",
                "amount": payload.get("amount", 0.0),
                "currency": payload.get("currency", "USD"),
                "status": "CAPTURED",
                "idempotency_key": event_id
            }
            self.processed_transactions[event_id] = txn_record
            return txn_record

        return retry_engine.execute_with_retry("PaymentAdapter", _operation, event_id)

payment_adapter = PaymentAdapter()
