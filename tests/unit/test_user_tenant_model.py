from notification_service.infrastructure.persistence.models.user.user import UserModel
from notification_service.infrastructure.persistence.models.user.user_tenant import UserTenantModel


def test_user_tenant_model_imports_without_name_error() -> None:
    assert UserTenantModel.__tablename__ == "user_tenants"


def test_user_tenant_model_has_tenant_scope_role_and_valid_constraint() -> None:
    table = UserTenantModel.__table__
    assert "role" in table.columns
    assert table.columns["role"].type.length == 50
    constraint_names = {constraint.name for constraint in table.constraints}
    assert "chk_user_tenant_role_valid" in constraint_names
    assert "chk_tenant_manager_has_tenant" not in constraint_names


def test_user_model_has_global_role_constraint() -> None:
    table = UserModel.__table__
    assert "role" in table.columns
    assert table.columns["role"].type.length == 50
    constraint_names = {constraint.name for constraint in table.constraints}
    assert "chk_user_role_valid" in constraint_names
