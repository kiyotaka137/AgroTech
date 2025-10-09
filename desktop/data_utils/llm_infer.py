# pip install -U outlines transformers torch

import outlines
from transformers import AutoTokenizer, AutoModelForCausalLM

from .prompt import grammar_str, sys_prompt, norm_prompt


MODEL_NAME = "Qwen/Qwen3-0.6B"   # при желании поменяй на свою

GRAMMAR_REGEX = grammar_str

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
# model = models.transformers(MODEL_ID, trust_remote_code=True)
# gen = generator.regex(model, GRAMMAR_REGEX)

model = outlines.from_transformers(
    AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="auto"),
    AutoTokenizer.from_pretrained(MODEL_NAME)
)

def _build_chat(user_text: str) -> str:
    """Собираем chat-подсказку под Qwen через шаблон токенайзера."""
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user",   "content": user_text},
    ]
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def llm_cleaning(batch):
    """
    batch: List[str] — сырые элементы.
    Возвращает dict {original: normalized}
    """
    outputs = []
    for elem in batch:
        prompt_text = _build_chat(norm_prompt.format(element=elem))
        sentiment = model(
            prompt_text,
            GRAMMAR_REGEX
        )
        outputs.append(sentiment.strip())
        print(sentiment)
    return {orig: norm for orig, norm in zip(batch, outputs)}


if __name__ == "__main__":
    demo = ["подсолнечник", "Жмых льняной. 36%, ЭНАПКХ", "зерносмесь18,500"]
    print(llm_cleaning(demo))
