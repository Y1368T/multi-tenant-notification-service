from datetime import datetime
from typing import Any, Dict, Optional
from notification_service.domain.interfaces.iprovider_service import IProviderService
import smtplib

class SmtpEmailSender(IProviderService):
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, from_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email

    

    async def send(
        self,
        request_object: Dict[str, Any],
        notification_id: str
    ) -> Dict[str, Any]:
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                
                message = f"Subject: {request_object['subject']}\n\n{request_object['body']}"
                server.sendmail(
                    request_object['from'],
                    request_object['to'],
                    message
                )
                
            return {
                "success": True,
                "provider_message_id": notification_id,
                "status": "sent",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "provider_message_id": notification_id,
                "status": "failed",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def callback(
        self,
        provider_callback: Dict[str, Any]
    ) -> Dict[str, Any]:
        # SMTP doesn't provide delivery callbacks, so we return a basic response
        return {
            "notification_id": provider_callback.get("notification_id"),
            "status": "delivered",
            "delivered_at": datetime.now().isoformat(),
            "error_message": None
        }

    async def save_to_outbox(
        self,
        notification_id: str,
        request_object: Dict[str, Any],
        retry_count: int = 0,
        next_retry_at: Optional[datetime] = None
    ) -> None:
        # Implementation would depend on your outbox storage mechanism
        # This is a placeholder that would typically save to database
        pass