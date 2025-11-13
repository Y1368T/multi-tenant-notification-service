# LINQ-Style Query API for Python

This implementation provides a .NET LINQ-like query API for Python with SQLAlchemy, enabling fluent, chainable queries similar to C# LINQ expressions.

## Features

- **Fluent API**: Method chaining for building queries
- **Type Safety**: Generic types with TypeVar support
- **Lambda Expressions**: Python lambdas used like C# for predicates and selectors
- **Eager Loading**: Include relationships with `include()`
- **Pagination**: Built-in pagination support with `to_paginated_list()`
- **Aggregations**: Sum, average, min, max, count, distinct, group_by
- **Projections**: Select specific fields or transform entities
- **Terminal Operations**: first, first_or_default, single, single_or_default, any

## Installation

The LINQ extensions are already integrated into the `GenericRepository` class. No additional setup required.

## Basic Usage

### 1. Simple Query with Where and OrderBy

**C# LINQ:**
```csharp
var results = await unitOfWork.SmsNotifications
    .Where(x => x.Status == NotificationStatus.Sent)
    .OrderByDescending(x => x.CreatedAt)
    .ToListAsync();
```

**Python Equivalent:**
```python
results = await (
    self.uow.sms_notifications.query()
    .where(lambda x: x.status == NotificationStatus.SENT)
    .order_by_descending(lambda x: x.created_at, "created_at")
    .to_list()
)
```

### 2. Pagination

**C# LINQ:**
```csharp
var page = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .OrderBy(x => x.CreatedAt)
    .ToPagedListAsync(page: 1, pageSize: 20);
```

**Python Equivalent:**
```python
page = await (
    self.uow.sms_notifications.query()
    .where(lambda x: x.template.tenant_id == tenant_id)
    .order_by(lambda x: x.created_at, "created_at")
    .to_paginated_list(page=1, page_size=20)
)
```

### 3. Complex Filtering with Navigation Properties

**C# LINQ:**
```csharp
var results = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId && 
               x.Template.Tenant.Prefix == prefix &&
               x.Status == status)
    .OrderBy(x => x.Template.Name)
    .ThenByDescending(x => x.CreatedAt)
    .ToPagedListAsync(page, pageSize);
```

**Python Equivalent:**
```python
results = await (
    self.uow.sms_notifications.query()
    .include("template", "template.tenant")  # Eager load
    .where(lambda x: 
        x.template.tenant_id == tenant_id and
        x.template.tenant.prefix == prefix and
        x.status == status
    )
    .order_by(lambda x: x.template.name, "template_id")
    .then_by_descending(lambda x: x.created_at, "created_at")
    .to_paginated_list(page, page_size)
)
```

### 4. Skip and Take

**C# LINQ:**
```csharp
var results = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .OrderBy(x => x.CreatedAt)
    .Skip(20)
    .Take(10)
    .ToListAsync();
```

**Python Equivalent:**
```python
results = await (
    self.uow.sms_notifications.query()
    .where(lambda x: x.template.tenant_id == tenant_id)
    .order_by(lambda x: x.created_at, "created_at")
    .skip(20)
    .take(10)
    .to_list()
)
```

### 5. Single Element Queries

**C# LINQ:**
```csharp
var notification = await unitOfWork.SmsNotifications
    .Where(x => x.Id == notificationId)
    .Include(x => x.Template)
    .ThenInclude(x => x.Tenant)
    .FirstOrDefaultAsync();
```

**Python Equivalent:**
```python
notification = await (
    self.uow.sms_notifications.query()
    .include("template", "template.tenant")
    .where(lambda x: x.id == notification_id)
    .first_or_default()
)
```

### 6. Aggregations

**C# LINQ:**
```csharp
var totalCount = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .CountAsync();

var totalRetries = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .SumAsync(x => x.RetryCount);

var avgRetries = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .AverageAsync(x => x.RetryCount);
```

**Python Equivalent:**
```python
query = self.uow.sms_notifications.query().where(
    lambda x: x.template.tenant_id == tenant_id
)

total_count = await query.count()
total_retries = await query.sum(lambda x: x.retry_count)
avg_retries = await query.average(lambda x: x.retry_count)
```

### 7. Group By

**C# LINQ:**
```csharp
var groups = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .GroupBy(x => x.Status)
    .ToListAsync();
```

**Python Equivalent:**
```python
groups = await (
    self.uow.sms_notifications.query()
    .where(lambda x: x.template.tenant_id == tenant_id)
    .group_by(lambda x: x.status)
)
# Returns dict[status, list[notifications]]
```

### 8. Select and Distinct

**C# LINQ:**
```csharp
var phoneNumbers = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .Select(x => x.RecipientPhone)
    .Distinct()
    .ToListAsync();
```

**Python Equivalent:**
```python
phone_numbers = await (
    self.uow.sms_notifications.query()
    .where(lambda x: x.template.tenant_id == tenant_id)
    .select(lambda x: x.recipient_phone)
    .distinct()
)
```

### 9. Projection to Custom Shape

**C# LINQ:**
```csharp
var results = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .Select(x => new {
        Id = x.Id,
        Phone = x.RecipientPhone,
        Status = x.Status,
        TemplateName = x.Template.Name
    })
    .ToListAsync();
```

**Python Equivalent:**
```python
results = await (
    self.uow.sms_notifications.query()
    .include("template")
    .where(lambda x: x.template.tenant_id == tenant_id)
    .select(lambda x: {
        "id": x.id,
        "phone": x.recipient_phone,
        "status": x.status,
        "template_name": x.template.name
    })
    .to_list()
)
```

### 10. Any (Existence Check)

**C# LINQ:**
```csharp
var hasPending = await unitOfWork.SmsNotifications
    .AnyAsync(x => x.Template.TenantId == tenantId && 
                  x.Status == NotificationStatus.Pending);
```

**Python Equivalent:**
```python
has_pending = await (
    self.uow.sms_notifications.query()
    .where(lambda x: 
        x.template.tenant_id == tenant_id and
        x.status == NotificationStatus.PENDING
    )
    .any()
)
```

### 11. Min and Max

**C# LINQ:**
```csharp
var oldest = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .MinAsync(x => x.CreatedAt);

var newest = await unitOfWork.SmsNotifications
    .Where(x => x.Template.TenantId == tenantId)
    .MaxAsync(x => x.CreatedAt);
```

**Python Equivalent:**
```python
query = self.uow.sms_notifications.query().where(
    lambda x: x.template.tenant_id == tenant_id
)

oldest = await query.min(lambda x: x.created_at)
newest = await query.max(lambda x: x.created_at)
```

## API Reference

### LinqQuery Class

#### Filtering Methods
- **`where(predicate: Callable[[TEntity], bool]) -> LinqQuery`**
  - Filter entities by lambda predicate
  - Example: `.where(lambda x: x.status == "sent")`

#### Ordering Methods
- **`order_by(key_selector, column_name=None) -> LinqQuery`**
  - Sort ascending by key selector
  - Example: `.order_by(lambda x: x.created_at, "created_at")`

- **`order_by_descending(key_selector, column_name=None) -> LinqQuery`**
  - Sort descending by key selector
  - Example: `.order_by_descending(lambda x: x.created_at, "created_at")`

- **`then_by(key_selector, column_name=None) -> LinqQuery`**
  - Secondary sort ascending
  - Example: `.order_by(lambda x: x.status).then_by(lambda x: x.created_at)`

- **`then_by_descending(key_selector, column_name=None) -> LinqQuery`**
  - Secondary sort descending

#### Pagination Methods
- **`skip(count: int) -> LinqQuery`**
  - Skip specified number of records
  - Example: `.skip(20)`

- **`take(count: int) -> LinqQuery`**
  - Take specified number of records
  - Example: `.take(10)`

#### Projection Methods
- **`select(selector: Callable[[TEntity], TResult]) -> LinqQuery`**
  - Transform entities to new shape
  - Example: `.select(lambda x: x.recipient_phone)`

#### Eager Loading Methods
- **`include(*relationships: str) -> LinqQuery`**
  - Eager load relationships
  - Example: `.include("template", "template.tenant")`

#### Terminal Operations
- **`async to_list() -> List[TEntity]`**
  - Execute query and return list
  - Example: `await query.to_list()`

- **`async to_paginated_list(page: int, page_size: int) -> PaginatedResult[TEntity]`**
  - Execute query with pagination
  - Example: `await query.to_paginated_list(1, 20)`

- **`async first() -> TEntity`**
  - Get first entity or raise exception
  - Raises `ValueError` if no entity found

- **`async first_or_default() -> Optional[TEntity]`**
  - Get first entity or None

- **`async single() -> TEntity`**
  - Get single entity or raise exception
  - Raises `ValueError` if 0 or multiple found

- **`async single_or_default() -> Optional[TEntity]`**
  - Get single entity or None
  - Raises `ValueError` if multiple found

#### Aggregation Methods
- **`async count() -> int`**
  - Count matching entities

- **`async any() -> bool`**
  - Check if any entity matches

- **`async sum(selector: Callable[[TEntity], Union[int, float]]) -> Union[int, float]`**
  - Sum numeric property

- **`async average(selector: Callable[[TEntity], Union[int, float]]) -> float`**
  - Calculate average of numeric property

- **`async min(selector: Callable[[TEntity], Any]) -> Any`**
  - Get minimum value

- **`async max(selector: Callable[[TEntity], Any]) -> Any`**
  - Get maximum value

- **`async distinct(key_selector=None) -> List[TEntity]`**
  - Get distinct entities

- **`async group_by(key_selector: Callable[[TEntity], Any]) -> dict`**
  - Group entities by key

## Repository Methods

### Starting a Query

**Method 1: Using `query()`**
```python
results = await self.uow.sms_notifications.query().where(...).to_list()
```

**Method 2: Using `where()` directly**
```python
results = await self.uow.sms_notifications.where(lambda x: x.status == "sent").to_list()
```

Both methods return a `LinqQuery[TEntity]` instance for fluent chaining.

## Value Objects

### PagedRequest
```python
from notification_service.domain.value_objects.paged_request import PagedRequest, SortDirection

request = PagedRequest(
    page=1,
    page_size=20,
    sort_by="created_at",
    sort_direction=SortDirection.DESC
)
```

### PaginatedResult
```python
@dataclass
class PaginatedResult(Generic[TEntity]):
    items: List[TEntity]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
```

## Performance Tips

1. **Use column names for SQL-level sorting**: When possible, provide the column name as the second argument to `order_by()`:
   ```python
   .order_by(lambda x: x.created_at, "created_at")  # SQL-level sort ✓
   .order_by(lambda x: x.created_at)  # In-memory sort ✗
   ```

2. **Eager load relationships**: Use `include()` to avoid N+1 queries:
   ```python
   .include("template", "template.tenant")
   ```

3. **Use pagination for large datasets**: Always paginate when displaying lists:
   ```python
   .to_paginated_list(page, page_size)
   ```

4. **Avoid in-memory filtering for large datasets**: Complex predicates are applied in-memory. For better performance, use SQL-level filters when possible.

## Examples in Service Layer

Check `application/services/sms_notification_service.py` for 11 comprehensive examples demonstrating:
- Basic filtering and ordering
- Complex multi-condition filtering
- Pagination
- Single element queries
- Aggregations (count, sum, average)
- Grouping and distinct
- Projections
- Min/max operations

## Architecture

### Files Structure
```
domain/value_objects/
  ├── paged_request.py          # PagedRequest, SortDirection
  └── paginated_result.py       # PaginatedResult[TEntity]

Infrastructure/persisitence/extensions/
  ├── linq_extensions.py        # LinqQuery[TEntity]
  └── queryable_extensions.py   # QueryableExtensions

Infrastructure/persisitence/repositories/
  └── generic_repository.py     # Updated with query() and where()

application/services/
  └── sms_notification_service.py  # Usage examples
```

## Type Safety

The implementation uses Python's `TypeVar` and `Generic` to provide type hints:

```python
TEntity = TypeVar('TEntity')
TModel = TypeVar('TModel')

class LinqQuery(Generic[TEntity, TModel]):
    ...
```

This enables IDE autocomplete and type checking when using the query builder.

## Comparison with Original Repository Methods

### Old Way (Still Available)
```python
# Old pagination method
result = await self.uow.sms_notifications.list_paginated(
    page=1,
    page_size=20,
    filters={"status": "sent"},
    order_by=SMSNotificationModel.created_at.desc()
)
```

### New Way (LINQ-Style)
```python
# New LINQ-style method
result = await (
    self.uow.sms_notifications.query()
    .where(lambda x: x.status == "sent")
    .order_by_descending(lambda x: x.created_at, "created_at")
    .to_paginated_list(page=1, page_size=20)
)
```

Both approaches work, but the LINQ-style provides:
- More fluent, readable syntax
- Better type safety with generics
- Familiar API for .NET developers
- More powerful querying capabilities

## Limitations

1. **Lambda Predicates**: Complex predicates are evaluated in-memory after SQL query. For best performance with large datasets, keep predicates simple or use the existing `list_paginated` method with SQL filters.

2. **Column Names**: For SQL-level sorting, you need to provide column names as strings. This is a trade-off for supporting complex lambda expressions.

3. **Transactions**: Always use queries within a `async with self.uow:` block to ensure proper transaction handling.

## Future Enhancements

Possible improvements:
- Expression tree parsing to convert lambda predicates to SQL WHERE clauses
- Better type inference for select projections
- Support for more complex join scenarios
- Compile-time validation of column names
- Query caching and optimization

## License

Part of the Notification Service project.
