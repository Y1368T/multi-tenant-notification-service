from fastapi import Depends, Request, Query
from qena_shared_lib.http import ControllerBase, api_controller, get, post, put, delete, patch
from qena_shared_lib.dependencies.http import get_service
from uuid import UUID
from typing import List, Optional, Any
from sqlalchemy import select, or_, func

from notification_service.application.services.tenant_service import TenantService
from notification_service.application.services.provider_service import ProviderService
from notification_service.adapters.inbound.dependencies import require_role
from notification_service.infrastructure.persistence.db_session.session import Database
from notification_service.infrastructure.persistence.models.user.user import UserModel
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel
from notification_service.infrastructure.persistence.models.tenant.tenant import TenantModel
from notification_service.adapters.inbound.dto.paginated_response_dto import PaginatedResponseDTO
from notification_service.adapters.inbound.dto.admin_user_dto import AdminUserResponseDTO, AdminCreateUserRequestDTO
from notification_service.infrastructure.services.keycloak_admin_service import KeycloakAdminService
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

# Use a generic controller for the new Admin API
@api_controller(prefix="/api/admin", tags=["Admin API"])
class AdminAPIController(ControllerBase):
    def __init__(self, tenantService: TenantService = Depends(), providerService: ProviderService = Depends()):
        self.tenantService = tenantService
        self.providerService = providerService

    # --- Tenants ---
    @get("/tenants")
    async def get_tenants(self, request: Request) -> Any:
        """Get all tenants (Super Admin)"""
        # In real implementation: build PaginatedRequest and return self.tenantService.get()
        return {"message": "List of all tenants (stubbed)"}

    @post("/tenants")
    async def create_tenant(self, request: Request, payload: dict) -> Any:
        return {"message": "Tenant created", "data": payload}

    @put("/tenants/{tenant_id}")
    async def update_tenant(self, tenant_id: UUID, request: Request, payload: dict) -> Any:
        return {"message": f"Tenant {tenant_id} updated", "data": payload}

    @delete("/tenants/{tenant_id}")
    async def delete_tenant(self, tenant_id: UUID, request: Request) -> Any:
        return {"message": f"Tenant {tenant_id} deleted"}

    # --- Users ---
    @get("/users", dependencies=[Depends(require_role(["super-admin"]))], response_model=PaginatedResponseDTO[AdminUserResponseDTO])
    async def get_users(self, 
                        request: Request, 
                        page: int = Query(1, ge=1), 
                        pageSize: int = Query(20, ge=1, le=100),
                        role: Optional[str] = None,
                        tenantId: Optional[UUID] = None,
                        search: Optional[str] = None) -> PaginatedResponseDTO[AdminUserResponseDTO]:
        
        db = get_service(request.app, Database)
        
        async with db.session_factory() as db_session:
            # Build base query
            stmt = select(UserModel)
            count_stmt = select(func.count(UserModel.id))
            
            # Apply filters
            if role:
                stmt = stmt.where(UserModel.role == role)
                count_stmt = count_stmt.where(UserModel.role == role)
                
            if tenantId:
                stmt = stmt.join(UserTenantModel).where(UserTenantModel.tenant_id == tenantId)
                count_stmt = count_stmt.join(UserTenantModel).where(UserTenantModel.tenant_id == tenantId)
                
            if search:
                search_filter = or_(
                    UserModel.email.ilike(f"%{search}%"),
                    UserModel.fullName.ilike(f"%{search}%")
                )
                stmt = stmt.where(search_filter)
                count_stmt = count_stmt.where(search_filter)
                
            # Execute count
            total_count = await db_session.scalar(count_stmt) or 0
            
            # Execute fetch with pagination
            stmt = stmt.order_by(UserModel.createdAt.desc()).offset((page - 1) * pageSize).limit(pageSize)
            result = await db_session.execute(stmt)
            users = result.scalars().all()
            
            # Prepare DTOs
            items = []
            for u in users:
                items.append(AdminUserResponseDTO(
                    id=u.id,
                    email=u.email,
                    fullName=u.fullName,
                    role=u.role,
                    isActive=u.isActive,
                    createdAt=u.createdAt,
                    updatedAt=u.updatedAt,
                    tenants=[] # Skipping eager join for now to avoid query complexity, but can be added
                ))
            
            total_pages = (total_count + pageSize - 1) // pageSize
            
            return PaginatedResponseDTO(
                items=items,
                totalCount=total_count,
                page=page,
                pageSize=pageSize,
                totalPages=total_pages,
                hasNext=page < total_pages,
                hasPrevious=page > 1
            )

    @post("/users", dependencies=[Depends(require_role(["super-admin"]))], status_code=status.HTTP_201_CREATED, response_model=AdminUserResponseDTO)
    async def create_user(self, request: Request, payload: AdminCreateUserRequestDTO) -> AdminUserResponseDTO:
        db = get_service(request.app, Database)
        keycloak_service = get_service(request.app, KeycloakAdminService)
        
        # We only support tenant-manager creation from this endpoint currently as per spec
        if payload.role != "tenant-manager":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only 'tenant-manager' role can be assigned via this endpoint.")
            
        # Split full name for Keycloak
        name_parts = payload.full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Step 1: Create user in Keycloak (this throws if email exists)
        try:
            keycloak_user_id = await keycloak_service.create_user(
                email=payload.email,
                first_name=first_name,
                last_name=last_name
            )
        except ValueError as e:
            # Re-raise standard value errors as 409 conflict
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to create user in Keycloak: {e}")

        # Step 2: Insert into local database
        try:
            async with db.session_factory() as db_session:
                new_user = UserModel(
                    keycloakId=keycloak_user_id,
                    email=payload.email,
                    fullName=payload.full_name,
                    role="tenant-manager",
                    isActive=True
                )
                db_session.add(new_user)
                await db_session.flush() # flush to get the user ID
                
                # Create the tenant association
                user_tenant = UserTenantModel(
                    user_id=new_user.id,
                    tenant_id=payload.tenant_id,
                    role="tenant-manager",
                    isActive=True
                )
                db_session.add(user_tenant)
                await db_session.commit()
                
                return AdminUserResponseDTO(
                    id=new_user.id,
                    email=new_user.email,
                    fullName=new_user.fullName,
                    role=new_user.role,
                    isActive=new_user.isActive,
                    createdAt=new_user.createdAt,
                    updatedAt=new_user.updatedAt,
                    tenants=[str(payload.tenant_id)]
                )
        except IntegrityError as e:
            # This handles foreign key violations (tenant doesn't exist)
            # Rollback was automatically handled by context manager, but we MUST cleanup Keycloak
            await keycloak_service.delete_user(keycloak_user_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database constraint violation (e.g. invalid tenant_id).")
        except Exception as e:
            # Complete failure, rollback keycloak
            await keycloak_service.delete_user(keycloak_user_id)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save user in database.")

    @patch("/users/{user_id}", dependencies=[Depends(require_role(["super-admin"]))], response_model=AdminUserResponseDTO)
    async def update_user(self, user_id: UUID, request: Request, payload: AdminUpdateUserRequestDTO) -> AdminUserResponseDTO:
        db = get_service(request.app, Database)
        
        async with db.session_factory() as db_session:
            stmt = select(UserModel).options(
                joinedload(UserModel.tenantMemberships)
            ).where(UserModel.id == user_id)
            
            result = await db_session.execute(stmt)
            user = result.unique().scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
                
            # Update provided fields
            if payload.full_name is not None:
                user.fullName = payload.full_name
                
            if payload.is_active is not None:
                user.isActive = payload.is_active
                
            # Note: We do not call backend session invalidation here as per the BACKEND-NEW-008 deferral
            
            # Handling tenant_id update for tenant-managers
            if payload.tenant_id is not None and user.role == "tenant-manager":
                # Check if tenant exists
                tenant_stmt = select(TenantModel).where(TenantModel.id == payload.tenant_id)
                tenant_result = await db_session.execute(tenant_stmt)
                tenant = tenant_result.scalar_one_or_none()
                
                if not tenant:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant not found.")
                
                # Update first membership or create one
                if user.tenantMemberships:
                    # Usually MTNS users only have one active tenant membership
                    user.tenantMemberships[0].tenant_id = payload.tenant_id
                else:
                    new_membership = UserTenantModel(
                        user_id=user.id,
                        tenant_id=payload.tenant_id,
                        role="tenant-manager",
                        isActive=True
                    )
                    db_session.add(new_membership)
            
            await db_session.commit()
            
            # Refetch to return populated object
            refetch_stmt = select(UserModel).options(
                joinedload(UserModel.tenantMemberships)
            ).where(UserModel.id == user_id)
            refetch_result = await db_session.execute(refetch_stmt)
            updated_user = refetch_result.unique().scalar_one()
            
            tenant_ids = [str(m.tenant_id) for m in updated_user.tenantMemberships if m.isActive]
            
            return AdminUserResponseDTO(
                id=updated_user.id,
                email=updated_user.email,
                fullName=updated_user.fullName,
                role=updated_user.role,
                isActive=updated_user.isActive,
                createdAt=updated_user.createdAt,
                updatedAt=updated_user.updatedAt,
                tenants=tenant_ids
            )

    @delete("/users/{user_id}")
    async def delete_user(self, user_id: UUID, request: Request) -> Any:
        return {"message": f"User {user_id} deactivated"}

    @post("/users/{user_id}/reset-password", dependencies=[Depends(require_role(["super-admin"]))])
    async def reset_user_password(self, user_id: UUID, request: Request) -> Any:
        db = get_service(request.app, Database)
        keycloak_service = get_service(request.app, KeycloakAdminService)
        
        async with db.session_factory() as db_session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
                
            keycloak_user_id = user.keycloakId
            if not keycloak_user_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have an associated Keycloak identity.")
        
        try:
            await keycloak_service.send_password_reset_email(keycloak_user_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to trigger password reset via Keycloak: {e}")
            
        return {"message": "Password reset email sent."}

    # --- Providers ---
    @get("/providers")
    async def get_providers(self, request: Request) -> Any:
        return {"message": "List of providers (stubbed)"}

    @post("/providers")
    async def create_provider(self, request: Request, payload: dict) -> Any:
        return {"message": "Provider registered", "data": payload}
        
    @put("/providers/{provider_id}")
    async def update_provider(self, provider_id: UUID, request: Request, payload: dict) -> Any:
        return {"message": f"Provider {provider_id} updated", "data": payload}

    @delete("/providers/{provider_id}")
    async def delete_provider(self, provider_id: UUID, request: Request) -> Any:
        return {"message": f"Provider {provider_id} deleted"}

    # --- Analytics (Stubs as per plan) ---
    @get("/analytics/overview")
    async def get_analytics_overview(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics overview stub for DB team to implement"}
        
    @get("/analytics/tenants")
    async def get_analytics_tenants(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics tenants stub for DB team to implement"}
        
    @get("/analytics/channels")
    async def get_analytics_channels(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics channels stub for DB team to implement"}
        
    @get("/analytics/providers")
    async def get_analytics_providers(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics providers stub for DB team to implement"}
        
    @get("/analytics/errors")
    async def get_analytics_errors(self, request: Request, period: str = "7d") -> Any:
        return {"message": "Analytics errors stub for DB team to implement"}
