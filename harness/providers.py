import os
from dataclasses import dataclass, field

from openai import OpenAI

DEFAULT_OLLAMA_HOST = "http://localhost:11434"


@dataclass
class OpenRouterProvider:
    model: str
    client: OpenAI = field(init=False)

    def __post_init__(self) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY environment variable not set")
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


@dataclass
class OllamaProvider:
    model: str
    host: str = DEFAULT_OLLAMA_HOST
    client: OpenAI = field(init=False)

    def __post_init__(self) -> None:
        self.client = OpenAI(base_url=f"{self.host}/v1", api_key="ollama")


Provider = OpenRouterProvider | OllamaProvider


def resolve(model: str, ollama_host: str = DEFAULT_OLLAMA_HOST) -> Provider:
    if model.startswith("ollama/"):
        return OllamaProvider(model=model[len("ollama/"):], host=ollama_host)
    return OpenRouterProvider(model=model)
