from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import time
import uuid

class EventType(str, Enum):
    ORDER_CREATED = "ORDER_CREATED"
    CUSTOMER_UPDATED = "CUSTOMER_UPDATED"
    INVOICE_PAID = "INVOICE_PAID"
    INVENTORY_SYNC = "INVENTORY_SYNC"

class TargetSystem(str, Enum):
    CRM = "CRM"
    ERP = "ERP"
    PAYMENT = "PAYMENT"
    ALL = "ALL"

class EventStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED_RETRY = "FAILED_RETRY"
    DLQ_ROUTED = "DLQ_ROUTED"

class WebhookIngestRequest(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}", description="Unique idempotency key")
    event_type: EventType = Field(..., description="Classification of integration event")
    target_system: TargetSystem = Field(TargetSystem.ALL, description="Destination subsystem routing")
    payload: Dict[str, Any] = Field(..., description="Raw transactional data payload")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp of generation")

class IntegrationEventRecord(BaseModel):
    event_id: str
    event_type: EventType
    target_system: TargetSystem
    status: EventStatus
    attempts: int = 0
    max_retries: int = 3
    payload: Dict[str, Any]
    created_at: float
    updated_at: float
    error_message: Optional[str] = None

class DLQEventResponse(BaseModel):
    dlq_id: str
    original_event_id: str
    target_system: TargetSystem
    failure_reason: str
    failed_at: float
    payload: Dict[str, Any]

class ReplayResponse(BaseModel):
    status: str
    event_id: str
    target_system: TargetSystem
    message: str
    new_status: EventStatus

class SystemHealthResponse(BaseModel):
    status: str
    active_integrations: int
    dlq_depth: int
    processed_events_count: int
    systems_status: Dict[str, str]
