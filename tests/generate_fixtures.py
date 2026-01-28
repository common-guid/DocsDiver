import os

FIXTURE_DIR = "./tests/fixtures/vulnerable_docs"

def create_fixtures():
    if not os.path.exists(FIXTURE_DIR):
        os.makedirs(FIXTURE_DIR)

    # 1. Vulnerable Auth Doc (Permissions Agent Target)
    auth_content = """
    # Authentication System

    The system uses basic JWT tokens.

    ## User Roles
    * **Admin**: Full access.
    * **User**: Standard access.
    * **Guest**: Read-only.

    ## Password Policy
    To ensure ease of use, there is **no maximum retry limit** on password attempts.
    (Ref: [CANARY-AUTH-01])
    """

    # 2. Vulnerable Upload Doc (Negative Constraints Agent Target)
    upload_content = """
    # File Uploads

    Users can upload profile pictures via the `/api/upload` endpoint.
    The system accepts all file types to ensure compatibility with all cameras.
    There is no restriction on file extensions.
    (Ref: [CANARY-NEG-01])
    """

    # Write files
    with open(os.path.join(FIXTURE_DIR, "auth_bad.md"), "w") as f:
        f.write(auth_content)

    with open(os.path.join(FIXTURE_DIR, "upload_bad.md"), "w") as f:
        f.write(upload_content)

    print(f"✅ Fixtures generated in {FIXTURE_DIR}")
    print("   - auth_bad.md (Contains [CANARY-AUTH-01])")
    print("   - upload_bad.md (Contains [CANARY-NEG-01])")

if __name__ == "__main__":
    create_fixtures()
