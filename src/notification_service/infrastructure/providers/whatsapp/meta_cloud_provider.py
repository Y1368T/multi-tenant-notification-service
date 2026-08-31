from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel

from notification_service.domain.entities.whatsapp.whatsapp_notification import WhatsAppNotification
from notification_service.domain.entities.whatsapp.whatsapp_outbox import WhatsAppOutbox
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.entities.tenant.tenant_whatsapp_configuration import TenantWhatsAppConfiguration
from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import (
    NotifiationResponsePerRecipient,
    NotificationResponse,
    ProviderTestResponse,
)
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload

from notification_service.infrastructure.services.webhook_client import WebhookClient

logger = logging.getLogger(__name__)


class MetaCloudConfig(BaseModel):
    """Configuration for the WhatsApp Meta Cloud API."""

    accessToken: str
    phoneNumberId: str
    businessAccountId: Optional[str] = None
    apiVersion: str = "v20.0"
    timeoutSeconds: Optional[int] = 10

    class Config:
        from_attributes = True

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "MetaCloudConfig":
        return cls(
            accessToken=data.get("accessToken", ""),
            phoneNumberId=data.get("phoneNumberId", ""),
            businessAccountId=data.get("businessAccountId"),
            apiVersion=data.get("apiVersion", "v20.0"),
            timeoutSeconds=int(data.get("timeoutSeconds", 10)) if data.get("timeoutSeconds") is not None else 10,
        )

    def messagesUrl(self) -> str:
        return f"https://graph.facebook.com/{self.apiVersion}/{self.phoneNumberId}/messages"

    def phoneNumberUrl(self) -> str:
        return f"https://graph.facebook.com/{self.apiVersion}/{self.phoneNumberId}"


class WhatsAppMetaCloudProvider(IProviderService):
    """
    WhatsApp provider backed by Meta's WhatsApp Cloud API.

    tenantConfig.config MUST contain "accessToken" and "phoneNumberId".
    """

    def __init__(self, uow: IUnitOfWork, webhook_client: WebhookClient) -> None:
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
                channel="whatsapp",
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
        Test Meta Cloud API configuration by fetching the phone number resource.
        This validates the access token and phone number ID without sending a message.
        """
        try:
            cfg = MetaCloudConfig.fromDict(config or {})

            if not cfg.accessToken or not cfg.phoneNumberId:
                return ProviderTestResponse(
                    success=False,
                    message="accessToken and phoneNumberId are required for WhatsApp Meta Cloud configuration",
                )

            headers = {"Authorization": f"Bearer {cfg.accessToken}"}
            response = await self.client.get(
                cfg.phoneNumberUrl(),
                headers=headers,
                timeout=cfg.timeoutSeconds or 10,
            )

            if response.status_code == 200:
                logger.info(f"WhatsApp Meta Cloud config OK for phoneNumberId {cfg.phoneNumberId}")
                return ProviderTestResponse(success=True, message="WhatsApp Meta Cloud API reachable")
            else:
                try:
                    body = response.json()
                except Exception:
                    body = {"raw": response.text}
                logger.error(f"WhatsApp Meta Cloud test failed for {cfg.phoneNumberId}: {body}")
                return ProviderTestResponse(success=False, message=f"Meta Cloud API error: {body}")
        except Exception as exc:
            logger.error(f"Exception during WhatsApp Meta Cloud test: {exc}")
            return ProviderTestResponse(success=False, message=f"Exception during test: {str(exc)}")

    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantWhatsAppConfiguration,
        messageToSend: str,
        templateId: UUID,
        saveToOutbox: bool = True
    ) -> NotificationResponse:
        """Send a WhatsApp text message using the Meta Cloud API.

        Args:
            saveToOutbox: If True, save failed messages to outbox for retry (fire-and-forget mode).
                         If False, just return failure (immediate mode, caller handles retry).
        """
        cfg = MetaCloudConfig.fromDict(tenantConfig.config or {})
        recipient: str = requestObject.recipient.address
        notificationResponsePerRecipient: List[NotifiationResponsePerRecipient] = []

        if not recipient:
            return NotificationResponse(
                success=False,
                errorMessage="No recipient provided",
            )
        elif not cfg.accessToken or not cfg.phoneNumberId:
            return NotificationResponse(
                success=False,
                errorMessage="Invalid WhatsApp Meta Cloud configuration: accessToken and phoneNumberId are required",
            )

        headers = {
            "Authorization": f"Bearer {cfg.accessToken}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": messageToSend},
        }
        isAllSent: bool = False

        try:
            logger.info(f"Sending WhatsApp message via Meta Cloud API to {recipient}")
            response = await self.client.post(
                cfg.messagesUrl(),
                json=payload,
                headers=headers,
                timeout=cfg.timeoutSeconds or 10,
            )

            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text}

            # Meta Cloud API success shape: {"messages": [{"id": "wamid...."}], ...}
            # Meta Cloud API failure shape: {"error": {"message": "...", "code": ..., ...}}
            if response.status_code == 200 and "messages" in body and body["messages"]:
                providerMessageId = body["messages"][0].get("id")
                logger.info(f"WhatsApp message sent successfully to {recipient}, id: {providerMessageId}")

                whatsappNotification = WhatsAppNotification(
                    id=uuid4(),
                    recipientNumber=recipient,
                    messageContent=messageToSend,
                    templateId=templateId,
                    status="sent",
                    idempotencyKey=requestObject.idempotencyKey,
                    createdAt=datetime.utcnow(),
                    updatedAt=datetime.utcnow()
                )
                await self.uow.whatsAppNotifications.add(whatsappNotification)
                await self.uow.commit()

                notifcationResponse = NotifiationResponsePerRecipient(
                    notificationId=str(whatsappNotification.id),
                    status="sent",
                    recipient=recipient,
                    createdAt=whatsappNotification.createdAt,
                    deliveredAt=whatsappNotification.createdAt,
                    success=True,
                    message="WhatsApp message sent successfully"
                )
                notificationResponsePerRecipient.append(notifcationResponse)
                isAllSent = True

                await self._send_callback(
                    callback_url=requestObject.callbackUrl,
                    callback_headers=requestObject.callbackHeaders,
                    idempotency_key=requestObject.idempotencyKey,
                    status="sent",
                    recipient=recipient,
                    notification_id=str(whatsappNotification.id)
                )
            else:
                error_body = body.get("error", {})
                error_msg = error_body.get("message") if isinstance(error_body, dict) else str(body)
                error_msg = error_msg or f"WhatsApp send failed with status {response.status_code}"

                if saveToOutbox:
                    existingOutbox = await self.uow.whatsAppOutboxes.firstOrDefault(
                        lambda x: x.idempotencyKey == requestObject.idempotencyKey and x.recipientNumber == recipient
                    )
                    if existingOutbox:
                        logger.info(f"WhatsApp outbox already exists for idempotencyKey {requestObject.idempotencyKey} and recipient {recipient}, skipping creation.")
                        existingOutbox.updatedAt = datetime.utcnow()
                        existingOutbox.lastErrorMessage = error_msg
                        existingOutbox.lastRetryAt = datetime.utcnow()
                        existingOutbox.providerAttempted = "meta_cloud"
                        existingOutbox.status = "failed"
                        await self.uow.whatsAppOutboxes.update(existingOutbox)
                        await self.uow.commit()
                        notifcationResponse = NotifiationResponsePerRecipient(
                            notificationId=str(existingOutbox.id),
                            status=existingOutbox.status,
                            recipient=recipient,
                            createdAt=existingOutbox.createdAt,
                            success=False,
                            message="WhatsApp outbox already exists, skipping creation",
                            errorMessage=error_msg,
                        )
                        notificationResponsePerRecipient.append(notifcationResponse)
                        isAllSent = False
                    else:
                        whatsappOutbox = WhatsAppOutbox(
                            id=uuid4(),
                            recipientNumber=recipient,
                            messageContent=messageToSend,
                            idempotencyKey=requestObject.idempotencyKey,
                            templateId=templateId,
                            retryCount=0,
                            status="failed",
                            lastErrorMessage=error_msg,
                            providerAttempted="meta_cloud",
                            callbackUrl=requestObject.callbackUrl,
                            callbackHeaders=requestObject.callbackHeaders,
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow()
                        )
                        await self.uow.whatsAppOutboxes.add(whatsappOutbox)
                        await self.uow.commit()
                        logger.error(f"Failed to send WhatsApp message to {recipient}, saved to outbox: {body}")
                        notifcationResponse = NotifiationResponsePerRecipient(
                            notificationId=str(whatsappOutbox.id),
                            status="failed",
                            recipient=recipient,
                            createdAt=whatsappOutbox.createdAt,
                            success=False,
                            message="Saved to outbox for retrying later",
                            errorMessage=error_msg,
                        )
                        notificationResponsePerRecipient.append(notifcationResponse)
                        isAllSent = False
                else:
                    logger.error(f"Failed to send WhatsApp message to {recipient}: {error_msg}")
                    notifcationResponse = NotifiationResponsePerRecipient(
                        notificationId=None,
                        status="failed",
                        recipient=recipient,
                        createdAt=datetime.utcnow(),
                        success=False,
                        message="Failed to send WhatsApp message",
                        errorMessage=error_msg,
                    )
                    notificationResponsePerRecipient.append(notifcationResponse)
                    isAllSent = False
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {str(exc) or 'No error details (WhatsApp Meta Cloud)'}"
            logger.error(f"Error sending WhatsApp message to {recipient}: {error_message}", exc_info=True)

            if saveToOutbox:
                whatsappOutbox = WhatsAppOutbox(
                    id=uuid4(),
                    recipientNumber=recipient,
                    messageContent=messageToSend,
                    idempotencyKey=requestObject.idempotencyKey,
                    templateId=templateId,
                    retryCount=0,
                    status="failed",
                    createdAt=datetime.utcnow(),
                    updatedAt=datetime.utcnow(),
                    lastErrorMessage=error_message,
                    lastRetryAt=datetime.utcnow(),
                    providerAttempted="meta_cloud",
                    callbackUrl=requestObject.callbackUrl,
                    callbackHeaders=requestObject.callbackHeaders,
                )
                await self.uow.whatsAppOutboxes.add(whatsappOutbox)
                await self.uow.commit()
                notifcationResponse = NotifiationResponsePerRecipient(
                    notificationId=str(whatsappOutbox.id),
                    status="failed",
                    recipient=recipient,
                    createdAt=whatsappOutbox.createdAt,
                    success=False,
                    message="Saved to outbox for retrying later",
                    errorMessage=error_message,
                )
            else:
                notifcationResponse = NotifiationResponsePerRecipient(
                    notificationId=None,
                    status="failed",
                    recipient=recipient,
                    createdAt=datetime.utcnow(),
                    success=False,
                    message="Failed to send WhatsApp message",
                    errorMessage=error_message,
                )
            notificationResponsePerRecipient.append(notifcationResponse)
            isAllSent = False

        return NotificationResponse(
            channel="WHATSAPP",
            tenantId=str(tenantConfig.tenantId),
            success=isAllSent,
            message="Processing completed" if isAllSent else "Some messages failed to send",
            recipientResponse=notificationResponsePerRecipient
        )

    async def send_raw(
        self,
        recipient: str,
        message: str,
        tenantConfig: TenantWhatsAppConfiguration
    ) -> tuple[bool, Optional[str]]:
        """
        Send a raw WhatsApp message (used for outbox retry).

        Args:
            recipient: WhatsApp number to send to
            message: Already-rendered message content
            tenantConfig: Tenant WhatsApp configuration with provider credentials

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            cfg = MetaCloudConfig.fromDict(tenantConfig.config or {})

            if not cfg.accessToken or not cfg.phoneNumberId:
                return (False, "Invalid WhatsApp Meta Cloud configuration: accessToken and phoneNumberId are required")

            headers = {
                "Authorization": f"Bearer {cfg.accessToken}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": message},
            }

            response = await self.client.post(
                cfg.messagesUrl(),
                json=payload,
                headers=headers,
                timeout=cfg.timeoutSeconds or 10,
            )

            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text}

            if response.status_code == 200 and "messages" in body and body["messages"]:
                logger.info(f"WhatsApp message sent successfully to {recipient} via Meta Cloud API (retry)")
                return (True, None)
            else:
                error_body = body.get("error", {})
                error_msg = error_body.get("message") if isinstance(error_body, dict) else str(body)
                logger.error(f"Failed to send WhatsApp message to {recipient} via Meta Cloud API: {error_msg}")
                return (False, error_msg)

        except Exception as e:
            logger.error(f"Exception sending WhatsApp message to {recipient} via Meta Cloud API: {e}")
            return (False, str(e))
