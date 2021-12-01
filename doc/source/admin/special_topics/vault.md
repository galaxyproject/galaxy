# Storing secrets in the vault

Galaxy can be configured to store secrets in an external vault, which is useful for secure handling and centralization of secrets management.
In particular, information fields in the "Manage information" section of the user profile, such as a dropbox password, can be configured to be stored
in an encrypted vault instead of the database. Vault keys are generally stored as key-value pairs in a hierarchical fashion, for example:
`/galaxy/user/2/preferences/aws/client_secret`.

## Vault backends

There are currently 3 supported backends.

| Backend     | Description                                                                                                                                                                                                                                                                                                                                   |
|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| hashicorp   | Hashicorp Vault is a secrets and encryption management system. https://www.vaultproject.io/                                                                                                                                                                                                                                                   |
| custos      | Custos is an NSF-funded project, backed by open source software that provides science gateways such as Galaxy with single sign-on, group management, and management of secrets such as access keys and OAuth2 access tokens. Custos secrets managament is backed by Hashicorp's vault, but provides a convenient, always-on ReST API service. |
| database    | The database backend stores secrets in an encrypted table in the Galaxy database itself. It is a convenient way to get started with a vault, and while it supports basic key rotation, we recommend using one of the above 2 options in production.                                                                                           |

## Configuring Galaxy

The first step to using a vault is to configure the `vault_config_file` setting in `galaxy.yml`. 

```yaml
galaxy:
  # Vault config file
  # The value of this option will be resolved with respect to
  # <config_dir>.
  vault_config_file: vault_conf.yml
```

## Configuring vault_conf.yml

The vault_conf.yml file itself has two basic fields:
```yaml
type: hashicorp  # required
path_prefix: /galaxy  # optional
...
```

The `type` must be a valid backend type. The `path_prefix` property indicates the root path under which to store all vault keys. If multiple Galaxy instances are using the same Vault, a prefix can be used to identify the galaxy instance uniquely for example.
If no path_prefix is provided, the prefix defaults to `/galaxy`.

## Vault configuration for Hashicorp Vault

```yaml
type: hashicorp
path_prefix: /my_galaxy_instance
vault_address: http://localhost:8200
vault_token: galaxy_test_token
```

## Vault configuration for Custos

```yaml
type: custos
custos_host: service.staging.usecustos.org
custos_port: 30170
custos_client_id: custos-jeREDACTEDye-10000001
custos_client_sec: OGREDACTEDBSUDHn
```

## Vault configuration for database

```yaml
type: database
path_prefix: /galaxy
# Encryption keys must be valid fernet keys
# To generate a valid key:
#
# Use the ascii string value as a key
# For more details, see: https://cryptography.io/en/latest/fernet/#
encryption_keys:
  - 5RrT94ji178vQwha7TAmEix7DojtsLlxVz8Ef17KWgg=
  - iNdXd7tRjLnSqRHxuhqQ98GTLU8HUbd5_Xx38iF8nZ0=
  - IK83IXhE4_7W7xCFEtD9op0BAs11pJqYN236Spppp7g=
```

Secrets stored in the database are encrypted using Fernet keys. Therefore, all listed encryption keys must be valid fernet keys. To generate a new
Fernet key, use the following Python code:

```python
from cryptography.fernet import Fernet
Fernet.generate_key()
```
which would result in a byte string such as `b'pZDP8_baVs3oWT4597HJWCysm49j-XELONQ-EdoU0DE='`. Copy the string value as the encryption key.

If multiple encryption keys are defined, only the first key is used to encrypt secrets. The remaining keys are tried in turn during decryption. This is useful for key rotation.
We recommend periodically generating a new fernet key and rotating old keys.

## Configuring user preferences to use the vault

The `user_preferences_extra_conf.yml` can be used to automatically route secrets to a vault. An example configuration follows:

```yaml
preferences:
    googledrive:
        description: Your Google Drive account
        inputs:
            - name: client_id
              label: Client ID
              type: text
              required: True
            - name: client_secret
              label: Client Secret
              type: secret
              store: vault
              required: True
            - name: access_token
              label: Access token
              type: password
              store: vault
              required: True
            - name: refresh_token
              label: Refresh Token
              type: secret
              store: vault
              required: True
```

Note the `store: vault` property, which results in the property being stored in the vault. Note also that if you use `type: password`, the secret is sent to the client front-end,
but specifying `type: secret` would mean that the values cannot be retrieved by the client, only written to, providing an extra layer of security.
