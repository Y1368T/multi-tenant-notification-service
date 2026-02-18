from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel

from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import (
    NotifiationResponsePerRecipient,
    NotificationResponse,
    ProviderTestResponse,
)
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload

if TYPE_CHECKING:
    from notification_service.infrastructure.services.webhook_client import WebhookClient

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

    def __init__(self, uow: IUnitOfWork, webhook_client: "WebhookClient" = None) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)
        self.uow = uow
        self.webhook_client = webhook_client

    async def _send_callback(
        self,
        callback_url: Optional[str],
        callback_headers: Optional[Dict[str, str]],
        idempotency_key: str,
        status: str,
        recipient: str,
        notification_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Send callback to the provided URL."""
        if not callback_url:
            return
        
        if not self.webhook_client:
            logger.warning("WebhookClient not configured, skipping callback")
            return
        
        try:
            payload = NotificationCallbackPayload(
                idempotencyKey=idempotency_key,
                status=status,
                channel="sms",
                recipient=recipient,
                timestamp=datetime.utcnow(),
                notificationId=notification_id,
                errorMessage=error_message
            )
            
            logger.info(f"Sending callback to {callback_url} for {recipient}: status={status}")
            
            asyncio.create_task(
                self.webhook_client.send_callback(
                    callback_url=callback_url,
                    payload=payload,
                    headers=callback_headers,
                    max_retries=3,
                    base_delay=1.0
                )
            )
        except Exception as e:
            logger.error(f"Error sending callback to {callback_url}: {e}", exc_info=True)

    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        """
        Test Jasmin configuration.

        - For HTTP mode: perform a lightweight GET on baseUrl.
        - For SMPP mode: currently a configuration validation only (no network dial).
        """
        try:
            
            http_conf = JasminHTTPConfig.fromDict(config or {})
            
            if not http_conf.baseUrl or not http_conf.username or not http_conf.password:
                    return ProviderTestResponse(
                        success=False,
                        message="baseUrl, username and password are required for Jasmin HTTP configuration",
                    )
            credentials = f"{http_conf.username}:{http_conf.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_credentials}",
            }
            payload = {
                "to": address,
                "content": "Jasmin SMS gateway test message",
                "from": http_conf.sender or "",  # Use sender if available
            }
            response= await self.client.post(
                    http_conf.baseUrl,
                    content=json.dumps(payload),
                    headers=headers,
                    timeout=http_conf.timeoutSeconds or 10,
                )
            response.raise_for_status()
            try:
                    body = response.json()
            except Exception:  # pragma: no cover - non-json body
                    body = {"raw": response.text}

                # Parse Jasmin HTTP response for success/failure
                # Success: {'data': 'Success "503f7101-3bb8-4966-992c-1bd3ff8d2ea2'}
                # Failure: {'message': 'Error "Authentication failure for username:unified'}
            if "data" in body and isinstance(body["data"], str) and body["data"].startswith("Success"):
                    
               logger.info(f"Jasmin HTTP SMS sent successfully to {address}, response: {body}")
               
            else:
                logger.error(f"Failed to send test SMS via Jasmin HTTP to {address}, response: {body}")
                return ProviderTestResponse(success=False, message="Failed to send test SMS",)
                
            return ProviderTestResponse(success=True, message="Jasmin SMS gateway reachable")
        except Exception as exc:  # pragma: no cover - network/config errors
            logger.error(f"Exception during Jasmin SMS test: {exc}")
            return ProviderTestResponse(success=False, message=f"Exception during test: {str(exc)}")

    
    async def send(
         self,
        requestObject: NotificationRequest,
        tenantConfig: TenantSMSConfiguration,
        messageToSend: str,
        templateId: UUID,
        saveToOutbox: bool = True
    ) -> NotificationResponse:
        """Send SMS using Jasmin HTTP API.
        
        Args:
            saveToOutbox: If True, save failed messages to outbox for retry (fire-and-forget mode).
                         If False, just return failure (immediate mode, caller handles retry).
        """
        http_conf = JasminHTTPConfig.fromDict(tenantConfig.config or {})
        recipients: List[str] = [recipient.address for recipient in requestObject.recipients]
        notificationResponsePerRecipient: List[NotifiationResponsePerRecipient] = []
        if not recipients:
            return NotificationResponse(
                success=False,
                errorMessage="No recipients provided",
            )
        elif not http_conf.baseUrl or not http_conf.username or not http_conf.password:
            return NotificationResponse(
                success=False,
                errorMessage="Invalid Jasmin HTTP configuration: baseUrl, username and password are required",
            )

        
        credentials = f"{http_conf.username}:{http_conf.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_credentials}",
        }
        isAllSent:bool=False
        for to in recipients:
            payload = {
                "to": to,
                "hex_content": messageToSend.encode("utf-16-be").hex(),  # Encode to UCS2 hex for Unicode/Amharic
                "from": http_conf.sender or "",
                "coding": 8,  # UCS2 encoding for Unicode
            }
            try:
                logger.info(f"Sending SMS via Jasmin HTTP to {to}")
                response = await self.client.post(
                    http_conf.baseUrl,
                    content=json.dumps(payload),
                    headers=headers,
                    timeout=http_conf.timeoutSeconds or 10,
                )
                response.raise_for_status()
                # Jasmin returns JSON by default
                try:
                    body = response.json()
                except Exception:  # pragma: no cover - non-json body
                    body = {"raw": response.text}

                # Parse Jasmin HTTP response for success/failure
                # Success: {'data': 'Success "503f7101-3bb8-4966-992c-1bd3ff8d2ea2'}
                # Failure: {'message': 'Error "Authentication failure for username:unified'}
                if "data" in body and isinstance(body["data"], str) and body["data"].startswith("Success"):
                    
                    logger.info(f"Jasmin HTTP SMS sent successfully to {to}, response: {body}")
                    
                    smsnotification=SMSNotification(
                        id=uuid4(),
                        recipientNumber=to,
                        messageContent=messageToSend,
                        templateId=templateId,
                        status="sent",
                        idempotencyKey=requestObject.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.uow.smsNotifications.add(smsnotification)
                    await self.uow.commit()
                    notifcationResponse=NotifiationResponsePerRecipient(
                        notificationId=str(smsnotification.id),
                        status="sent",
                        recipient=to,
                        createdAt=smsnotification.createdAt,
                        deliveredAt=smsnotification.createdAt,
                        success=True,
                        message="SMS sent successfully"
                    )
                    notificationResponsePerRecipient.append(notifcationResponse)
                    isAllSent = True
                    
                    # Send callback on success (if callbackUrl provided)
                    await self._send_callback(
                        callback_url=requestObject.callbackUrl,
                        callback_headers=requestObject.callbackHeaders,
                        idempotency_key=requestObject.idempotencyKey,
                        status="sent",
                        recipient=to,
                        notification_id=str(smsnotification.id)
                    )
                elif "message" in body and isinstance(body["message"], str) and body["message"].startswith("Error"):
                    error_msg = body.get("message", body["message"])
                    # Only save to outbox if saveToOutbox is True (fire-and-forget mode)
                    if saveToOutbox:
                        #check if smsoutbox exist by the idempotency key and recipient number
                        existingOutbox = await self.uow.smsOutboxes.where(
                            lambda x: x.idempotencyKey == requestObject.idempotencyKey and x.recipientNumber == to
                        )
                        if existingOutbox:
                            logger.info(f"SMS outbox already exists for idempotencyKey {requestObject.idempotencyKey} and recipient {to}, skipping creation.")
                            existingOutbox.updatedAt = datetime.utcnow()
                            existingOutbox.lastErrorMessage = error_msg
                            existingOutbox.lastRetryAt = datetime.utcnow()
                            existingOutbox.providerAttempted = "JasminHTTP"
                            existingOutbox.status="failed"
                            await self.uow.smsOutboxes.update(existingOutbox)
                            await self.uow.commit()
                            notifcationResponse=NotifiationResponsePerRecipient(
                                notificationId=str(existingOutbox.id),
                                status=existingOutbox.status,
                                recipient=to,
                                createdAt=existingOutbox.createdAt,
                                success=False,
                                message="SMS outbox already exists, skipping creation",
                                errorMessage=error_msg,
                            )
                            notificationResponsePerRecipient.append(notifcationResponse)
                            isAllSent = False
                            continue  #skip to next recipient
                        else:
                            smsOutBox=SMSOutbox(
                                id=uuid4(),
                                recipientNumber=to,
                                messageContent=messageToSend,
                                idempotencyKey=requestObject.idempotencyKey,
                                templateId=templateId,
                                retryCount=0,
                                status="failed",
                                lastErrorMessage=error_msg,
                                providerAttempted="jasmin",
                                callbackUrl=requestObject.callbackUrl,
                                callbackHeaders=requestObject.callbackHeaders,
                                createdAt=datetime.utcnow(),
                                updatedAt=datetime.utcnow()
                            )
                            await self.uow.smsOutboxes.add(smsOutBox)
                            await self.uow.commit()
                            logger.error(f"Failed to send SMS via Jasmin HTTP to {to}, saved to outbox: {body}")
                            notifcationResponse=NotifiationResponsePerRecipient(
                                notificationId=str(smsOutBox.id),
                                status="failed",
                                recipient=to,
                                createdAt=smsOutBox.createdAt,
                                success=False,
                                message="Saved to outbox for retrying later",
                                errorMessage=error_msg,
                            )
                            notificationResponsePerRecipient.append(notifcationResponse)
                            isAllSent = False
                    else:
                        # Immediate mode - just return failure, caller handles retry
                        logger.error(f"Failed to send SMS via Jasmin HTTP to {to}: {error_msg}")
                        notifcationResponse=NotifiationResponsePerRecipient(
                            notificationId=None,
                            status="failed",
                            recipient=to,
                            createdAt=datetime.utcnow(),
                            success=False,
                            message="Failed to send SMS",
                            errorMessage=error_msg,
                        )
                        notificationResponsePerRecipient.append(notifcationResponse)
                        isAllSent = False
            except Exception as exc:  
                    logger.error(f"Error sending SMS via Jasmin HTTP to {to}: {exc}")
                    
                    # Only save to outbox if saveToOutbox is True (fire-and-forget mode)
                    if saveToOutbox:
                        smsOutBox=SMSOutbox(
                            id=uuid4(),
                            recipientNumber=to,
                            messageContent=messageToSend,
                            idempotencyKey=requestObject.idempotencyKey,
                            templateId=templateId,
                            retryCount=0,
                            status="failed",
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow(),
                            lastErrorMessage=str(exc),
                            lastRetryAt=datetime.utcnow(),
                            providerAttempted="jasmin",
                            callbackUrl=requestObject.callbackUrl,
                            callbackHeaders=requestObject.callbackHeaders,
                        )
                        await self.uow.smsOutboxes.add(smsOutBox)
                        await self.uow.commit()
                        notifcationResponse=NotifiationResponsePerRecipient(
                            notificationId=str(smsOutBox.id),
                            status="failed",
                            recipient=to,
                            createdAt=smsOutBox.createdAt,
                            success=False,
                            message="Saved to outbox for retrying later",
                            errorMessage=str(exc),
                        )
                    else:
                        # Immediate mode - just return failure, caller handles retry
                        notifcationResponse=NotifiationResponsePerRecipient(
                            notificationId=None,
                            status="failed",
                            recipient=to,
                            createdAt=datetime.utcnow(),
                            success=False,
                            message="Failed to send SMS",
                            errorMessage=str(exc),
                        )
                    notificationResponsePerRecipient.append(notifcationResponse)
                    isAllSent = False

        

        return NotificationResponse(
            
            channel="SMS",
            tenantId=str(tenantConfig.tenantId),
            success=isAllSent,
            message="Processing completed" if isAllSent else "Some messages failed to send",
            recipientResponse=notificationResponsePerRecipient
        )

    async def send_raw(
        self,
        recipient: str,
        message: str,
        tenantConfig: TenantSMSConfiguration
    ) -> tuple[bool, Optional[str]]:
        """
        Send a raw SMS message (used for outbox retry).
        
        Args:
            recipient: Phone number to send to
            message: Already-rendered message content
            tenantConfig: Tenant SMS configuration with provider credentials
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            http_conf = JasminHTTPConfig.fromDict(tenantConfig.config or {})
            
            if not http_conf.baseUrl or not http_conf.username or not http_conf.password:
                return (False, "Invalid Jasmin HTTP configuration: baseUrl, username and password are required")
            
            credentials = f"{http_conf.username}:{http_conf.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {encoded_credentials}",
            }
            
            payload = {
                "to": recipient,
                "hex_content": message.encode("utf-16-be").hex(),  # Encode to UCS2 hex for Unicode/Amharic
                "from": http_conf.sender or "",
                "coding": 8,  # UCS2 encoding for Unicode
            }
            
            response = await self.client.post(
                http_conf.baseUrl,
                content=json.dumps(payload),
                headers=headers,
                timeout=http_conf.timeoutSeconds or 10,
            )
            response.raise_for_status()
            
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text}
            
            if "data" in body and isinstance(body["data"], str) and body["data"].startswith("Success"):
                logger.info(f"SMS sent successfully to {recipient} via Jasmin HTTP (retry)")
                return (True, None)
            else:
                error_msg = body.get("message", str(body))
                logger.error(f"Failed to send SMS to {recipient} via Jasmin HTTP: {error_msg}")
                return (False, error_msg)
                
        except Exception as e:
            logger.error(f"Exception sending SMS to {recipient} via Jasmin HTTP: {e}")
            return (False, str(e))
    