# Placeholder LLM helper. Swap with LangChain LLMs or OpenAI calls.
class LanguageModel:
    def generate(self, prompt: str) -> str:
        return f"LLM response to: {prompt}"
