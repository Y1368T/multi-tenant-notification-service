from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio
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


class JasminHTTPConfig(BaseModel):
    """Configuration for Jasmin HTTP send interface."""

    baseUrl: str
    username: str
    password: str
    sender: Optional[str] = None
    dlrUrl: Optional[str] = None
    dlrLevel: Optional[str] = None
    dlrMethod: Optional[str] = None
    priority: Optional[int] = None
    coding: Optional[int] = None
    timeoutSeconds: Optional[int] = 10
    extraParams: Dict[str, Any] | None = None

    class Config:
        from_attributes = True

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "JasminHTTPConfig":
        return cls(
            baseUrl=data.get("baseUrl", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            sender=data.get("sender"),
            dlrUrl=data.get("dlrUrl"),
            dlrLevel=str(data.get("dlrLevel")) if data.get("dlrLevel") is not None else None,
            dlrMethod=data.get("dlrMethod"),
            priority=int(data.get("priority", 0)) if data.get("priority") is not None else None,
            coding=int(data.get("coding", 0)) if data.get("coding") is not None else None,
            timeoutSeconds=int(data.get("timeoutSeconds", 10)) if data.get("timeoutSeconds") is not None else 10,
            extraParams=data.get("extraParams") or {},
        )

    def toQueryParams(self, to: str, text: str, sender_override: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "username": self.username,
            "password": self.password,
            "to": to,
            "content": text,
        }

        sender_value = sender_override or self.sender
        if sender_value:
            params["from"] = sender_value

        if self.dlrUrl:
            params["dlr-url"] = self.dlrUrl
            if self.dlrLevel:
                params["dlr-level"] = self.dlrLevel
            if self.dlrMethod:
                params["dlr-method"] = self.dlrMethod

        if self.priority is not None:
            params["priority"] = self.priority

        if self.coding is not None:
            params["coding"] = self.coding

        if self.extraParams:
            params.update(self.extraParams)

        return params


class JasminSMPPConfig(BaseModel):
    """Configuration for Jasmin SMPP client mode."""

    host: str
    port: int = 2775
    systemId: str
    password: str
    systemType: str | None = None
    bindType: str = "transceiver"  # transmitter / receiver / transceiver
    sourceAddr: str | None = None
    dataCoding: int | None = 0
    registeredDelivery: int | None = 1
    connectTimeoutSeconds: int | None = 10

    class Config:
        from_attributes = True

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "JasminSMPPConfig":
        return cls(
            host=data.get("host", ""),
            port=int(data.get("port", 2775)) if data.get("port") is not None else 2775,
            systemId=data.get("systemId", ""),
            password=data.get("password", ""),
            systemType=data.get("systemType"),
            bindType=data.get("bindType", "transceiver"),
            sourceAddr=data.get("sourceAddr"),
            dataCoding=int(data.get("dataCoding", 0)) if data.get("dataCoding") is not None else 0,
            registeredDelivery=int(data.get("registeredDelivery", 1))
            if data.get("registeredDelivery") is not None
            else 1,
            connectTimeoutSeconds=int(data.get("connectTimeoutSeconds", 10))
            if data.get("connectTimeoutSeconds") is not None
            else 10,
        )


class JasminSMSProvider(IProviderService):
    """
    Jasmin SMS provider that supports both HTTP and SMPP based on tenant configuration.

    tenantConfig.config MUST contain a key "mode" with value "http" or "smpp".
    For "http" mode, JasminHTTPConfig is used.
    For "smpp" mode, JasminSMPPConfig is used.
    """

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)

    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """
        Test Jasmin configuration.

        - For HTTP mode: perform a lightweight GET on baseUrl.
        - For SMPP mode: currently a configuration validation only (no network dial).
        """
        try:
            mode = (config or {}).get("mode", "http").lower()
            if mode == "http":
                http_conf = JasminHTTPConfig.fromDict(config or {})
                if not http_conf.baseUrl or not http_conf.username or not http_conf.password:
                    return ProviderTestResponse(
                        success=False,
                        message="baseUrl, username and password are required for Jasmin HTTP configuration",
                    )
                resp = await self.client.get(http_conf.baseUrl, timeout=http_conf.timeoutSeconds or 10)
                resp.raise_for_status()
                return ProviderTestResponse(success=True, message="Jasmin HTTP gateway reachable")
            elif mode == "smpp":
                smpp_conf = JasminSMPPConfig.fromDict(config or {})
                if not smpp_conf.host or not smpp_conf.systemId or not smpp_conf.password:
                    return ProviderTestResponse(
                        success=False,
                        message="host, systemId and password are required for Jasmin SMPP configuration",
                    )
                # For now we only validate configuration; full SMPP connectivity
                # tests can be implemented later.
                return ProviderTestResponse(success=True, message="Jasmin SMPP configuration looks valid")
            else:
                return ProviderTestResponse(success=False, message=f"Unsupported Jasmin mode: {mode}")
        except Exception as exc:  # pragma: no cover - network/config errors
            logger.error(f"Exception during Jasmin SMS test: {exc}")
            return ProviderTestResponse(success=False, message=f"Exception during test: {str(exc)}")

    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
        templateId: UUID,
    ) -> NotificationResponse:
        """
        Send SMS via Jasmin using HTTP or SMPP depending on tenantConfig.config["mode"].
        """
        config: Dict[str, Any] = tenantConfig.config or {}
        mode = (config.get("mode") or "http").lower()

        if mode == "http":
            return await self._send_http(requestObject, tenantConfig, messageToSend)
        if mode == "smpp":
            return await self._send_smpp(requestObject, tenantConfig, messageToSend)

        return NotificationResponse(
            notificationId="",
            status="failed",
            channel="SMS",
            recipients=[],
            tenantId=str(tenantConfig.tenantId),
            createdAt=datetime.utcnow(),
            success=False,
            message=f"Unsupported Jasmin mode: {mode}",
        )

    async def _send_http(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
    ) -> NotificationResponse:
        """Send SMS using Jasmin HTTP API."""
        http_conf = JasminHTTPConfig.fromDict(tenantConfig.config or {})

        if not http_conf.baseUrl or not http_conf.username or not http_conf.password:
            return NotificationResponse(
                notificationId="",
                status="failed",
                channel="SMS",
                recipients=[],
                tenantId=str(tenantConfig.tenantId),
                createdAt=datetime.utcnow(),
                success=False,
                message="Invalid Jasmin HTTP configuration: baseUrl, username and password are required",
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
            params = http_conf.toQueryParams(to=to, text=messageToSend, sender_override=None)
            try:
                logger.info(f"Sending SMS via Jasmin HTTP to {to}")
                response = await self.client.post(
                    http_conf.baseUrl,
                    params=params,
                    timeout=http_conf.timeoutSeconds or 10,
                )
                response.raise_for_status()
                # Jasmin returns JSON by default
                try:
                    body = response.json()
                except Exception:  # pragma: no cover - non-json body
                    body = {"raw": response.text}

                status_val = str(body.get("status", "")).upper()
                success_statuses = {"ESME_ROK", "ROK", "0"}
                if status_val in success_statuses or status_val == "" and response.status_code < 300:
                    successful_recipients.append(to)
                    logger.info(f"Jasmin HTTP SMS sent successfully to {to}, response: {body}")
                else:
                    failed_recipients.append(to)
                    logger.error(f"Jasmin HTTP SMS failed for {to}, response: {body}")
            except Exception as exc:  # pragma: no cover - network errors
                failed_recipients.append(to)
                logger.error(f"Error sending SMS via Jasmin HTTP to {to}: {exc}")

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
            message="Failed to send SMS via Jasmin HTTP to all recipients",
        )

    async def _send_smpp(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
    ) -> NotificationResponse:
        """
        Send SMS using Jasmin SMPP interface.

        NOTE: This implementation uses a very minimal synchronous SMPP client
        executed in a background thread. For production, consider replacing
        this with a fully-featured async SMPP client and connection pooling.
        """
        smpp_conf = JasminSMPPConfig.fromDict(tenantConfig.config or {})

        # Delay import so that environments that don't use SMPP are not forced
        # to have smpplib installed.
        try:
            import smpplib.client  # type: ignore
            import smpplib.consts  # type: ignore
            import smpplib.gsm  # type: ignore
        except ImportError as exc:  # pragma: no cover - missing dependency
            logger.error(f"smpplib is required for Jasmin SMPP mode: {exc}")
            return NotificationResponse(
                notificationId="",
                status="failed",
                channel="SMS",
                recipients=[],
                tenantId=str(tenantConfig.tenantId),
                createdAt=datetime.utcnow(),
                success=False,
                message="smpplib package is required for Jasmin SMPP mode",
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

        def _send_sync() -> List[str]:
            """Blocking SMPP send in a separate thread."""
            successful: List[str] = []
            client = smpplib.client.Client(smpp_conf.host, smpp_conf.port)

            client.connect()
            client.bind_transceiver(
                system_id=smpp_conf.systemId,
                password=smpp_conf.password,
                system_type=smpp_conf.systemType or "",
            )

            for to in recipients:
                try:
                    pdu = client.send_message(
                        source_addr_ton=smpplib.consts.SMPP_TON_ALNUM,
                        source_addr_npi=smpplib.consts.SMPP_NPI_UNK,
                        source_addr=smpp_conf.sourceAddr or "",
                        dest_addr_ton=smpplib.consts.SMPP_TON_INTERNATIONAL,
                        dest_addr_npi=smpplib.consts.SMPP_NPI_E164,
                        destination_addr=to,
                        short_message=smpplib.gsm.make_parts(messageToSend)[0],
                        data_coding=smpp_conf.dataCoding or 0,
                        registered_delivery=smpp_conf.registeredDelivery or 1,
                    )
                    logger.info(f"Jasmin SMPP sent to {to}, message_id={getattr(pdu, 'message_id', None)}")
                    successful.append(to)
                except Exception as exc_inner:
                    logger.error(f"Failed to send Jasmin SMPP SMS to {to}: {exc_inner}")

            try:
                client.unbind()
                client.disconnect()
            except Exception:
                # ignore disconnect errors
                pass

            return successful

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:  # pragma: no cover - no running loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        successful_recipients = await loop.run_in_executor(None, _send_sync)

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
            message="Failed to send SMS via Jasmin SMPP to all recipients",
        )


    async def callback(self, providerCallback):
        return await super().callback(providerCallback)
    
    async def saveToOutbox(self, notificationId, requestObject, retryCount = 0, nextRetryAt = None):
        return await super().saveToOutbox(notificationId, requestObject, retryCount, nextRetryAt)