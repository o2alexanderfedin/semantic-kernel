# Copyright (c) Microsoft. All rights reserved.


import asyncio
from typing import Annotated

from semantic_kernel.connectors.ai.function_call_behavior import FunctionCallBehavior
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.core_plugins.time_plugin import TimePlugin
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.kernel import Kernel


class WeatherPlugin:
    """A sample plugin that provides weather information for cities."""

    @kernel_function(name="get_weather_for_city", description="Get the weather for a city")
    def get_weather_for_city(self, city: Annotated[str, "The input city"]) -> Annotated[str, "The output is a string"]:
        if city == "Boston":
            return "61 and rainy"
        elif city == "London":
            return "55 and cloudy"
        elif city == "Miami":
            return "80 and sunny"
        elif city == "Paris":
            return "60 and rainy"
        elif city == "Tokyo":
            return "50 and sunny"
        elif city == "Sydney":
            return "75 and sunny"
        elif city == "Tel Aviv":
            return "80 and sunny"
        else:
            return "31 and snowing"


async def main():
    kernel = Kernel()

    use_azure_openai = False
    service_id = "function_calling"
    if use_azure_openai:
        # Please make sure your AzureOpenAI Deployment allows for function calling
        ai_service = AzureChatCompletion(
            service_id=service_id,
        )
    else:
        ai_service = OpenAIChatCompletion(
            service_id=service_id,
            ai_model_id="gpt-3.5-turbo-1106",
        )
    kernel.add_service(ai_service)

    kernel.add_plugin(TimePlugin(), plugin_name="time")
    kernel.add_plugin(WeatherPlugin(), plugin_name="weather")

    # Example 1: Use automated function calling with a non-streaming prompt
    print("========== Example 1: Use automated function calling with a non-streaming prompt ==========")
    settings: OpenAIChatPromptExecutionSettings = kernel.get_prompt_execution_settings_from_service_id(
        service_id=service_id
    )
    settings.function_call_behavior = FunctionCallBehavior.EnableFunctions(
        auto_invoke=True, filters={"include_plugin": ["weather", "time"]}
    )

    print(
        await kernel.invoke_prompt(
            function_name="prompt_test",
            plugin_name="weather_test",
            prompt="Given the current time of day and weather, what is the likely color of the sky in Boston?",
            settings=settings,
        )
    )

    # Example 2: Use automated function calling with a streaming prompt
    print("========== Example 2: Use automated function calling with a streaming prompt ==========")
    settings: OpenAIChatPromptExecutionSettings = kernel.get_prompt_execution_settings_from_service_id(
        service_id=service_id
    )
    settings.function_call_behavior = FunctionCallBehavior.EnableFunctions(
        auto_invoke=True, filters={"include_plugin": ["weather", "time"]}
    )

    result = kernel.invoke_prompt_stream(
        function_name="prompt_test",
        plugin_name="weather_test",
        prompt="Given the current time of day and weather, what is the likely color of the sky in Boston?",
        settings=settings,
    )

    async for message in result:
        print(str(message[0]), end="")
    print("")

    # Example 3: Use manual function calling with a non-streaming prompt
    print("========== Example 3: Use manual function calling with a non-streaming prompt ==========")

    chat: OpenAIChatCompletion | AzureChatCompletion = kernel.get_service(service_id)
    chat_history = ChatHistory()
    settings: OpenAIChatPromptExecutionSettings = kernel.get_prompt_execution_settings_from_service_id(
        service_id=service_id
    )
    settings.function_call_behavior = FunctionCallBehavior.EnableFunctions(
        auto_invoke=True, filters={"include_plugin": ["weather", "time"]}
    )
    chat_history.add_user_message(
        "Given the current time of day and weather, what is the likely color of the sky in Boston?"
    )

    while True:
        # The result is a list of ChatMessageContent objects, grab the first one
        result = await chat.get_chat_message_contents(chat_history=chat_history, settings=settings)
        result = result[0]

        if result.content:
            print(result.content)

        if not result.items or not any(isinstance(item, FunctionCallContent) for item in result.items):
            break

        chat_history.add_message(result)
        await chat._process_function_calls(
            result=result,
            kernel=kernel,
            chat_history=chat_history,
            arguments=KernelArguments(),
        )


if __name__ == "__main__":
    asyncio.run(main())
