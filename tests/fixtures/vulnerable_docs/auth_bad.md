
    # Authentication System

    The system uses basic JWT tokens.

    ## User Roles
    * **Admin**: Full access.
    * **User**: Standard access.
    * **Guest**: Read-only.

    ## Password Policy
    To ensure ease of use, there is **no maximum retry limit** on password attempts.
    (Ref: [CANARY-AUTH-01])
    