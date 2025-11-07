from typing import Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from notification_service.domain.entities.tenant.tenant_sms_configuration import TenantSMSConfiguration
from notification_service.Infrastructure.providers.sms.ethiotelecom_shortcode import EthioTelecomConfiguration
from notification_service.Infrastructure.providers.sms.kifiya_sms_gateway import KifiyaSMSConfig


class TenantSMSConfigurationRequestDto(BaseModel):
    tenant_id: UUID
    provider_name: str
    priority: str
    is_active: bool = True
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500
    rate_limit_per_day: int = 5000
    config: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "provider_name": "EthioTelecomShortcode",
                "priority": 1,
                "is_active": True,
                "rate_limit_per_minute": 30,
                "rate_limit_per_hour": 500,
                "rate_limit_per_day": 5000,
                "config": {
                    "tokenId": "your_api_key",
                    "url": "your_kifiya_url",
                }
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TenantSMSConfigurationRequestDto":
        return cls(
            tenant_id=data["tenant_id"],
            provider_name=data["provider_name"],
            priority=data.get("priority", 1),
            is_active=data.get("is_active", True),
            rate_limit_per_minute=data.get("rate_limit_per_minute", 30),
            rate_limit_per_hour=data.get("rate_limit_per_hour", 500),
            rate_limit_per_day=data.get("rate_limit_per_day", 5000),
            config=data.get("config", {}),
        )
    
    def toEntity(self) -> TenantSMSConfiguration:
        return TenantSMSConfiguration(
            id=uuid4(),
            tenant_id=self.tenant_id,
            provider_name=self.provider_name,
            priroty=self.priority,
            is_active=self.is_active,
            rate_limit_per_minute=self.rate_limit_per_minute,
            rate_limit_per_hour=self.rate_limit_per_hour,
            rate_limit_per_day=self.rate_limit_per_day,
            config=self.config.to_dict() if hasattr(self.config, 'to_dict') else self.config,
        )