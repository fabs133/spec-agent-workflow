"""Tests for core.llm_client (stdlib OpenAI API wrapper)."""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from core.errors import AgentError
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

    # --- Error handling tests ---

    @patch("core.llm_client.urllib.request.urlopen")
    def test_http_401_raises_agent_error(self, mock_urlopen):
        error_body = json.dumps({"error": {"message": "Invalid API key"}}).encode()
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401, msg="Unauthorized", hdrs={},
            fp=io.BytesIO(error_body),
        )
        with pytest.raises(AgentError, match="Authentication failed"):
            chat_completion("bad-key", "gpt-4o", [{"role": "user", "content": "hi"}])

    @patch("core.llm_client.urllib.request.urlopen")
    def test_http_429_raises_agent_error(self, mock_urlopen):
        error_body = json.dumps({"error": {"message": "Rate limit exceeded"}}).encode()
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=429, msg="Too Many Requests", hdrs={},
            fp=io.BytesIO(error_body),
        )
        with pytest.raises(AgentError, match="Rate limit exceeded"):
            chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])

    @patch("core.llm_client.urllib.request.urlopen")
    def test_http_500_raises_agent_error(self, mock_urlopen):
        error_body = json.dumps({"error": {"message": "Internal server error"}}).encode()
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=500, msg="Internal Server Error", hdrs={},
            fp=io.BytesIO(error_body),
        )
        with pytest.raises(AgentError, match="server error"):
            chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])

    @patch("core.llm_client.urllib.request.urlopen")
    def test_network_error_raises_agent_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with pytest.raises(AgentError, match="Network error"):
            chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])

    @patch("core.llm_client.urllib.request.urlopen")
    def test_timeout_raises_agent_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()
        with pytest.raises(AgentError, match="timed out"):
            chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])

    @patch("core.llm_client.urllib.request.urlopen")
    def test_malformed_json_raises_agent_error(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json at all"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with pytest.raises(AgentError, match="Invalid JSON"):
            chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])

    @patch("core.llm_client.urllib.request.urlopen")
    def test_missing_choices_raises_agent_error(self, mock_urlopen):
        body = json.dumps({"error": "something went wrong"}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with pytest.raises(AgentError, match="Unexpected response structure"):
            chat_completion("sk-test", "gpt-4o", [{"role": "user", "content": "hi"}])

    # --- Custom base_url tests ---

    @patch("core.llm_client.urllib.request.urlopen")
    def test_custom_base_url_used_in_request(self, mock_urlopen):
        mock_urlopen.return_value = self._mock_response("local output", 50)
        content, tokens = chat_completion(
            api_key="",
            model="qwen2.5:7b",
            messages=[{"role": "user", "content": "hi"}],
            base_url="http://localhost:11434",
        )
        assert content == "local output"
        assert tokens == 50

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://localhost:11434/v1/chat/completions"
        assert req.get_header("Authorization") is None
        assert req.get_header("Content-type") == "application/json"

        # SSL context should be None for HTTP
        ctx = mock_urlopen.call_args[1].get("context") if mock_urlopen.call_args[1] else mock_urlopen.call_args[0][1] if len(mock_urlopen.call_args[0]) > 1 else None
        assert ctx is None

    def test_custom_base_url_unreachable(self):
        with pytest.raises(AgentError, match="Network error"):
            chat_completion(
                api_key="",
                model="test",
                messages=[{"role": "user", "content": "test"}],
                base_url="http://localhost:99999",
            )
