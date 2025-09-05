# Split Service - Debt Management API

A microservice for managing groups, expenses, debts, and settlements between users.

## Features

- 👥 **Groups Management**: Create and manage groups of users
- 💸 **Expense Tracking**: Add expenses with automatic debt calculation
- 📊 **Debt Optimization**: Minimize transactions with optimized settlements
- 🔐 **JWT Authentication**: Secure API with JWT tokens
- 👑 **Admin Permissions**: Group admins can manage categories and members
- 📱 **Category Organization**: Organize expenses by categories within groups
- 🏷️ **User-Friendly URLs**: Auto-generated slugs from group names for readable URLs

## Tech Stack

- **FastAPI**: High-performance async web framework
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Database (easily configurable for PostgreSQL/MySQL)
- **Pydantic**: Data validation and serialization
- **PyJWT**: JWT token handling

## Installation

1. Clone the repository
2. Navigate to the split_service directory
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Service

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`

## API Documentation

Once running, visit `http://localhost:8001/docs` for interactive Swagger documentation.

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

The JWT payload should contain:
```json
{
  "user_id": "user-uuid",
  "email": "user@example.com",
  "phone_number": "09123456789",
  "exp": 1757095078
}
```

## API Endpoints

### Groups

- `POST /groups/` - Create a new group
- `GET /groups/` - Get user's groups
- `GET /groups/{group_slug}` - Get group details with members
- `PATCH /groups/{group_slug}` - Update group (admin only)
- `DELETE /groups/{group_slug}` - Delete group (admin only)

### Group Members

- `POST /groups/{group_slug}/members` - Add member to group (admin only)
- `DELETE /groups/{group_slug}/members/{user_id}` - Remove member from group

### Categories

- `POST /groups/{group_slug}/categories` - Create category (admin only)
- `GET /groups/{group_slug}/categories` - Get group categories
- `PATCH /groups/{group_slug}/categories/{category_id}` - Update category (admin only)
- `DELETE /groups/{group_slug}/categories/{category_id}` - Delete category (admin only)

### Expenses

- `POST /expenses/groups/{group_slug}` - Create expense with shares
- `GET /expenses/groups/{group_slug}` - Get group expenses
- `GET /expenses/categories/{category_id}` - Get category expenses
- `GET /expenses/{expense_id}` - Get expense details
- `PATCH /expenses/{expense_id}` - Update expense
- `DELETE /expenses/{expense_id}` - Delete expense

### Settlements

- `POST /settlements/groups/{group_slug}` - Create manual settlement
- `GET /settlements/groups/{group_slug}` - Get group settlements
- `GET /settlements/groups/{group_slug}/debts` - Get debt summary
- `GET /settlements/groups/{group_slug}/optimize` - Get optimized settlement suggestions

## Database Schema

### Groups
- `id`: UUID (Primary Key)
- `name`: String (Group name)
- `slug`: String (Auto-generated URL-friendly identifier, unique)
- `image_url`: String (Optional group image)
- `created_by`: UUID (Creator user ID)
- `rounding_option`: Enum (up/down/none)
- `created_at`: DateTime

### Group Members
- `id`: UUID (Primary Key)
- `group_id`: UUID (Foreign Key)
- `user_id`: UUID (User ID from user service)
- `is_admin`: Boolean
- `joined_at`: DateTime

### Expenses
- `id`: UUID (Primary Key)
- `group_id`: UUID (Foreign Key)
- `group_category_id`: UUID (Foreign Key)
- `title`: String
- `amount`: Decimal
- `paid_by`: UUID (User ID)
- `description`: Text (Optional)
- `receipt_url`: String (Optional)
- `date`: DateTime
- `created_at`: DateTime

### Expense Shares
- `id`: UUID (Primary Key)
- `expense_id`: UUID (Foreign Key)
- `user_id`: UUID (User ID)
- `share_amount`: Decimal
- `is_settled`: Boolean

### Settlements
- `id`: UUID (Primary Key)
- `group_id`: UUID (Foreign Key)
- `from_user_id`: UUID (User ID)
- `to_user_id`: UUID (User ID)
- `amount`: Decimal
- `settled_at`: DateTime

## User-Friendly URLs (Slugs)

The service automatically generates unique, readable slugs from group names for all URLs. This replaces UUIDs with human-readable identifiers.

### How Slugs Work

- **Auto-generated**: Slugs are created automatically from group names
- **Unique**: If a slug already exists, a number is appended (e.g., `weekend-trip-1`)
- **URL-friendly**: Special characters are removed, spaces become hyphens
- **Immutable**: Slugs cannot be manually changed by users

### Examples

| Group Name | Generated Slug | URL |
|------------|----------------|-----|
| "Weekend Trip" | `weekend-trip` | `/groups/weekend-trip` |
| "Office Lunch" | `office-lunch` | `/groups/office-lunch` |
| "Weekend Trip" (duplicate) | `weekend-trip-1` | `/groups/weekend-trip-1` |
| "My Awesome Group!" | `my-awesome-group` | `/groups/my-awesome-group` |

### Slug Generation Rules

- Convert to lowercase
- Replace spaces and underscores with hyphens
- Remove special characters (keep only letters, numbers, hyphens)
- Remove multiple consecutive hyphens
- Trim leading/trailing hyphens
- Maximum 100 characters
- Fallback to UUID-based slug for edge cases

## Permissions

- **Group Creation**: Any authenticated user
- **Group Admin Operations**: Only group admins can update/delete groups, manage categories, add/remove members
- **Expense Management**: Expense creators and group admins can edit/delete expenses
- **Settlement**: Users involved in settlements can create them

## Debt Optimization

The service includes an algorithm to minimize the number of transactions needed to settle all debts within a group. This is achieved by:

1. Calculating net balances for each member
2. Matching creditors with debtors
3. Minimizing transaction count while maintaining accuracy

Use `GET /expenses/groups/{group_id}/optimize` to get settlement suggestions.

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

The service uses SQLAlchemy with automatic table creation. For production, consider using Alembic for migrations.

### Environment Variables

- `SECRET_KEY`: JWT secret key (default: "your_secret_key")

## License

This project is part of a microservices architecture for debt management.
