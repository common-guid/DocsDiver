# Authentication System

The application uses **JWT (JSON Web Tokens)** for stateless authentication.

## Roles & Permissions
*   **Guest:** Can view public pages.
*   **User:** Can manage own profile, view own data.
*   **Admin:** Full access to all resources.

## Registration
Users sign up via `/api/register`. No email verification required in dev.

## Login
POST `/api/login` with `username` and `password`. Returns `access_token`.
