# API Reference & Boundaries

## General
Base URL: `https://api.example.com/v1`

## Endpoints

### User Profile
*   `GET /users/me`: Get own profile.
*   `PUT /users/me`: Update profile.

### File Uploads
*   `POST /upload`: Uploads file to S3 bucket `user-uploads`.
*   **Boundary:** Data moves from Client (Public) to AWS S3 (Internal/Third-party).

### Admin Exports
*   `GET /admin/export`: Exports all user data to CSV.
