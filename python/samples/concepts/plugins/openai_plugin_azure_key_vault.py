# Copyright (c) Microsoft. All rights reserved.


import os

import httpx
from aiohttp import ClientSession
from azure_key_vault_settings import AzureKeyVaultSettings

from semantic_kernel import Kernel
from semantic_kernel.connectors.openai_plugin import OpenAIAuthenticationType, OpenAIFunctionExecutionParameters
from semantic_kernel.functions import KernelPlugin
from semantic_kernel.functions.kernel_arguments import KernelArguments


async def add_secret_to_key_vault(kernel: Kernel, plugin: KernelPlugin):
    """Adds a secret to the Azure Key Vault."""
    arguments = KernelArguments()
    arguments["secret_name"] = "Foo"
    arguments["api_version"] = "7.0"
    arguments["value"] = "Bar"
    arguments["enabled"] = True
    result = await kernel.invoke(
        function=plugin["SetSecret"],
        arguments=arguments,
    )

    print(f"Secret added to Key Vault: {result}")


async def get_secret_from_key_vault(kernel: Kernel, plugin: KernelPlugin):
    """Gets a secret from the Azure Key Vault."""
    arguments = KernelArguments()
    arguments["secret_name"] = "Foo"
    arguments["api_version"] = "7.0"
    result = await kernel.invoke(
        function=plugin["GetSecret"],
        arguments=arguments,
    )

    print(f"Secret retrieved from Key Vault: {result}")


class OpenAIAuthenticationProvider:
    """A Sample Authentication Provider for an OpenAI/OpenAPI plugin"""

    def __init__(
        self, oauth_values: dict[str, dict[str, str]] | None = None, credentials: dict[str, str] | None = None
    ):
        """Initializes the OpenAIAuthenticationProvider."""
        self.oauth_values = oauth_values or {}
        self.credentials = credentials or {}

    async def authenticate_request(
        self,
        plugin_name: str,
        openai_auth_config: OpenAIAuthenticationType,
        **kwargs,
    ) -> dict[str, str] | None:
        """An example of how to authenticate a request as part of an auth callback."""
        if openai_auth_config.type == OpenAIAuthenticationType.NoneType:
            return

        scheme = ""
        credential = ""

        if openai_auth_config.type == OpenAIAuthenticationType.OAuth:
            if not openai_auth_config.authorization_url:
                raise ValueError("Authorization URL is required for OAuth.")

            domain = openai_auth_config.authorization_url.host
            domain_oauth_values = self.oauth_values.get(domain)

            if not domain_oauth_values:
                raise ValueError("No OAuth values found for the provided authorization URL.")

            values = domain_oauth_values | {"scope": openai_auth_config.scope or ""}

            content_type = openai_auth_config.authorization_content_type or "application/x-www-form-urlencoded"
            async with ClientSession() as session:
                authorization_url = str(openai_auth_config.authorization_url)

                if content_type == "application/x-www-form-urlencoded":
                    response = await session.post(authorization_url, data=values)
                elif content_type == "application/json":
                    response = await session.post(authorization_url, json=values)
                else:
                    raise ValueError(f"Unsupported authorization content type: {content_type}")

                response.raise_for_status()

                token_response = await response.json()
                scheme = token_response.get("token_type", "")
                credential = token_response.get("access_token", "")

        else:
            token = openai_auth_config.verification_tokens.get(plugin_name, "")
            scheme = openai_auth_config.authorization_type.value
            credential = token

        auth_header = f"{scheme} {credential}"
        return {"Authorization": auth_header}


async def main():
    # This example demonstrates how to connect an Azure Key Vault plugin to the Semantic Kernel.
    # To use this example, there are a few requirements:
    # 1. Register a client application with the Microsoft identity platform.
    # https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app
    #
    # 2. Create an Azure Key Vault
    # https://learn.microsoft.com/en-us/azure/key-vault/general/quick-create-portal
    # Please make sure to configure the AKV with a Vault Policy, instead of the default RBAC policy
    # This is because you will need to assign the Key Vault access policy to the client application you
    # registered in step 1. You should give the client application the "Get," "List," and "Set"
    # permissions for secrets.
    #
    # 3. Set your Key Vault endpoint, client ID, and client secret as user secrets using in your .env file:
    # AZURE_KEY_VAULT_ENDPOINT = ""
    # AZURE_KEY_VAULT_CLIENT_ID = ""
    # AZURE_KEY_VAULT_CLIENT_SECRET = ""
    #
    # 4. Replace your tenant ID with the "TENANT_ID" placeholder in
    # python/samples/kernel-syntax-examples/resources/akv-openai.json

    azure_keyvault_settings = AzureKeyVaultSettings.create()
    client_id = azure_keyvault_settings.client_id
    client_secret = azure_keyvault_settings.client_secret.get_secret_value()
    endpoint = azure_keyvault_settings.endpoint

    authentication_provider = OpenAIAuthenticationProvider(
        {
            "login.microsoftonline.com": {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            }
        }
    )

    kernel = Kernel()

    openai_spec_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "resources", "open_ai_plugins", "akv-openai.json"
    )
    with open(openai_spec_file) as file:
        openai_spec = file.read()

    http_client = httpx.AsyncClient()

    plugin = await kernel.add_plugin_from_openai(
        plugin_name="AzureKeyVaultPlugin",
        plugin_str=openai_spec,
        execution_parameters=OpenAIFunctionExecutionParameters(
            http_client=http_client,
            auth_callback=authentication_provider.authenticate_request,
            server_url_override=endpoint,
            enable_dynamic_payload=True,
        ),
    )

    await add_secret_to_key_vault(kernel, plugin)
    await get_secret_from_key_vault(kernel, plugin)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
