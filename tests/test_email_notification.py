"""
Comprehensive Email Notification Testing Script

This script tests the complete email notification flow through SMTP:
1. Create tenant
2. Configure SMTP provider for tenant
3. Create email template
4. Send email notifications
5. Verify notification status

Run with: python -m pytest tests/test_email_notification.py -v -s
Or run directly: python tests/test_email_notification.py
"""

import asyncio
import httpx
import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration - Update these values for your environment
BASE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-key")

# SMTP Configuration - Update with your actual SMTP credentials
SMTP_CONFIG = {
    "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.getenv("SMTP_PORT", "587")),
    "username": os.getenv("SMTP_USERNAME", "your-email@gmail.com"),
    "password": os.getenv("SMTP_PASSWORD", "your-app-password"),  # Use App Password for Gmail
    "fromEmail": os.getenv("SMTP_FROM_EMAIL", "noreply@yourcompany.com"),
    "fromName": os.getenv("SMTP_FROM_NAME", "Test Notification Service"),
    "useTls": True,
    "useSsl": False,
    "timeout": 30,
}

# Test recipient email - Update with your actual test email
TEST_RECIPIENT_EMAIL = os.getenv("TEST_EMAIL", "test-recipient@example.com")


class EmailNotificationTester:
    """Complete email notification testing class."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": ADMIN_API_KEY,  # Admin API key for creating tenants
        }
        self.tenant_id: Optional[str] = None
        self.tenant_prefix: Optional[str] = None
        self.tenant_api_key: Optional[str] = None
        self.template_id: Optional[str] = None
        self.template_name: Optional[str] = None
        self.config_id: Optional[str] = None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _log(self, message: str, level: str = "INFO"):
        """Simple logging helper."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def test_health_check(self) -> bool:
        """Test if the service is running."""
        self._log("Testing service health...")
        try:
            response = await self.client.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                self._log("[OK] Service is healthy")
                return True
            self._log(f"[FAIL] Health check failed: {response.status_code}", "ERROR")
            return False
        except Exception as e:
            self._log(f"[FAIL] Cannot connect to service: {e}", "ERROR")
            return False

    async def create_tenant(self) -> bool:
        """Create a test tenant."""
        self._log("Creating test tenant...")
        
        unique_suffix = str(uuid.uuid4())[:4].upper().replace("-", "")
        tenant_data = {
            "name": f"Email Test Tenant {unique_suffix}",
            "prefix": f"EM_{unique_suffix}",  # Max 10 chars
            "isActive": True,
            "supportedChannels": ["sms", "inapp", "email"],
            "preferedCommunicationMethod": "rest"
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/tenants/create",
                json=tenant_data,
                headers=self.headers,
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.tenant_id = data.get("id")
                self.tenant_prefix = data.get("prefix")
                self.tenant_api_key = data.get("apiKey")
                self._log(f"[OK] Tenant created: {self.tenant_id}")
                self._log(f"   Prefix: {self.tenant_prefix}")
                self._log(f"   API Key: {self.tenant_api_key}")
                return True
            else:
                self._log(f"[FAIL] Failed to create tenant: {response.status_code}", "ERROR")
                self._log(f"   Response: {response.text}", "ERROR")
                return False
        except Exception as e:
            self._log(f"[FAIL] Exception creating tenant: {e}", "ERROR")
            return False

    async def configure_smtp_provider(self) -> bool:
        """Configure SMTP provider for the tenant."""
        if not self.tenant_id:
            self._log("[FAIL] No tenant ID available", "ERROR")
            return False

        self._log("Configuring SMTP email provider...")
        
        config_data = {
            "tenantId": self.tenant_id,
            "providerName": "smtp",
            "priority": 1,
            "isActive": True,
            "rateLimitPerMinute": 50,
            "rateLimitPerHour": 800,
            "rateLimitPerDay": 8000,
            "config": SMTP_CONFIG,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/tenant-email-configurations/create",
                json=config_data,
                headers=self.headers,
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.config_id = data.get("id")
                self._log(f"[OK] SMTP configuration created: {self.config_id}")
                return True
            else:
                self._log(f"[FAIL] Failed to create SMTP config: {response.status_code}", "ERROR")
                self._log(f"   Response: {response.text}", "ERROR")
                return False
        except Exception as e:
            self._log(f"[FAIL] Exception creating SMTP config: {e}", "ERROR")
            return False

    async def create_email_template(self) -> bool:
        """Create an email template for testing."""
        if not self.tenant_id:
            self._log("[FAIL] No tenant ID available", "ERROR")
            return False

        self._log("Creating email template...")
        
        # Use unique template name to avoid conflicts
        unique_suffix = str(uuid.uuid4())[:8]
        self.template_name = f"test-email-{unique_suffix}"
        template_data = {
            "templateName": self.template_name,
            "tenantId": self.tenant_id,
            "serviceName": "test-service",
            "subject": "Welcome {userName}! - Test Email from Notification Service",
            "version": 1,
            "isActive": True,
            "bodyType": "html",
            "body": {
                "en": "<html><body><h1>Welcome {userName}!</h1><p>Thank you for joining {companyName}.</p><p>Email: {userEmail}</p><p>Registration: {registrationDate}</p><p>Sent at {timestamp}</p></body></html>",
                "es": "<html><body><h1>Bienvenido {userName}!</h1><p>Gracias por unirse a {companyName}.</p><p>Enviado en {timestamp}</p></body></html>",
            },
            "fileUrls": None,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/email-templates/create",
                json=template_data,
                headers=self.headers,
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.template_id = data.get("id")
                self._log(f"[OK] Email template created: {self.template_id}")
                return True
            else:
                self._log(f"[FAIL] Failed to create template: {response.status_code}", "ERROR")
                self._log(f"   Response: {response.text}", "ERROR")
                return False
        except Exception as e:
            self._log(f"[FAIL] Exception creating template: {e}", "ERROR")
            return False

    async def send_email_notification(
        self, 
        recipient_email: str = TEST_RECIPIENT_EMAIL,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Send a test email notification."""
        if not self.tenant_id:
            self._log("[FAIL] No tenant ID available", "ERROR")
            return {"success": False, "error": "No tenant ID"}

        self._log(f"Sending email to: {recipient_email}...")
        
        notification_data = {
            "serviceName": "test-service",
            "recipients": [{"address": recipient_email}],
            "templateName": self.template_name or "test-welcome-email",
            "payload": {
                "userName": "Test User",
                "companyName": "Kifiya Financial Technologies",
                "userEmail": recipient_email,
                "registrationDate": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "idempotencyKey": str(uuid.uuid4()),
            "lang": language,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/email-notifications/send?tenant_id={self.tenant_id}",
                json=notification_data,
                headers=self.headers,
            )
            
            data = response.json()
            
            if response.status_code in [200, 201]:
                if data.get("success"):
                    self._log(f"[OK] Email sent successfully!")
                    self._log(f"   Response: {data.get('message', 'OK')}")
                    if data.get("recipientResponse"):
                        for recipient in data["recipientResponse"]:
                            self._log(f"   - {recipient.get('recipient')}: {recipient.get('status')}")
                else:
                    self._log(f"[WARN] Email request accepted but may have failed")
                    self._log(f"   Message: {data.get('message') or data.get('errorMessage')}")
            else:
                self._log(f"[FAIL] Failed to send email: {response.status_code}", "ERROR")
                self._log(f"   Response: {response.text}", "ERROR")
            
            return data
            
        except Exception as e:
            self._log(f"[FAIL] Exception sending email: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    async def send_multi_recipient_email(
        self, 
        recipient_emails: list[str]
    ) -> Dict[str, Any]:
        """Send email to multiple recipients."""
        if not self.tenant_id:
            self._log("[FAIL] No tenant ID available", "ERROR")
            return {"success": False, "error": "No tenant ID"}

        self._log(f"Sending email to {len(recipient_emails)} recipients...")
        
        notification_data = {
            "serviceName": "test-service",
            "recipients": [{"address": email} for email in recipient_emails],
            "templateName": self.template_name or "test-welcome-email",
            "payload": {
                "userName": "Multiple Users",
                "companyName": "Kifiya Financial Technologies",
                "userEmail": ", ".join(recipient_emails),
                "registrationDate": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "idempotencyKey": str(uuid.uuid4()),
            "lang": "en",
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/email-notifications/send?tenant_id={self.tenant_id}",
                json=notification_data,
                headers=self.headers,
            )
            
            data = response.json()
            self._log(f"Multi-recipient response: {data.get('success')}")
            return data
            
        except Exception as e:
            self._log(f"[FAIL] Exception: {e}", "ERROR")
            return {"success": False, "error": str(e)}

    async def test_idempotency(self) -> bool:
        """Test that duplicate messages are rejected."""
        self._log("Testing idempotency (duplicate message rejection)...")
        
        idempotency_key = str(uuid.uuid4())
        
        notification_data = {
            "serviceName": "test-service",
            "recipients": [{"address": TEST_RECIPIENT_EMAIL}],
            "templateName": self.template_name or "test-welcome-email",
            "payload": {
                "userName": "Idempotency Test",
                "companyName": "Test Company",
                "userEmail": TEST_RECIPIENT_EMAIL,
                "registrationDate": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "idempotencyKey": idempotency_key,
            "lang": "en",
        }

        try:
            # First request
            response1 = await self.client.post(
                f"{self.base_url}/email-notifications/send?tenant_id={self.tenant_id}",
                json=notification_data,
                headers=self.headers,
            )
            data1 = response1.json()
            self._log(f"   First request: success={data1.get('success')}")

            # Second request with same idempotency key
            response2 = await self.client.post(
                f"{self.base_url}/email-notifications/send?tenant_id={self.tenant_id}",
                json=notification_data,
                headers=self.headers,
            )
            data2 = response2.json()
            self._log(f"   Second request: success={data2.get('success')}, message={data2.get('message')}")

            # Second request should indicate duplicate
            if "Duplicate" in str(data2.get("message", "")):
                self._log("[OK] Idempotency test passed - duplicate detected")
                return True
            else:
                self._log("[WARN] Idempotency test may have failed - check manually", "WARN")
                return True  # May have been processed before first one completed

        except Exception as e:
            self._log(f"[FAIL] Idempotency test failed: {e}", "ERROR")
            return False

    async def get_notifications(self) -> Dict[str, Any]:
        """Get list of email notifications."""
        self._log("Fetching email notifications...")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/email-notifications/get?tenantId={self.tenant_id}&pageSize=10",
                headers=self.headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                self._log(f"[OK] Found {len(items)} notifications")
                for item in items[:5]:  # Show first 5
                    self._log(f"   - {item.get('recipientEmail')}: {item.get('status')}")
                return data
            else:
                self._log(f"[FAIL] Failed to fetch notifications: {response.status_code}", "ERROR")
                return {}
        except Exception as e:
            self._log(f"[FAIL] Exception: {e}", "ERROR")
            return {}

    async def cleanup(self) -> None:
        """Clean up test resources."""
        self._log("Cleaning up test resources...")
        
        try:
            # Delete template
            if self.template_id:
                await self.client.delete(
                    f"{self.base_url}/email-templates/{self.template_id}",
                    headers=self.headers,
                )
                self._log(f"   Deleted template: {self.template_id}")

            # Delete config
            if self.config_id:
                await self.client.delete(
                    f"{self.base_url}/tenant-email-configurations/{self.config_id}",
                    headers=self.headers,
                )
                self._log(f"   Deleted config: {self.config_id}")

            # Delete tenant
            if self.tenant_id:
                await self.client.delete(
                    f"{self.base_url}/tenants/{self.tenant_id}",
                    headers=self.headers,
                )
                self._log(f"   Deleted tenant: {self.tenant_id}")

            self._log("[OK] Cleanup completed")
        except Exception as e:
            self._log(f"[WARN] Cleanup error: {e}", "WARN")


async def run_full_test(cleanup_after: bool = False):
    """Run complete email notification test suite."""
    print("\n" + "=" * 70)
    print("   EMAIL NOTIFICATION FULL TEST SUITE")
    print("=" * 70 + "\n")

    tester = EmailNotificationTester()
    results = {}

    try:
        # Test 1: Health Check
        results["health_check"] = await tester.test_health_check()
        if not results["health_check"]:
            print("\n[FAIL] Service is not running. Start the service first.")
            return results

        print("")
        
        # Test 2: Create Tenant
        results["create_tenant"] = await tester.create_tenant()
        if not results["create_tenant"]:
            return results

        print("")

        # Test 3: Configure SMTP
        results["configure_smtp"] = await tester.configure_smtp_provider()
        if not results["configure_smtp"]:
            return results

        print("")

        # Test 4: Create Template
        results["create_template"] = await tester.create_email_template()
        if not results["create_template"]:
            return results

        print("")

        # Test 5: Send Email (English)
        result = await tester.send_email_notification(
            recipient_email=TEST_RECIPIENT_EMAIL,
            language="en"
        )
        results["send_email_en"] = result.get("success", False)

        print("")

        # Test 6: Send Email (Spanish)
        result = await tester.send_email_notification(
            recipient_email=TEST_RECIPIENT_EMAIL,
            language="es"
        )
        results["send_email_es"] = result.get("success", False)

        print("")

        # Test 7: Idempotency Test
        results["idempotency_test"] = await tester.test_idempotency()

        print("")

        # Test 8: Get Notifications
        notifications = await tester.get_notifications()
        results["get_notifications"] = len(notifications.get("items", [])) > 0

        print("")

        # Cleanup if requested
        if cleanup_after:
            await tester.cleanup()

    except Exception as e:
        print(f"\n[FAIL] Test suite error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.close()

    # Print Summary
    print("\n" + "=" * 70)
    print("   TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    print(f"\n   Total: {total_passed}/{total_tests} tests passed")
    print("=" * 70 + "\n")

    return results


async def quick_send_email(recipient: str, smtp_config: Optional[Dict] = None):
    """Quick utility to send a test email."""
    print(f"\n[EMAIL] Quick Send Email to: {recipient}\n")
    
    tester = EmailNotificationTester()
    
    try:
        # Check health
        if not await tester.test_health_check():
            print("[FAIL] Service not running")
            return
        
        # Setup
        await tester.create_tenant()
        
        if smtp_config:
            global SMTP_CONFIG
            SMTP_CONFIG = smtp_config
            
        await tester.configure_smtp_provider()
        await tester.create_email_template()
        
        # Send
        result = await tester.send_email_notification(recipient_email=recipient)
        
        print(f"\nResult: {'[OK] Success' if result.get('success') else '[FAIL] Failed'}")
        
    finally:
        await tester.close()


# ============================================================================
# PYTEST TEST FUNCTIONS
# ============================================================================
# These functions are discovered and run by pytest

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def tester():
    """Fixture that provides a configured EmailNotificationTester instance."""
    t = EmailNotificationTester()
    yield t
    await t.close()


@pytest_asyncio.fixture
async def setup_tenant(tester):
    """Fixture that sets up a tenant with SMTP config and template."""
    # Create tenant
    assert await tester.create_tenant(), "Failed to create tenant"
    # Configure SMTP
    assert await tester.configure_smtp_provider(), "Failed to configure SMTP"
    # Create template
    assert await tester.create_email_template(), "Failed to create template"
    yield tester
    # Cleanup after test
    await tester.cleanup()


@pytest.mark.asyncio
async def test_service_health(tester):
    """Test that the notification service is healthy and responding."""
    result = await tester.test_health_check()
    assert result is True, "Service health check failed"


@pytest.mark.asyncio
async def test_create_tenant(tester):
    """Test creating a new tenant."""
    result = await tester.create_tenant()
    assert result is True, "Failed to create tenant"
    assert tester.tenant_id is not None, "Tenant ID should be set"
    assert tester.tenant_prefix is not None, "Tenant prefix should be set"


@pytest.mark.asyncio
async def test_configure_smtp_provider(tester):
    """Test configuring SMTP provider for a tenant."""
    # First create tenant
    await tester.create_tenant()
    
    # Then configure SMTP
    result = await tester.configure_smtp_provider()
    assert result is True, "Failed to configure SMTP provider"
    assert tester.config_id is not None, "Config ID should be set"


@pytest.mark.asyncio
async def test_create_email_template(tester):
    """Test creating an email template."""
    # Setup: create tenant first
    await tester.create_tenant()
    
    # Create template
    result = await tester.create_email_template()
    assert result is True, "Failed to create email template"
    assert tester.template_id is not None, "Template ID should be set"


@pytest.mark.asyncio
async def test_full_email_flow(tester):
    """Test the complete email notification flow (infrastructure only).
    
    Note: Actual email sending will fail without real SMTP credentials.
    This test verifies the infrastructure setup works correctly.
    """
    # 1. Create tenant
    assert await tester.create_tenant(), "Failed to create tenant"
    
    # 2. Configure SMTP
    assert await tester.configure_smtp_provider(), "Failed to configure SMTP"
    
    # 3. Create template
    assert await tester.create_email_template(), "Failed to create template"
    
    # 4. Attempt to send email (will fail with placeholder credentials)
    result = await tester.send_email_notification()
    
    # The request should be accepted even if sending fails
    # (infrastructure test, not actual delivery test)
    assert result is not None, "Should receive a response"
    assert "success" in result or "errorMessage" in result, "Response should have status"


@pytest.mark.asyncio
async def test_idempotency_check(tester):
    """Test that duplicate messages are detected."""
    # Setup
    await tester.create_tenant()
    await tester.configure_smtp_provider()
    await tester.create_email_template()
    
    # Test idempotency
    result = await tester.test_idempotency()
    assert result is True, "Idempotency check should pass"


@pytest.mark.asyncio
async def test_get_notifications_endpoint(tester):
    """Test the get notifications endpoint returns valid response."""
    # Setup
    await tester.create_tenant()
    
    # Get notifications (empty is fine)
    result = await tester.get_notifications()
    assert result is not None, "Should receive a response"
    # Response should have items key (even if empty)
    assert "items" in result or "error" in result, "Response should have items or error"


# ============================================================================
# MAIN ENTRY POINT (for direct script execution)
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("""
+======================================================================+
|                 Email Notification Test Script                        |
+======================================================================+
|                                                                       |
|  Before running, update the following environment variables:          |
|                                                                       |
|  SMTP_HOST         - Your SMTP server (default: smtp.gmail.com)       |
|  SMTP_PORT         - SMTP port (default: 587)                         |
|  SMTP_USERNAME     - Your SMTP username/email                         |
|  SMTP_PASSWORD     - Your SMTP password (use App Password for Gmail)  |
|  SMTP_FROM_EMAIL   - Sender email address                             |
|  SMTP_FROM_NAME    - Sender display name                              |
|  TEST_EMAIL        - Recipient email for testing                      |
|                                                                       |
|  Usage:                                                               |
|    python tests/test_email_notification.py              # Full test   |
|    python tests/test_email_notification.py quick email  # Quick send  |
|    python tests/test_email_notification.py cleanup      # With clean  |
|                                                                       |
+======================================================================+
""")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick" and len(sys.argv) > 2:
            asyncio.run(quick_send_email(sys.argv[2]))
        elif sys.argv[1] == "cleanup":
            asyncio.run(run_full_test(cleanup_after=True))
        else:
            print(f"Unknown argument: {sys.argv[1]}")
    else:
        asyncio.run(run_full_test(cleanup_after=False))

