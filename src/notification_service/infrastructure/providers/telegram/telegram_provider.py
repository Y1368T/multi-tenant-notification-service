import asyncio
import logging
import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel

from notification_service.domain.interfaces.iprovider_service import IProviderService
from notification_service.domain.interfaces.iunit_of_work import IUnitOfWork
from notification_service.domain.value_objects.notification_request import NotificationRequest
from notification_service.domain.value_objects.notification_response import (
    NotifiationResponsePerRecipient,
    NotificationResponse,
    ProviderTestResponse,
)
from notification_service.adapters.inbound.dto.notification_callback import NotificationCallbackPayload
from notification_service.infrastructure.services.webhook_client import WebhookClient
from notification_service.domain.entities.tenant_telegram_configuration import TenantTelegramConfiguration

logger = logging.getLogger(__name__)
TELEGRAM_API_BASE_URL = "https://api.telegram.org"


class TelegramConfig(BaseModel):
    botToken: str
    parseMode: str = ""

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "TelegramConfig":
        bot_token = data.get("botToken") or data.get("bot_token") or ""
        return cls(
            botToken=bot_token,
            parseMode=data.get("parseMode") or data.get("parse_mode", "")
        )

    def toDict(self) -> Dict[str, Any]:
        return {
            "botToken": self.botToken,
            "parseMode": self.parseMode
        }

class TelegramProvider(IProviderService):
    def __init__(self, uow: IUnitOfWork, webhook_client: WebhookClient):
        self._uow = uow
        self.client = httpx.AsyncClient(timeout=30.0)
        self.webhook_client = webhook_client

    def _send_url(self, bot_token: str) -> str:
        return f"{TELEGRAM_API_BASE_URL}/bot{bot_token}/sendMessage"

    async def _send_callback(
        self,
        callback_url: str,
        callback_headers: Dict[str, str],
        idempotency_key: str,
        status: str,
        recipient: str,
        notification_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        if not callback_url or not self.webhook_client:
            return
        try:
            payload = NotificationCallbackPayload(
                idempotency_key=idempotency_key,
                status=status,
                channel="telegram",
                recipient=recipient,
                timestamp=datetime.utcnow(),
                notificationId=notification_id,
                errorMessage=error_message,
            )
            asyncio.create_task(
                self.webhook_client.send_callback(
                    callback_url=callback_url,
                    payload=payload,
                    headers=callback_headers,
                    max_retries=3,
                    base_delay=1.0,
                )
            )
        except Exception as e:
            logger.error(
                f"Error in sending callback: {e}, "
                f"callback_url: {callback_url}, "
                f"callback_headers: {callback_headers}, "
                f"idempotency_key: {idempotency_key}, "
                f"status: {status}, "
                f"recipient: {recipient}, "
                f"notification_id: {notification_id}, "
                f"error_message: {error_message}"
            )
    # IProviderService Interface Methods
    async def test(self, config: Dict[str, Any], address: str) -> ProviderTestResponse:
        try:
            tg_config = TelegramConfig.fromDict(config)
            url = self._send_url(tg_config.botToken)
            payload = {
                "chat_id": address,
                "text": "Test message from notification service",
                "parse_mode": tg_config.parseMode or "HTML",
            }
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return ProviderTestResponse(
                    success=True,
                    message="Test message sent successfully"
                )
            else:
                return ProviderTestResponse(
                    success=False,
                    message=data.get("description", "Unknown error") or "Failed to send test message"
                )
        except Exception as e:
            logger.error(f"Error in sending test message: {e}")
            return ProviderTestResponse(
                success=False,
                message=f"Failed to send test message: {e}"
            )
    
    async def send(
        self,
        requestObject: NotificationRequest,
        tenantConfig: TenantTelegramConfiguration,
        messageToSend: str,
        templateId: UUID,
        saveToOutbox: bool = True,
    ) -> NotificationResponse:
        try:
            tg_config = TelegramConfig.fromDict(tenantConfig.config)
            chat_id = requestObject.recipient.address

            if not chat_id:
                return NotificationResponse(
                    success=False,
                    message="No recipient chat_id provided"
                )
            
            url = self._send_url(tg_config.botToken)
            payload = {
                "chat_id": chat_id,
                "text": messageToSend,
                "parse_mode": tg_config.parseMode or "HTML",
            }

            logger.info(f"Sending telegram message to {chat_id} with payload: {payload}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                message_id = data.get("result", {}).get("message_id")
                logger.info(f"Telegram message sent successfully with message ID: {message_id}")
                
                await self._send_callback(
                    callback_url=requestObject.callbackUrl,
                    callback_headers=requestObject.callbackHeaders,
                    idempotency_key=requestObject.idempotencyKey,
                    status="sent",
                    recipient=requestObject.recipient.address,
                    notification_id=requestObject.idempotencyKey,
                )

                response = NotificationResponse(
                    success=True,
                    message="Telegram message sent successfully",
                    recipientResponse=[
                        NotifiationResponsePerRecipient(
                            notificationId=message_id,
                            status="sent",
                            recipient=chat_id,
                            createdAt=datetime.now(UTC),
                            success=True,
                            message="Telegram message sent successfully",
                        )
                    ],
                )
            else:
                logger.error(f"Failed to send telegram message to {chat_id} with error: {data.get('description')}")
                await self._send_callback(
                    callback_url=requestObject.callbackUrl,
                    callback_headers=requestObject.callbackHeaders,
                    idempotency_key=requestObject.idempotencyKey,
                    status="failed",
                    recipient=requestObject.recipient.address,
                    notification_id=requestObject.idempotencyKey,
                    error_message=data.get("description", "Failed to send telegram message")
                )
                return NotificationResponse(
                    success=False,
                    errorMessage=data.get("description", "Failed to send telegram message"),
                    recipientResponse=[
                        NotifiationResponsePerRecipient(
                            notificationId=None,
                            status="failed",
                            recipient=chat_id,
                            createdAt=datetime.now(UTC),
                            success=False,
                            errorMessage=data.get("description", "Failed to send telegram message"),
                        )
                    ],
                )
        except Exception as e:
            error_message = f"{type(e).__name__} : {str(e)}"
            logger.error(f"Error in sending telegram message: {error_message}", exc_info=True)
            return NotificationResponse(
                success=False,
                errorMessage=error_message,
                recipientResponse=[
                    NotifiationResponsePerRecipient(
                        notificationId=None,
                        status="failed",
                        recipient=chat_id,
                        createdAt=datetime.now(UTC),
                        success=False,
                        errorMessage=error_message,
                    )
                ],
            )
    async def send_raw(
        self,
        recipient: str,
        message: str,
        tenantConfig: Any,
    ) -> tuple[bool, Optional[str]]:
        try:
            tg_config = TelegramConfig.fromDict(tenantConfig.config)
            url = self._send_url(tg_config.botToken)
            payload = {
                "chat_id": recipient,
                "text": message,
                "parse_mode": tg_config.parseMode or "HTML",
            }
            logger.info(f"Sending telegram message to {recipient} with payload: {payload}")
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                message_id = data.get("result", {}).get("message_id")
                logger.info(f"Telegram message sent successfully with message ID: {message_id}")
                return (True, message_id)
            else:
                logger.error(f"Failed to send telegram message to {recipient} with error: {data.get('description')}")
                return (False, data.get("description", "Failed to send telegram message"))
        except Exception as e:
            error_message = f"{type(e).__name__} : {str(e)}"
            logger.error(f"Error in sending telegram message: {error_message}", exc_info=True)
            return (False, error_message)