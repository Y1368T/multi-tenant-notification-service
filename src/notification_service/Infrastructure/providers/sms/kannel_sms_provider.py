from typing import Any, Dict, List
import logging
from datetime import datetime
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel

from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import (
    NotificationResponse,
    ProviderTestResponse,
)

logger = logging.getLogger(__name__)


class KannelSMSConfig(BaseModel):
    """Configuration settings for Kannel SMS provider (HTTP interface)."""

    baseUrl: str
    username: str
    password: str
    sender: str | None = None
    dlrUrl: str | None = None
    dlrMask: str | None = None
    timeoutSeconds: int | None = 10
    extraParams: Dict[str, Any] | None = None

    class Config:
        from_attributes = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KannelSMSConfig":
        return cls(
            baseUrl=data.get("baseUrl", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            sender=data.get("sender"),
            dlrUrl=data.get("dlrUrl"),
            dlrMask=str(data.get("dlrMask")) if data.get("dlrMask") is not None else None,
            timeoutSeconds=int(data.get("timeoutSeconds", 10)) if data.get("timeoutSeconds") is not None else 10,
            extraParams=data.get("extraParams") or {},
        )

    def to_query_params(self, to: str, text: str, sender_override: str | None = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "username": self.username,
            "password": self.password,
            "to": to,
            "text": text,
        }

        sender_value = sender_override or self.sender
        if sender_value:
            params["from"] = sender_value

        if self.dlrUrl:
            params["dlr-url"] = self.dlrUrl
            if self.dlrMask:
                params["dlr-mask"] = self.dlrMask

        if self.extraParams:
            params.update(self.extraParams)

        return params


class KannelSMSProvider(IProviderService):
    """Kannel SMS provider implementation (HTTP sendsms API)."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)

    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """Test Kannel configuration by sending a lightweight request."""
        try:
            kannel_conf = KannelSMSConfig.from_dict(config)
            if not kannel_conf.baseUrl or not kannel_conf.username or not kannel_conf.password:
                return ProviderTestResponse(
                    success=False,
                    message="baseUrl, username and password are required for Kannel configuration",
                )

            # Perform a simple GET to ensure gateway is reachable.
            resp = await self.client.get(kannel_conf.baseUrl, timeout=kannel_conf.timeoutSeconds or 10)
            resp.raise_for_status()
            logger.info("Kannel gateway reachable for test")
            return ProviderTestResponse(success=True, message="Kannel gateway reachable")
        except Exception as exc:  # pragma: no cover - network errors
            logger.error(f"Exception during Kannel SMS test: {exc}")
            return ProviderTestResponse(success=False, message=f"Exception during test: {str(exc)}")

    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
        templateId: UUID,
    ) -> NotificationResponse:
        """
        Send SMS via Kannel HTTP interface.

        Uses tenantConfig.config to build the Kannel configuration and sends one
        message per recipient number.
        """
        try:
            kannel_conf = KannelSMSConfig.from_dict(tenantConfig.config or {})
            if not kannel_conf.baseUrl or not kannel_conf.username or not kannel_conf.password:
                return NotificationResponse(
                    notificationId="",
                    status="failed",
                    channel="SMS",
                    recipients=[],
                    tenantId=str(tenantConfig.tenantId),
                    createdAt=datetime.utcnow(),
                    success=False,
                    message="Invalid Kannel configuration: baseUrl, username and password are required",
                )

            recipients: List[str] = [recipient.address for recipient in requestObject.recipients]
            if not recipients:
                return NotificationResponse(
                    notificationId="",
                    status="failed",
                    channel="SMS",
                    recipients=[],
                    tenantId=str(tenantConfig.tenantId),
                    createdAt=datetime.utcnow(),
                    success=False,
                    message="No recipients provided",
                )

            successful_recipients: List[str] = []
            failed_recipients: List[str] = []

            for to in recipients:
                params = kannel_conf.to_query_params(to=to, text=messageToSend, sender_override=None)
                try:
                    logger.info(f"Sending SMS via Kannel to {to}")
                    response = await self.client.get(
                        kannel_conf.baseUrl,
                        params=params,
                        timeout=kannel_conf.timeoutSeconds or 10,
                    )
                    response.raise_for_status()
                    body = response.text.strip()
                    # Typical Kannel success starts with "0:"
                    if body.startswith("0:"):
                        successful_recipients.append(to)
                        logger.info(f"Kannel SMS sent successfully to {to}, response: {body}")
                    else:
                        failed_recipients.append(to)
                        logger.error(f"Kannel SMS failed for {to}, response: {body}")
                except Exception as exc:  # pragma: no cover - network errors
                    failed_recipients.append(to)
                    logger.error(f"Error sending SMS via Kannel to {to}: {exc}")

            if successful_recipients:
                return NotificationResponse(
                    notificationId=str(uuid4()),
                    status="sent",
                    channel="SMS",
                    recipients=successful_recipients,
                    tenantId=str(tenantConfig.tenantId),
                    createdAt=datetime.utcnow(),
                    success=True,
                    message=messageToSend,
                )

            return NotificationResponse(
                notificationId="",
                status="failed",
                channel="SMS",
                recipients=[],
                tenantId=str(tenantConfig.tenantId),
                createdAt=datetime.utcnow(),
                success=False,
                message="Failed to send SMS via Kannel to all recipients",
            )
        except Exception as exc:  # pragma: no cover - unexpected
            logger.error(f"Unexpected error while sending SMS via Kannel: {exc}", exc_info=True)
            return NotificationResponse(
                notificationId="",
                status="failed",
                channel="SMS",
                recipients=[],
                tenantId=str(tenantConfig.tenantId),
                createdAt=datetime.utcnow(),
                success=False,
                message=str(exc),
            )


    async def callback(self, providerCallback):
        return await super().callback(providerCallback)
    
    async def saveToOutbox(self, notificationId, requestObject, retryCount = 0, nextRetryAt = None):
        return await super().saveToOutbox(notificationId, requestObject, retryCount, nextRetryAt)