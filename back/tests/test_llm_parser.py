"""Tests for the unified LLM JSON parser."""

import pytest

from app.utils.llm_parser import (
    normalize_chinese_punctuation,
    parse_llm_json,
    parse_llm_json_list,
)


class TestNormalizeChinesePunctuation:
    """Tests for Chinese punctuation normalization."""

    def test_comma(self) -> None:
        assert normalize_chinese_punctuation("a，b") == "a,b"

    def test_colon(self) -> None:
        assert normalize_chinese_punctuation("key：value") == "key:value"

    def test_parentheses(self) -> None:
        assert normalize_chinese_punctuation("（test）") == "(test)"

    def test_enumeration_comma(self) -> None:
        assert normalize_chinese_punctuation("a、b、c") == "a,b,c"

    def test_curly_quotes(self) -> None:
        assert normalize_chinese_punctuation("\u201chello\u201d") == '"hello"'

    def test_single_curly_quotes(self) -> None:
        assert normalize_chinese_punctuation("\u2018hi\u2019") == "'hi'"

    def test_mixed_punctuation(self) -> None:
        result = normalize_chinese_punctuation("key：\u201cvalue，a、b\u201d")
        assert result == 'key:"value,a,b"'

    def test_no_chinese_punctuation(self) -> None:
        text = '{"key": "value", "num": 1}'
        assert normalize_chinese_punctuation(text) == text

    def test_empty_string(self) -> None:
        assert normalize_chinese_punctuation("") == ""


class TestParseLlmJson:
    """Tests for the 3-strategy LLM JSON parser."""

    def test_code_block_extraction(self) -> None:
        response = 'Here is the result:\n```json\n{"score": 85, "passed": true}\n```\nDone.'
        result = parse_llm_json(response)
        assert result == {"score": 85, "passed": True}

    def test_code_block_with_surrounding_text(self) -> None:
        response = 'Some text before\n```json\n{"key": "value"}\n```\nSome text after'
        result = parse_llm_json(response)
        assert result == {"key": "value"}

    def test_raw_json_in_text(self) -> None:
        response = 'The analysis shows {"scene": "medical", "total_score": 75} as the result.'
        result = parse_llm_json(response)
        assert result == {"scene": "medical", "total_score": 75}

    def test_entire_response_is_json(self) -> None:
        response = '{"scene": "general", "score": 50}'
        result = parse_llm_json(response)
        assert result == {"scene": "general", "score": 50}

    def test_nested_json(self) -> None:
        response = '{"outer": {"inner": "value"}, "list": [1, 2]}'
        result = parse_llm_json(response)
        assert result == {"outer": {"inner": "value"}, "list": [1, 2]}

    def test_nested_json_in_code_block(self) -> None:
        response = '```json\n{"scores": {"accuracy": 90}, "passed": true}\n```'
        result = parse_llm_json(response)
        assert result == {"scores": {"accuracy": 90}, "passed": True}

    def test_chinese_punctuation_in_code_block(self) -> None:
        response = '```json\n{"analysis"："病情分析"，"score"：80}\n```'
        result = parse_llm_json(response)
        assert result == {"analysis": "病情分析", "score": 80}

    def test_chinese_punctuation_in_raw_json(self) -> None:
        response = '结果如下：{"analysis"："分析"，"items"：["a"、"b"]}'
        result = parse_llm_json(response)
        assert result == {"analysis": "分析", "items": ["a", "b"]}

    def test_chinese_punctuation_in_entire_response(self) -> None:
        response = '{"key"："value"，"num"：1}'
        result = parse_llm_json(response)
        assert result == {"key": "value", "num": 1}

    def test_invalid_json_returns_none(self) -> None:
        response = "This is not JSON at all, just plain text."
        result = parse_llm_json(response)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_llm_json("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_llm_json("   \n\t  ") is None

    def test_code_block_takes_priority_over_raw(self) -> None:
        """When both code block and raw JSON exist, code block wins."""
        response = '{"bad": 1}\n```json\n{"good": 2}\n```\n{"also_bad": 3}'
        result = parse_llm_json(response)
        assert result == {"good": 2}

    def test_non_dict_json_returns_none(self) -> None:
        """Array responses are not dict and should return None."""
        response = '[1, 2, 3]'
        result = parse_llm_json(response)
        assert result is None

    def test_code_block_non_dict_returns_none(self) -> None:
        response = '```json\n[1, 2, 3]\n```'
        result = parse_llm_json(response)
        assert result is None

    def test_multiple_code_blocks_extracts_first(self) -> None:
        response = '```json\n{"first": true}\n```\n```json\n{"second": true}\n```'
        result = parse_llm_json(response)
        assert result == {"first": True}

    def test_non_greedy_before_greedy(self) -> None:
        """When text has multiple JSON objects, non-greedy extracts the first."""
        response = 'Result: {"a": 1} and {"b": 2}'
        result = parse_llm_json(response)
        assert result == {"a": 1}


class TestParseLlmJsonList:
    """Tests for list parsing in LLM JSON responses."""

    def test_uppercase_code_block_with_trailing_text(self) -> None:
        response = (
            "```JSON\n"
            '[{"name": "白细胞计数", "matched_index_id": 1}]\n'
            "```\n"
            "说明[完成]"
        )
        result = parse_llm_json_list(response)
        assert result == [{"name": "白细胞计数", "matched_index_id": 1}]

    def test_list_with_extra_text_after_array(self) -> None:
        response = (
            "解析结果如下：\n"
            '[{"name": "血红蛋白", "value": "116"}]\n'
            "以上结果可直接入库。"
        )
        result = parse_llm_json_list(response)
        assert result == [{"name": "血红蛋白", "value": "116"}]

    def test_repairs_prefixed_numeric_token(self) -> None:
        response = (
            "```json\n"
            '[{"name": "中性粒细胞数", "match_confidence": perm_0.9}]\n'
            "```"
        )
        result = parse_llm_json_list(response)
        assert result == [{"name": "中性粒细胞数", "match_confidence": 0.9}]

    def test_repairs_cjk_prefixed_numeric_token(self) -> None:
        response = (
            "```json\n"
            '[{"name": "白细胞计数", "match_confidence": 祭0.95}]\n'
            "```"
        )
        result = parse_llm_json_list(response)
        assert result == [{"name": "白细胞计数", "match_confidence": 0.95}]
