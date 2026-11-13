# API tokens

API tokens let scripts call the Acme API as the user who created the token.

## Creating a token

Go to **Settings > API tokens** and select **New token**. Copy the token when it is shown; it is not shown again.

```bash
# List the notebooks you can see
curl -H "Authorization: Bearer $ACME_TOKEN" https://api.acme.example/v1/notebooks
```

## Token scopes

A token has the same access as its owner. A token can be limited to read-only access when it is created.

## Expiry

Tokens expire after 90 days. An Admin can revoke any token from **Settings > Members**.
