from __future__ import annotations
import json, os
from typing import Any, Dict, Optional, Tuple

from llama_cpp import Llama, LlamaGrammar


MODEL_NAME = ""

class LLMInferenceError(RuntimeError):
    pass

# pip install llama-cpp-python jsonschema jsonschema-gbnf  # (jsonschema-gbnf опционально, но очень желательно)

class LLMInferenceError(RuntimeError):
    pass

def _compile_schema_to_gbnf(schema: Dict[str, Any]) -> str:  # todo: не работает нахуй можно нахуй удалять
    """
    Пытаемся конвертировать JSON Schema в GBNF:
    - если доступен пакет jsonschema_gbnf — используем его (полноценная конвертация)
    - иначе используем минимальный встроенный конвертер для подмножества:
      object + properties (string/number/boolean) + enum, required, additionalProperties=false
    """
    # Попытка полнофункционального конвертера
    try:
        from jsonschema_gbnf import to_gbnf  # type: ignore
        gbnf = to_gbnf(schema)
        return gbnf
    except Exception:
        pass

    # Мини-конвертер (подмножество JSON Schema)
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def gbnf_for_type(sub: Dict[str, Any]) -> str:
        t = sub.get("type")
        if "enum" in sub:
            # строковые enum
            choices = sub["enum"]
            alts = " | ".join(f'"{esc(str(c))}"' for c in choices)
            return f"({alts})"
        if t == "string":
            return 'string'
        if t == "number":
            return 'number'
        if t == "integer":
            return 'integer'
        if t == "boolean":
            return '( "true" | "false" )'
        if t == "null":
            return '"null"'
        if t == "array":
            items = sub.get("items", {"type": "string"})
            inner = gbnf_for_type(items)
            return f'"[" _ ( {inner} ( _ "," _ {inner} )* )? _ "]"'
        if t == "object" or ("properties" in sub):
            return gbnf_for_object(sub)
        # по умолчанию строка
        return 'string'

    def gbnf_for_object(obj_schema: Dict[str, Any]) -> str:
        props: Dict[str, Any] = obj_schema.get("properties", {})
        required = set(obj_schema.get("required", []))
        additional = obj_schema.get("additionalProperties", True)

        # Порядок ключей фиксируем (детерминированно): required сначала, затем опциональные
        ordered_keys = list(required) + [k for k in props.keys() if k not in required]

        # Правило для одной пары "ключ: значение"
        parts = []
        for i, k in enumerate(ordered_keys):
            v = props[k]
            kv_rule = f'"{esc(k)}" _ ":" _ ' + gbnf_for_type(v)
            parts.append(kv_rule)
        # опциональные: разрешим их отсутствие с запятыми корректно
        # Для простоты: требуем точный набор ключей, если additionalProperties=false.
        # Иначе позволим ноль ключей.
        if not additional:
            if parts:
                joined = ' ( _ "," _ '.join(parts) + ' ) '
                return f'"{{" _ {joined} _ "}}"'
            else:
                return '"{" _ "}"'
        else:
            # простой объект без ограничений
            return '"{" _ ( string _ ":" _ value ( _ "," _ string _ ":" _ value )* )? _ "}"'

    # Базовые нетерминалы для строк/чисел/пробелов/значений JSON
    core = r'''
json  ::= object
object ::= "{" _ ( string _ ":" _ value ( _ "," _ string _ ":" _ value )* )? _ "}"
array  ::= "[" _ ( value ( _ "," _ value )* )? _ "]"
value  ::= string | number | integer | object | array | "true" | "false" | "null"
string ::= "\"" chars "\""
chars  ::= ( [^"\\] | escape )*
escape ::= "\\" ( ["\\/bfnrt] | "u" [0-9a-fA-F]{4} )
number ::= integer frac? exp?
integer ::= "-"? ( "0" | [1-9] [0-9]* )
frac   ::= "." [0-9]+
exp    ::= [eE] [+\-]? [0-9]+
_      ::= ([ \t\n\r ] )*
'''

    # Если верхний тип — объект с properties и additionalProperties=false — генерим строгую грамматику объекта
    if schema.get("type") == "object" or "properties" in schema:
        obj_rule = gbnf_for_object(schema)
        gbnf = core + "\njson ::= " + obj_rule + "\n"
        return gbnf
    else:
        # иначе просто строгий JSON любого типа (минимально)
        return core + "\n"

def llm_infer_with_schema_local(
    prompt: str,
    schema: Dict[str, Any],
    *,
    model_path: str = "models/Qwen2.5-0.5B-Instruct-f16.gguf",
    n_ctx: int = 2048,
    n_threads: Optional[int] = None,
    max_new_tokens: int = 128,
    temperature: float = 0.0,
    top_p: float = 1.0,
    seed: Optional[int] = 42,
    system_prompt: str = "Отвечай строго валидным JSON в соответствии со схемой.",
    validate: bool = True,
    reuse_llm: Optional[Llama] = None,
) -> Tuple[Dict[str, Any], Llama]:
    """
    Возвращает (json_object, llm_instance). llm можно переиспользовать между вызовами.
    """
    if not os.path.exists(model_path):
        raise LLMInferenceError(f"Модель не найдена: {model_path}")

    gbnf = _compile_schema_to_gbnf(schema)
    grammar = LlamaGrammar.from_string(gbnf)

    llm = reuse_llm or Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=(n_threads or max(1, (os.cpu_count() or 4) - 1)),
        n_gpu_layers=0,
        verbose=False,
        seed=seed,
    )

    # Простой «инструктивный» формат
    full_prompt = f"{system_prompt}\n\nПользователь: {prompt}\nПомощник:"

    out = llm.create_completion(
        prompt=full_prompt,
        max_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        grammar=grammar,          # ← жёсткое ограничение по грамматике (из схемы)
        stop=["\n\nПользователь:"],  # на всякий случай, чтобы не «пролезал» лишний текст
    )

    text = out["choices"][0]["text"].strip()

    # Парсим JSON
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMInferenceError(f"Ответ не JSON: {e}\nТекст: {text[:400]}")

    # Опционально валидируем той же схемой
    if validate:
        try:
            import jsonschema
            jsonschema.validate(obj, schema)
        except Exception as e:
            raise LLMInferenceError(f"JSON не прошёл валидацию схемой: {e}\nТекст: {text[:400]}")

    return obj, llm


if __name__ == "__main__":
    SCHEMA = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["кормить", "доить", "лечить"]},
            "priority": {"type": "integer", "minimum": 0, "maximum": 5},
            "ok": {"type": "boolean"}
        },
        "required": ["action"],
        "additionalProperties": False
    }

    result, llm = llm_infer_with_schema_local(
        prompt="Выбери действие для коровы в стойле №7 и оцени приоритет.",
        schema=SCHEMA,
        max_new_tokens=96,
        temperature=0.0,  # детерминированный greedy
        top_p=1.0
    )
    print(result)
    # {'action': 'кормить', 'priority': 2, 'ok': true}
