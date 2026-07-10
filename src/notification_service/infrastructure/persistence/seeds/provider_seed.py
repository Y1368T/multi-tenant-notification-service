"""Seed data for the providers table."""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.sql import or_

from notification_service.domain.entities.providers_supported import Provider
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.persistence.mappers.provider_mapper import ProviderMapper
from notification_service.infrastructure.persistence.models.providers_supported import ProviderModel

logger = logging.getLogger(__name__)

# Default Firebase private key sample used in the exported CSV
_FCM_PRIVATE_KEY = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDHQr2e7v8GlRJO\n"
    "i4BQonPnUOx9SXNSjulGeMwI7VIykZmF5+hQ8SqxX6TGRso/c94jBLTn6cbwsx9b\n"
    "IKOnROYmL6CaEwzGLOiAtQnCPLCOpxHDzEdTLek4jHsk4b1O3ah8fvMJLt0S0oX2\n"
    "Zw2ApTawyJwmSBpyYxY1lSE7ahlHxuF2s5iX32xYh9kxesaQBK6hKnMcLBLpQ6la\n"
    "Xm74hjDASZio19+DrBxypxthe8MGknydYRArG26BZFBghSqjI2dJgak8+9Aodi1Q\n"
    "cvb8ZofuFS+nY9TlKs6ztup4umaTigw1WvU98sP2H3yxUtqdbkjwf1cQ9nEHPU9v\n"
    "KLKMERoXAgMBAAECggEAIBjp9u7ptBORnNxk1thW/OpwsH0t70e9ClCNZrIP3RHO\n"
    "HfSthqhVJ7hP5cPjx//anF/MN6qqlKhN7ehz5Dm5gb+HSnpfbZGGAaw9PlrMrVX6\n"
    "ixneCBHrsQ5pYcIJNBSJk5sBfDez0y3dTW6WjWP6S3+Cg7ohTyQTS538+eyigN3z\n"
    "tBsBVA9Fkr4xOaO/Gz2xuNLcffjZNX8zMaG+6GnfvIpVJZvZ6ACpOkfgT2s/UzVv\n"
    "KOsi/0zEsbKGkxxSTHisPe2sQUqabN2NQgeAtZAznBz02Qou92nvn7SYJSKCXu3j\n"
    "zew26V2gKKOm1lW9g+SRnv/5/wqt4/LFVQ5RSHUW7QKBgQD+9olY3KWOfb9Im27U\n"
    "T0c4rKjHwt5TtjGoYM4MwZgWuUrswAB8Nd095AUZx42RH9YEVNKTpImCkS3LO5wn\n"
    "pHuvjMEyC+pj3oTn+9U+xhBkuANLv+NvU6+YtXct+LAxJc666XQJs98oBinzDeu9\n"
    "4vuv7ylLRLiDUp4j1AJOAleL6wKBgQDIEjUzBNZtcd5pFmKECtiOgOHHhd/c8gwG\n"
    "kpGkx7jj4TyB+7Upw1ECAvnv/zdLM/DifRDviAjjAddZf9+Sm0GfD5ADqK3YLjew\n"
    "Xup31v811ueF30WlzanPUQcxlprByIhMcnJLkPNS+L8ETkKds31v3CJ8vo+SIa5M\n"
    "pHM8X7L7hQKBgBwGtapS9s/m+rPcgh5MaKPONu9eeFnzWRoNKhk03qcAzz+fC26b\n"
    "7Sn0eqsOyHz/ZuMq/8rC92qm0sXYU5338rClZEdAEA/SUgG+KP6xfvPTVmlpOnLu\n"
    "XAsJR4SCJbwBT+wz5VF7uDgKFWpmSVeiL9BzFbL0ZuPonQGLOIWitETpAoGAZZdJ\n"
    "SDTGpSBS7U2ejKntOL8c5nGGMOz/Sj8WkXOQ4LW4QdCMNz6kXb8hJsqTSy5+vKMA\n"
    "/IA48vw2W43g+tK3SYtfd1wpmkItqPMpX9zeDnqnaYTsGrsJ5OmiG3376zZmb1sV\n"
    "ymU6CQGiDQ+oJ+fCZBCFuo4Q3QUZOnWuxhNaEPkCgYEAzhHABTccdP9MD5xGb82d\n"
    "3MgYRdSL69jeWFulS/0Y776Sf3jladwg/xfprf/svQ+2R8np1tSoJsNDBkEZYLBM\n"
    "dd7GYePo8Z4pogZB+Lc1KBzcXUbM2zfiIkjRtZGuor8+NZ/gaW2548Y5mFn8g6Iu\n"
    "sSRjYHAzY3ciWd5AxX20qdE=\n"
    "-----END PRIVATE KEY-----\n"
)

PROVIDER_SEED_DATA: tuple[Provider, ...] = (
    # SMTP Email Provider
    Provider(
        id=UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        providerName="smtp",
        displayName="SMTP Email",
        channel="email",
        description="Send emails via SMTP server (Gmail, Outlook, custom SMTP servers).",
        docsUrl="https://docs.python.org/3/library/smtplib.html",
        testEndpoint="/api/providers/email/smtp/test",
        configSchema={
            "title": "SMTP Configuration",
            "type": "object",
            "required": ["host", "port", "username", "password", "fromEmail"],
            "properties": {
                "host": {
                    "title": "SMTP Host",
                    "type": "string",
                    "minLength": 1,
                    "description": "SMTP server hostname (e.g., smtp.gmail.com)",
                },
                "port": {
                    "title": "Port",
                    "type": "integer",
                    "default": 587,
                    "description": "SMTP port (587 for TLS, 465 for SSL, 25 for plain)",
                },
                "username": {
                    "title": "Username",
                    "type": "string",
                    "minLength": 1,
                    "description": "SMTP authentication username (usually your email)",
                },
                "password": {
                    "title": "Password",
                    "type": "string",
                    "minLength": 1,
                    "description": "SMTP authentication password or app password",
                },
                "fromEmail": {
                    "title": "From Email",
                    "type": "string",
                    "format": "email",
                    "minLength": 1,
                    "description": "Email address to send from",
                },
                "fromName": {
                    "title": "From Name",
                    "type": "string",
                    "default": "",
                    "description": "Display name for the sender (optional)",
                },
                "useTls": {
                    "title": "Use TLS",
                    "type": "boolean",
                    "default": True,
                    "description": "Use STARTTLS encryption (recommended for port 587)",
                },
                "useSsl": {
                    "title": "Use SSL",
                    "type": "boolean",
                    "default": False,
                    "description": "Use SSL encryption (for port 465)",
                },
                "timeout": {
                    "title": "Timeout",
                    "type": "integer",
                    "default": 30,
                    "description": "Connection timeout in seconds",
                },
            },
        },
        uiSchema={
            "host": {
                "ui:widget": "text",
                "ui:placeholder": "smtp.gmail.com",
                "ui:help": "Enter your SMTP server hostname.",
            },
            "port": {
                "ui:widget": "number",
                "ui:placeholder": "587",
                "ui:help": "SMTP port (587 for TLS, 465 for SSL).",
            },
            "username": {
                "ui:widget": "text",
                "ui:placeholder": "your-email@gmail.com",
                "ui:help": "Your SMTP username (usually your email).",
            },
            "password": {
                "ui:widget": "password",
                "ui:placeholder": "******",
                "ui:help": "Your SMTP password or app-specific password.",
            },
            "fromEmail": {
                "ui:widget": "email",
                "ui:placeholder": "noreply@yourcompany.com",
                "ui:help": "The email address that will appear in the From field.",
            },
            "fromName": {
                "ui:widget": "text",
                "ui:placeholder": "Your Company",
                "ui:help": "Display name for the sender (optional).",
            },
            "useTls": {
                "ui:widget": "checkbox",
                "ui:help": "Enable TLS encryption (recommended).",
            },
            "useSsl": {
                "ui:widget": "checkbox",
                "ui:help": "Enable SSL encryption (use for port 465).",
            },
            "timeout": {
                "ui:widget": "number",
                "ui:placeholder": "30",
                "ui:help": "Connection timeout in seconds.",
            },
            "ui:order": [
                "host",
                "port",
                "username",
                "password",
                "fromEmail",
                "fromName",
                "useTls",
                "useSsl",
                "timeout",
            ],
        },
        isActive=True,
        createdAt=datetime.fromisoformat("2025-01-26 10:00:00.000000"),
        updatedAt=datetime.fromisoformat("2025-01-26 10:00:00.000000"),
    ),
    # Jasmin SMS Provider
    Provider(
        id=UUID("127bdcb3-d7f9-4d76-8660-8804cde5171e"),
        providerName="jasmin",
        displayName="Jasmin SMS Gateway",
        channel="sms",
        description="Send SMS via Jasmin HTTP API.",
        docsUrl="https://jasminsms.com/docs/http-api",
        testEndpoint="/api/providers/sms/jasmin/test",
        configSchema={
            "title": "Jasmin Configuration",
            "type": "object",
            "required": ["baseUrl", "username", "password", "sender"],
            "properties": {
                "baseUrl": {
                    "title": "Base URL",
                    "type": "string",
                    "format": "uri",
                    "default": "http://10.253.2.150:8080/secure/send",
                },
                "username": {
                    "title": "Username",
                    "type": "string",
                    "minLength": 1,
                    "default": "unified",
                },
                "password": {
                    "title": "Password",
                    "type": "string",
                    "minLength": 1,
                    "default": "unified",
                },
                "sender": {
                    "title": "Sender ID",
                    "type": "string",
                    "minLength": 1,
                    "default": "9994",
                },
            },
        },
        uiSchema={
            "baseUrl": {
                "ui:widget": "uri",
                "ui:placeholder": "http://10.253.2.150:8080/secure/send",
                "ui:help": "Enter the Jasmin HTTP endpoint.",
            },
            "username": {
                "ui:widget": "text",
                "ui:placeholder": "unified",
                "ui:help": "Jasmin account username.",
            },
            "password": {
                "ui:widget": "password",
                "ui:placeholder": "******",
                "ui:help": "Jasmin account password.",
            },
            "sender": {
                "ui:widget": "text",
                "ui:placeholder": "9994",
                "ui:help": "Originator/Sender ID.",
            },
            "ui:order": ["baseUrl", "username", "password", "sender"],
        },
        isActive=True,
        createdAt=datetime.fromisoformat("2025-12-02 08:20:26.501364"),
        updatedAt=datetime.fromisoformat("2025-12-02 08:20:26.501370"),
    ),
    Provider(
        id=UUID("81bde38f-0d02-43ea-8fc1-b2f93302b2d0"),
        providerName="afromessage",
        displayName="Afromessage",
        channel="sms",
        description="Send SMS via Afromessage API.",
        docsUrl="https://example.com/docs/afromessage",
        testEndpoint="/api/providers/sms/afromessage/test",
        configSchema={
            "title": "Afromessage Configuration",
            "type": "object",
            "required": ["baseUrl", "apiKey", "sender", "from"],
            "properties": {
                "baseUrl": {
                    "title": "Base URL",
                    "type": "string",
                    "format": "uri",
                    "default": "https://api.afromessage.com/api",
                },
                "apiKey": {
                    "title": "API Key",
                    "type": "string",
                    "minLength": 1,
                },
                "sender": {
                    "title": "Sender Name",
                    "type": "string",
                    "minLength": 1,
                },
                "from": {
                    "title": "From ID",
                    "type": "string",
                    "minLength": 1,
                },
                "callbackUrl": {
                    "title": "Callback URL",
                    "type": "string",
                    "format": "uri",
                },
            },
        },
        uiSchema={
            "baseUrl": {
                "ui:widget": "uri",
                "ui:placeholder": "https://api.afromessage.com/api",
                "ui:help": "Enter the Afromessage API base URL.",
            },
            "apiKey": {
                "ui:widget": "password",
                "ui:placeholder": "API Key",
                "ui:help": "Enter your Afromessage API key.",
            },
            "sender": {
                "ui:widget": "text",
                "ui:placeholder": "Sender Name",
                "ui:help": "Enter the sender name for SMS.",
            },
            "from": {
                "ui:widget": "text",
                "ui:placeholder": "From ID",
                "ui:help": "Enter the from ID provided by Afromessage.",
            },
            "callbackUrl": {
                "ui:widget": "uri",
                "ui:placeholder": "https://your-domain.com/callback",
                "ui:help": "Optional callback URL for delivery status.",
            },
            "ui:order": ["baseUrl", "apiKey", "sender", "from", "callbackUrl"],
        },
        isActive=True,
        createdAt=datetime.fromisoformat("2025-12-02 08:29:04.440925"),
        updatedAt=datetime.fromisoformat("2025-12-02 08:29:04.440933"),
    ),
    Provider(
        id=UUID("9fede230-239c-4234-9ac2-c8f292545f72"),
        providerName="fcm",
        displayName="Firebase Cloud Messaging (FCM)",
        channel="inapp",
        description="Send push notifications via Firebase Cloud Messaging using service account credentials.",
        docsUrl="https://firebase.google.com/docs/cloud-messaging",
        testEndpoint="/api/providers/inapp/firebase_cloud_messaging/test",
        configSchema={
            "title": "Firebase Cloud Messaging Configuration",
            "type": "object",
            "required": ["type", "project_id", "private_key", "client_email"],
            "properties": {
                "type": {
                    "type": "string",
                    "title": "Type",
                    "default": "service_account",
                    "description": "Service account type (always 'service_account')",
                },
                "project_id": {
                    "type": "string",
                    "title": "Project ID",
                    "minLength": 1,
                    "default": "crafty-mile-256206",
                    "description": "Your Firebase project ID",
                },
                "private_key_id": {
                    "type": "string",
                    "title": "Private Key ID",
                    "default": "5c83f0518acbe9fc3f6ac8b255be88371fea7681",
                    "description": "Private key identifier",
                },
                "private_key": {
                    "type": "string",
                    "title": "Private Key",
                    "minLength": 1,
                    "default": _FCM_PRIVATE_KEY,
                    "description": "Service account private key (PEM format)",
                },
                "client_email": {
                    "type": "string",
                    "title": "Client Email",
                    "format": "email",
                    "minLength": 1,
                    "default": "firebase-adminsdk-cd1zw@crafty-mile-256206.iam.gserviceaccount.com",
                    "description": "Service account client email",
                },
                "client_id": {
                    "type": "string",
                    "title": "Client ID",
                    "default": "107900063202060280081",
                    "description": "Service account client ID",
                },
                "auth_uri": {
                    "type": "string",
                    "title": "Auth URI",
                    "default": "https://accounts.google.com/o/oauth2/auth",
                    "format": "uri",
                    "description": "OAuth2 authentication URI",
                },
                "token_uri": {
                    "type": "string",
                    "title": "Token URI",
                    "default": "https://oauth2.googleapis.com/token",
                    "format": "uri",
                    "description": "OAuth2 token URI",
                },
                "auth_provider_x509_cert_url": {
                    "type": "string",
                    "title": "Auth Provider X509 Cert URL",
                    "default": "https://www.googleapis.com/oauth2/v1/certs",
                    "format": "uri",
                    "description": "OAuth2 certificate URL",
                },
                "client_x509_cert_url": {
                    "type": "string",
                    "title": "Client X509 Cert URL",
                    "format": "uri",
                    "default": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-cd1zw%40crafty-mile-256206.iam.gserviceaccount.com",
                    "description": "Client certificate URL",
                },
                "universe_domain": {
                    "type": "string",
                    "title": "Universe Domain",
                    "default": "googleapis.com",
                    "description": "Google APIs universe domain",
                },
            },
        },
        uiSchema={
            "type": {
                "ui:help": "Service account type (typically 'service_account').",
                "ui:placeholder": "service_account",
                "ui:widget": "text",
            },
            "project_id": {
                "ui:help": "Enter your Firebase project ID (e.g., crafty-mile-256206).",
                "ui:placeholder": "crafty-mile-256206",
                "ui:widget": "text",
            },
            "private_key_id": {
                "ui:help": "Private key identifier from your service account JSON.",
                "ui:placeholder": "Private Key ID",
                "ui:widget": "password",
            },
            "private_key": {
                "ui:help": "Enter the complete private key from your service account JSON (including BEGIN/END lines).",
                "ui:placeholder": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
                "ui:widget": "textarea",
                "ui:options": {"rows": 10},
            },
            "client_email": {
                "ui:help": "Service account email address (e.g., firebase-adminsdk-xxx@project-id.iam.gserviceaccount.com).",
                "ui:placeholder": "firebase-adminsdk-xxx@project-id.iam.gserviceaccount.com",
                "ui:widget": "email",
            },
            "client_id": {
                "ui:help": "Service account client ID (optional).",
                "ui:placeholder": "Client ID",
                "ui:widget": "text",
            },
            "auth_uri": {
                "ui:help": "OAuth2 authentication URI (default: https://accounts.google.com/o/oauth2/auth).",
                "ui:placeholder": "https://accounts.google.com/o/oauth2/auth",
                "ui:widget": "text",
            },
            "token_uri": {
                "ui:help": "OAuth2 token URI (default: https://oauth2.googleapis.com/token).",
                "ui:placeholder": "https://oauth2.googleapis.com/token",
                "ui:widget": "text",
            },
            "auth_provider_x509_cert_url": {
                "ui:help": "OAuth2 certificate URL (default: https://www.googleapis.com/oauth2/v1/certs).",
                "ui:placeholder": "https://www.googleapis.com/oauth2/v1/certs",
                "ui:widget": "text",
            },
            "client_x509_cert_url": {
                "ui:help": "Client X509 certificate URL (optional).",
                "ui:placeholder": "https://www.googleapis.com/robot/v1/metadata/x509/...",
                "ui:widget": "uri",
            },
            "universe_domain": {
                "ui:help": "Google APIs universe domain (default: googleapis.com).",
                "ui:placeholder": "googleapis.com",
                "ui:widget": "text",
            },
            "ui:order": [
                "type",
                "project_id",
                "client_email",
                "private_key",
                "private_key_id",
                "client_id",
                "auth_uri",
                "token_uri",
                "auth_provider_x509_cert_url",
                "client_x509_cert_url",
                "universe_domain",
            ],
        },
        isActive=True,
        createdAt=datetime.fromisoformat("2025-11-17 11:42:31.784895"),
        updatedAt=datetime.fromisoformat("2025-11-17 11:42:31.784900"),
    ),
    Provider(
        id=UUID("af779fb3-425d-487a-828f-edfe52776a9f"),
        providerName="kifiya",
        displayName="KifiyaShortcode",
        channel="sms",
        description="Send SMS via Kifiya shortcode.",
        docsUrl="https://example.com/docs/ethiotelecom",
        testEndpoint="/test",
        configSchema={
            "title": "Kifiya Shortcode Configuration",
            "type": "object",
            "required": ["tokenId", "url", "address"],
            "properties": {
                "address": {
                    "minLength": 10,
                    "title": "phone",
                    "type": "string",
                },
                "tokenId": {
                    "minLength": 1,
                    "title": "TokenId",
                    "type": "string",
                },
                "url": {
                    "format": "uri",
                    "title": "API URL",
                    "type": "string",
                },
            },
        },
        uiSchema={
            "tokenId": {
                "ui:help": "Enter your tokenId key here.",
                "ui:placeholder": "API Key",
                "ui:widget": "password",
            },
            "address": {
                "ui:help": "Enter your Phone here.",
                "ui:placeholder": "+251913327219",
                "ui:widget": "text",
            },
            "url": {
                "ui:widget": "uri",
                "ui:placeholder": "https://api.afromessage.com/api",
                "ui:help": "Enter the Afromessage API base URL.",
            },
            "ui:order": ["tokenId", "url", "address"],
        },
        isActive=True,
        createdAt=datetime.fromisoformat("2025-11-05 20:01:54.087337"),
        updatedAt=datetime.fromisoformat("2025-11-05 20:01:54.087354"),
    ),
    #new
    # WhatsApp Meta Cloud API Provider
    Provider(
        id=UUID("d3f1a2b4-5c6d-4e7f-8a9b-0c1d2e3f4a5b"),
        providerName="meta_cloud",
        displayName="WhatsApp (Meta Cloud API)",
        channel="whatsapp",
        description="Send WhatsApp messages via Meta's WhatsApp Cloud API.",
        docsUrl="https://developers.facebook.com/docs/whatsapp/cloud-api",
        testEndpoint="/api/providers/whatsapp/meta_cloud/test",
        configSchema={
            "title": "WhatsApp Meta Cloud API Configuration",
            "type": "object",
            "required": ["accessToken", "phoneNumberId"],
            "properties": {
                "accessToken": {
                    "title": "Access Token",
                    "type": "string",
                    "minLength": 1,
                    "description": "Permanent or temporary Meta Cloud API access token",
                },
                "phoneNumberId": {
                    "title": "Phone Number ID",
                    "type": "string",
                    "minLength": 1,
                    "description": "The WhatsApp Business phone number ID from Meta's developer console",
                },
                "businessAccountId": {
                    "title": "Business Account ID",
                    "type": "string",
                    "description": "Optional WhatsApp Business Account ID",
                },
                "apiVersion": {
                    "title": "API Version",
                    "type": "string",
                    "default": "v20.0",
                    "description": "Meta Graph API version to use",
                },
            },
        },
        uiSchema={
            "accessToken": {
                "ui:widget": "password",
                "ui:placeholder": "EAAG...",
                "ui:help": "Enter your Meta Cloud API access token.",
            },
            "phoneNumberId": {
                "ui:widget": "text",
                "ui:placeholder": "1234567890",
                "ui:help": "Enter your WhatsApp Business phone number ID.",
            },
            "businessAccountId": {
                "ui:widget": "text",
                "ui:placeholder": "1234567890",
                "ui:help": "Optional: your WhatsApp Business Account ID.",
            },
            "apiVersion": {
                "ui:widget": "text",
                "ui:placeholder": "v20.0",
                "ui:help": "Meta Graph API version (default v20.0).",
            },
            "ui:order": ["accessToken", "phoneNumberId", "businessAccountId", "apiVersion"],
        },
        isActive=True,
        createdAt=datetime.fromisoformat("2026-07-09 00:00:00.000000"),
        updatedAt=datetime.fromisoformat("2026-07-09 00:00:00.000000"),
    ),
    #new
)

async def seed_providers(database: Database) -> bool:
    """Insert default providers if they are missing."""
    mapper = ProviderMapper()
    
    # Use async context manager to ensure proper session initialization
    async with database.getSession() as session:
        try:
            inserted = 0

            for provider in PROVIDER_SEED_DATA:
                exists_stmt = select(ProviderModel.id).where(
                    or_(
                        ProviderModel.id == provider.id,
                        ProviderModel.providerName == provider.providerName,
                    )
                ).limit(1)

                existing = await session.scalar(exists_stmt)
                if existing:
                    continue

                session.add(mapper.toModel(provider))
                inserted += 1

            if inserted == 0:
                logger.info("Provider seed skipped; all default providers already exist.")
                return False

            await session.commit()
            logger.info("Seeded %d provider(s).", inserted)
            return True
        except Exception:
            await session.rollback()
            logger.exception("Failed to seed providers.")
            raise
