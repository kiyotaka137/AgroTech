from llama_cpp import Llama, LlamaGrammar
from transformers import AutoTokenizer

from .prompt import grammar_str, norm_prompt, sys_prompt



model_name = "Qwen/Qwen3-0.6B"
model_path = "models/Qwen3-0.6B-Q8_0.gguf"

def llm_cleaning(batch):
    grammar = LlamaGrammar.from_string(grammar_str)

    llm = Llama(
        model_path=model_path,
        n_ctx=1024,
        n_batch=512,
        verbose=False
    )

    messages = []

    for elem in batch:
        messages.append([{"role": "user", "content": norm_prompt.format(element=elem)}])

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    outputs = []

    for t in text:
        output = llm(
            t,
            max_tokens=6,    # Максимальное количество токенов для генерации
            temperature=0.15,   # Контроль случайности (ниже = более детерминировано)
            grammar=grammar    # Применяем грамматику
        )
        outputs.append(output["choices"][0]["text"])

    generated_text = outputs
    return {j : i for i, j in zip(generated_text, batch)} # todo: доделать побатчевую

if __name__ == '__main__':
    llm_cleaning(["подсолнечник", "Жмых льняной. 36%, ЭНАПКХ", "зерносмесь18,500"])