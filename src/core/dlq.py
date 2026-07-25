import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from src.models.schemas import DLQEventResponse, TargetSystem

logger = logging.getLogger("EnterpriseHub.DLQ")

class DeadLetterQueueService:
    """
    In-memory Dead-Letter Queue (DLQ) storage and event replay inspection service.
    In enterprise production, this interfaces directly with AWS SQS DLQ, RabbitMQ Dead Letter Exchange, or Kafka topic.
    """
    def __init__(self):
        self._queue: Dict[str, DLQEventResponse] = {}

    def route_to_dlq(self, original_event_id: str, target_system: TargetSystem, failure_reason: str, payload: Dict[str, Any]) -> DLQEventResponse:
        dlq_id = f"dlq_{uuid.uuid4().hex[:10]}"
        record = DLQEventResponse(
            dlq_id=dlq_id,
            original_event_id=original_event_id,
            target_system=target_system,
            failure_reason=failure_reason,
            failed_at=time.time(),
            payload=payload
        )
        self._queue[dlq_id] = record
        logger.error(f"[DLQ ROUTED] Event {original_event_id} routed to DLQ ({dlq_id}) for {target_system.value}. Reason: {failure_reason}")
        return record

    def list_dlq_events(self, limit: int = 50) -> List[DLQEventResponse]:
        return list(self._queue.values())[:limit]

    def get_dlq_event(self, dlq_id: str) -> Optional[DLQEventResponse]:
        return self._queue.get(dlq_id)

    def remove_dlq_event(self, dlq_id: str) -> bool:
        if dlq_id in self._queue:
            del self._queue[dlq_id]
            return True
        return False

    def clear(self):
        self._queue.clear()

    @property
    def depth(self) -> int:
        return len(self._queue)

dlq_service = DeadLetterQueueService()
