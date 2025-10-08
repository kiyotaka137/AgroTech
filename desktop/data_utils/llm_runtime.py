# llm_runtime.py
from pathlib import Path
from threading import Lock
from llama_cpp import Llama

_MODEL_PATH = Path("models/Qwen3-0.6B-Q8_0.gguf")
_LLM = None
_LOCK = Lock()

def init_llm_in_main_thread(n_ctx=1024, n_batch=128, **kw):
    """
    ВЫЗВАТЬ ОДИН РАЗ в главном потоке (до старта QThread'ов).
    """
    global _LLM
    with _LOCK:
        if _LLM is None:
            if not _MODEL_PATH.is_file():
                raise FileNotFoundError(_MODEL_PATH.resolve())
            _LLM = Llama(
                model_path=str(_MODEL_PATH),
                n_ctx=n_ctx,
                n_batch=n_batch,  # начинать с поменьше
                verbose=False,
                **kw
            )
    return _LLM

def get_llm():
    """
    В воркерах/любой логике — только получать уже готовый объект.
    Не создаёт заново.
    """
    if _LLM is None:
        raise RuntimeError("LLM не инициализирован. Вызови init_llm_in_main_thread() при старте приложения.")
    return _LLM
