"""Tests for core.llm_client (stdlib OpenAI API wrapper)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from core.llm_client import chat_completion


class TestChatCompletion:
    def _mock_response(self, content="Hello", tokens=42):
        body = json.dumps({
            "choices": [{"message": {"content": content}}],
            "usage": {"total_tokens": tokens},
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("core.llm_client.urllib.request.urlopen")
    def test_returns_content_and_tokens(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response("test output", 100)
        content, tokens = chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])
        assert content == "test output"
        assert tokens == 100

    @patch("core.llm_client.urllib.request.urlopen")
    def test_sends_correct_request(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response()
        chat_completion("sk-key", "gpt-4o-mini", [{"role": "system", "content": "sys"}], temperature=0.5)

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://api.openai.com/v1/chat/completions"
        assert req.get_header("Authorization") == "Bearer sk-key"
        assert req.get_header("Content-type") == "application/json"

        body = json.loads(req.data)
        assert body["model"] == "gpt-4o-mini"
        assert body["temperature"] == 0.5
        assert body["messages"][0]["role"] == "system"

    @patch("core.llm_client.urllib.request.urlopen")
    def test_empty_content_returns_empty_string(self, mock_urlopen):
        body = json.dumps({
            "choices": [{"message": {"content": None}}],
            "usage": {"total_tokens": 0},
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        content, tokens = chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])
        assert content == ""
        assert tokens == 0
