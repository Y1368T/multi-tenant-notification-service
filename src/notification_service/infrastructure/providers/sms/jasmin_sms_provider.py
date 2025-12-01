from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional
import asyncio
import logging
from datetime import datetime
from uuid import UUID, uuid4

import httpx
from notification_service.domain.entities.sms.sms_notification import SMSNotification
from notification_service.domain.entities.sms.sms_outbox import SMSOutbox
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from pydantic import BaseModel

from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import (
    NotifiationResponsePerRecipient,
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

    def __init__(self,uow: IUnitOfWork) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)
        self.uow = uow

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
            await self.client.post(
                    http_conf.baseUrl,
                    content=json.dumps(payload),
                    headers=headers,
                    timeout=http_conf.timeoutSeconds or 10,
                )
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
    ) -> NotificationResponse:
        """Send SMS using Jasmin HTTP API."""
        http_conf = JasminHTTPConfig.fromDict(tenantConfig.config or {})
        recipients: List[str] = [recipient.address for recipient in requestObject.recipients]
        notificationResponsePerRecipient: Optional[List[NotifiationResponsePerRecipient]]=None
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
                "content": messageToSend,
                "from": http_conf.sender or "",  # Use sender if available
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
                        notificationId=uuid4(),
                        tenantId=tenantConfig.tenantId,
                        recipientNumber=to,
                        messageContent=messageToSend,
                        templateId=templateId,
                        status="sent",
                        idempotencyKey=requestObject.idempotencyKey,
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.unitOfWork.smsNotificationRepository.add(smsnotification)
                    await self.unitOfWork.commit()
                    notifcationResponse=NotifiationResponsePerRecipient(
                        notificationId=str(smsnotification.id),
                        status="sent",
                        recipientResponse=to,
                        createdAt=smsnotification.createdAt,
                        updatedAt=smsnotification.updatedAt,
                        success=True,
                        message="SMS sent successfully"
                    )
                    notificationResponsePerRecipient.append(notifcationResponse)
                    isAllSent = True
                elif "message" in body and isinstance(body["message"], str) and body["message"].startswith("Error"):
                    smsOutBox=SMSOutbox(
                        id=uuid4(),
                        recipientNumber=to,
                        messageContent=messageToSend,
                        idempotencyKey=requestObject.idempotencyKey,
                        templateId=templateId,
                        retryCount=0,
                        status="failed",
                        createdAt=datetime.utcnow(),
                        updatedAt=datetime.utcnow()
                    )
                    await self.unitOfWork.smsOutboxRepository.add(smsOutBox)
                    await self.unitOfWork.commit()
                    logger.error(f"Failed to send SMS via Jasmin HTTP to {to}, response: {body}")
                    notifcationResponse=NotifiationResponsePerRecipient(
                        notificationId=str(smsOutBox.id),
                        status="failed",
                        recipientResponse=to,
                        createdAt=smsOutBox.createdAt,
                        updatedAt=smsOutBox.updatedAt,
                        success=False,
                        message="Saved to outbox for retrying later",
                        errorMessage=body.get("message", body["message"]),
                    )
                    notificationResponsePerRecipient.append(notifcationResponse)
                    isAllSent = False
            except Exception as exc:  
                logger.error(f"Error sending SMS via Jasmin HTTP to {to}: {exc}")

        

        return NotificationResponse(
            
            channel="SMS",
            tenantId=str(tenantConfig.tenantId),
            success=isAllSent,
            message="Processing completed" if isAllSent else "Some messages failed to send",
            recipientResponse=notificationResponsePerRecipient
        )

   
    