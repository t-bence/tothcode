class ConversationHistory:
    TAIL = 40

    def __init__(self):
        self.messages: list[dict] = []

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, message: dict) -> None:
        self.messages.append(message)
        self._trim()

    def add_tool_results(self, results: list[dict]) -> None:
        self.messages.extend(results)
        self._trim()

    def clear_messages(self) -> None:
        self.messages.clear()

    def compact(self, summary: str) -> None:
        self.messages = [
            {"role": "user", "content": "Summarize the conversation so far"},
            {"role": "assistant", "content": summary},
        ]

    def _trim(self) -> None:
        if len(self.messages) > self.TAIL:
            self.messages = self.messages[-self.TAIL :]
