"""Credentials resolution for tool testing."""

from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
    List,
)


class CredentialsResolver(ABC):
    """Abstract interface for resolving credentials to environment variables.

    This provides a unified way to resolve credentials from different sources
    (e.g., vault for production, embedded dict for tests) into environment
    variable dictionaries suitable for tool execution.
    """

    @abstractmethod
    def resolve(self, requirements: List[Any]) -> List[Dict[str, str]]:
        """Resolve credentials to environment variable dicts.

        Args:
            requirements: List of credential requirements from the tool definition.

        Returns:
            List of environment variable dictionaries with 'name' and 'value' keys.
        """
        pass


class TestCredentialsResolver(CredentialsResolver):
    """Resolver for test mode credentials.

    Used during tool testing (e.g., via planemo) where credentials are provided
    as embedded dictionaries in job parameters rather than from the vault.
    """

    def __init__(self, test_credentials: Dict[str, Dict[str, Any]]):
        """Initialize with test credentials dictionary.

        Args:
            test_credentials: Dict mapping service names to credential dicts
                containing 'secrets' and 'variables' sub-dicts.
        """
        self.test_credentials = test_credentials

    def resolve(self, requirements: List[Any]) -> List[Dict[str, str]]:
        """Resolve test credentials to environment variables.

        Args:
            requirements: List of credential requirements from the tool definition.
                Each requirement should have 'name', 'secrets', and 'variables' attributes.

        Returns:
            List of environment variable dictionaries with 'name' and 'value' keys.
        """
        env_variables: List[Dict[str, str]] = []
        for credential in requirements:
            if credential.name in self.test_credentials:
                service_creds = self.test_credentials[credential.name]
                for secret in credential.secrets:
                    value = service_creds.get("secrets", {}).get(secret.name, "")
                    env_variables.append({"name": secret.inject_as_env, "value": value})
                for variable in credential.variables:
                    value = service_creds.get("variables", {}).get(variable.name, "")
                    env_variables.append({"name": variable.inject_as_env, "value": value})
        return env_variables
