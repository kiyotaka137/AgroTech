from llama_cpp import Llama, LlamaGrammar
from transformers import AutoTokenizer

from prompt import grammar_str, norm_prompt, sys_prompt


model_name = "Qwen/Qwen3-0.6B"
model_path = "models/Qwen3-0.6B-Q8_0.gguf"
grammar = LlamaGrammar.from_string(grammar_str)

llm = Llama(
    model_path=model_path,
    n_ctx=1024,
    n_batch=512,
    verbose=False
)

messages = [
    {"role": "user", "content": norm_prompt.format(element="Ячмень. сухой 53%")}
]

tokenizer = AutoTokenizer.from_pretrained(model_name)
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=False
)


output = llm(
    text,
    max_tokens=6,    # Максимальное количество токенов для генерации
    temperature=0.15,   # Контроль случайности (ниже = более детерминировано)
    grammar=grammar    # Применяем грамматику
)

generated_text = output["choices"][0]["text"]
print(generated_text)
