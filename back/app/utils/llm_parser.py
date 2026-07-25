"""Unified LLM JSON parser with 3-strategy extraction.

Replaces hand-written JSON parsing logic in assessment_service,
expert_selector, discussion_manager, and OCR modules with a single robust parser.
"""

import json
import logging
import re
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Chinese -> English punctuation mapping
_CHINESE_PUNCTUATION: dict[str, str] = {
    "\uff0c": ",",   # ，→,
    "\uff1a": ":",   # ：→:
    "\uff08": "(",   # （→(
    "\uff09": ")",   # ）→)
    "\u3001": ",",   # 、→,
    "\u201c": '"',   # "→"
    "\u201d": '"',   # "→"
    "\u2018": "'",   # '→'
    "\u2019": "'",   # '→'
}

_CHINESE_PUNCTUATION_PATTERN = re.compile(
    "|".join(re.escape(k) for k in _CHINESE_PUNCTUATION)
)

# Trailing comma before ] or } — LLMs frequently produce these
_TRAILING_COMMA_PATTERN = re.compile(r",\s*([}\]])")
_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:\s*[a-zA-Z0-9_-]+)?\s*([\s\S]*?)(?:\s*```|$)",
    re.IGNORECASE,
)
_INVISIBLE_CHAR_PATTERN = re.compile(r"[\ufeff\u200b\u200c\u200d]")
_NUMERIC_IDENTIFIER_PREFIX_PATTERN = re.compile(
    r'(:\s*)([^\d\s.,\]}\[{:"\']*[A-Za-z_\u4e00-\u9fff]'
    r'[^\d\s.,\]}\[{:"\']*)(-?\d+(?:\.\d+)?)(?=\s*[,}\]])'
)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before ] or } (common LLM output error)."""
    return _TRAILING_COMMA_PATTERN.sub(r"\1", text)


def _sanitize_json_candidate(text: str) -> str:
    """Normalize a candidate JSON string before parsing."""
    sanitized = _INVISIBLE_CHAR_PATTERN.sub("", text).strip()
    sanitized = normalize_chinese_punctuation(sanitized)
    # Repair numeric-ish tokens emitted as bare identifiers, e.g. perm_0.9 / 祭0.95 -> 0.9 / 0.95.
    sanitized = _NUMERIC_IDENTIFIER_PREFIX_PATTERN.sub(r"\1\3", sanitized)
    return _strip_trailing_commas(sanitized)


def _try_parse_json_candidate(
    candidate: str,
    expected_type: type,
    *,
    start_char: str,
) -> Optional[Union[dict, list]]:
    """Parse a JSON candidate, allowing extra prose before/after the payload.

    Tries multiple passes to maximise success:
    1. Raw parse: just strip invisible characters — safe for well-formed JSON.
    2. Light normalise: add Chinese punctuation replacement on top.
    3. Full sanitise: add numeric-identifier prefix repair (most destructive).
    4. start_char scan: find the first `[` / `{` and raw_decode from there.

    Each pass tries a full-doc parse first, then a raw_decode at start_char.
    """
    raw = _INVISIBLE_CHAR_PATTERN.sub("", candidate).strip()
    if not raw:
        return None

    light = normalize_chinese_punctuation(raw)
    full = _strip_trailing_commas(
        _NUMERIC_IDENTIFIER_PREFIX_PATTERN.sub(r"\1\3", light)
    )

    # Use strict=False to allow control characters inside JSON strings
    # (LLMs frequently produce these, and Python's default strict=True rejects them)
    _lenient_decoder = json.JSONDecoder(strict=False)

    passes = [raw, light, full]

    for i, text in enumerate(passes):
        # Full-document parse
        try:
            result = _lenient_decoder.decode(text)
            if isinstance(result, expected_type):
                return result
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.warning(f"Pass {i}: unexpected error in json.loads: {type(e).__name__}: {e}")

        # raw_decode at start_char
        idx = text.find(start_char)
        if idx != -1:
            try:
                result, _ = _lenient_decoder.raw_decode(text[idx:])
                if isinstance(result, expected_type):
                    return result
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.warning(f"Pass {i}: unexpected error in raw_decode: {type(e).__name__}: {e}")

    return None


def normalize_chinese_punctuation(text: str) -> str:
    """Replace Chinese punctuation with English equivalents.

    Handles: ，：（）、「」""''
    """
    return _CHINESE_PUNCTUATION_PATTERN.sub(
        lambda m: _CHINESE_PUNCTUATION[m.group()], text
    )


def parse_llm_json(response: str) -> Optional[dict]:
    """Parse JSON dict from an LLM response using 3 strategies.

    Strategies tried in order:
    1. Code block: Extract JSON from ```json ... ``` markdown blocks
    2. Raw JSON: Find first complete JSON object (non-greedy then greedy)
    3. Entire response: Try parsing the whole stripped text as JSON

    All strategies normalize Chinese punctuation before parsing.

    Returns:
        Parsed dict, or None if all strategies fail.
    """
    return _parse_llm_json_typed(response, dict)


def parse_llm_json_list(response: str) -> Optional[list]:
    """Parse JSON array from an LLM response using 3 strategies.

    Same strategy order as parse_llm_json but expects a JSON array.

    Returns:
        Parsed list, or None if all strategies fail.
    """
    return _parse_llm_json_typed(response, list)


def _diagnose_parse_failure(text: str, expected_type: type) -> str:
    """收集解析失败的关键诊断信息（只诊断，不修复）。

    用于在所有解析策略失败时，从日志直接定位 LLM 输出的具体破坏点，
    避免需要拿原始响应才能定向修复。覆盖常见破坏模式：
    - 中途插入额外 ``` 代码块分隔符（code_block_match 截断 / backtick_count > 2）
    - 未转义字符 / 控制字符（JSONDecodeError.msg + pos）
    - 结构性缺失（"Expecting ',' delimiter" 等）
    """
    start_char = "{" if expected_type is dict else "["
    code_block = _CODE_BLOCK_PATTERN.search(text)
    backtick_count = text.count("```")
    decoder = json.JSONDecoder(strict=False)

    candidates: list[tuple[str, str]] = []
    if code_block:
        candidates.append(("code_block_inner", code_block.group(1).strip()))
    candidates.append(("full_text", text))

    errors: list[str] = []
    for label, candidate in candidates:
        idx = candidate.find(start_char)
        payloads: list[tuple[str, str]] = [("decode", candidate)]
        if idx != -1:
            payloads.append(("raw_decode", candidate[idx:]))
        for method, payload in payloads:
            try:
                if method == "decode":
                    decoder.decode(payload)
                else:
                    decoder.raw_decode(payload)
            except json.JSONDecodeError as e:
                snippet = payload[e.pos:e.pos + 20] if 0 <= e.pos < len(payload) else "EOF"
                errors.append(f"{label}.{method}: {e.msg} at pos {e.pos} near {snippet!r}")
                break
            except Exception as e:  # pragma: no cover - 防御性
                errors.append(f"{label}.{method}: {type(e).__name__}: {e}")
                break

    return (
        f"code_block_match={bool(code_block)}, "
        f"backtick_count={backtick_count}, "
        f"errors={errors}"
    )


def _parse_llm_json_typed(response: str, expected_type: type) -> Optional[Union[dict, list]]:
    """Generic typed LLM JSON parser"""
    if not response or not response.strip():
        return None

    text = response.strip()
    start_char = "{" if expected_type is dict else "["

    # Strategy 1: ```json code block (regex)
    code_block_match = _CODE_BLOCK_PATTERN.search(text)
    if code_block_match:
        result = _try_parse_json_candidate(
            code_block_match.group(1),
            expected_type,
            start_char=start_char,
        )
        if result is not None:
            return result
        logger.debug("JSON parse failed in code block (regex)")

    # Strategy 1b: Manual code block stripping (fallback for encoding issues)
    if text.startswith("```"):
        newline_idx = text.find("\n")
        if newline_idx != -1:
            # Find closing ```
            close_idx = text.rfind("```")
            if close_idx > newline_idx:
                inner = text[newline_idx + 1:close_idx]
            else:
                inner = text[newline_idx + 1:]
            result = _try_parse_json_candidate(inner, expected_type, start_char=start_char)
            if result is not None:
                return result
            logger.debug("JSON parse failed in manual code block strip")

    # Strategy 2: Raw JSON in text
    if expected_type is dict:
        # 2a: Non-greedy match (first { ... })
        raw_match = re.search(r"\{.*?\}", text, re.DOTALL)
        if raw_match:
            result = _try_parse_json_candidate(
                raw_match.group(0),
                dict,
                start_char="{",
            )
            if result is not None:
                return result

        # 2b: Greedy fallback (first { to last })
        greedy_match = re.search(r"\{.*\}", text, re.DOTALL)
        if greedy_match:
            result = _try_parse_json_candidate(
                greedy_match.group(0),
                dict,
                start_char="{",
            )
            if result is not None:
                return result
            logger.debug("JSON parse failed in raw search")
    else:
        # For list type: greedy match first [ to last ]
        list_match = re.search(r"\[.*\]", text, re.DOTALL)
        if list_match:
            result = _try_parse_json_candidate(list_match.group(0), list, start_char="[")
            if result is not None:
                return result
        # Fallback: try the full text
        result = _try_parse_json_candidate(text, list, start_char="[")
        if result is not None:
            return result
        logger.debug("JSON parse failed in list extraction")

    # Strategy 3: Entire response
    result = _try_parse_json_candidate(text, expected_type, start_char=start_char)
    if result is not None:
        return result

    # Log details when all strategies fail to aid debugging
    logger.warning(
        f"All JSON parse strategies failed for expected_type={expected_type.__name__}. "
        f"Response length: {len(text)}, first 300 chars: {text[:300]!r}. "
        f"Diagnosis: {_diagnose_parse_failure(text, expected_type)}"
    )

    return None
