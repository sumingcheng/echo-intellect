"""chat endpoint 集成测试：mock 掉 RetrievalChain，验证 HTTP 层行为。"""
import pytest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.app import create_app
from app.core.container import AppContainer


def _make_app(chain_result: dict):
    """构造一个注入 mock RetrievalChain 的 FastAPI 实例。"""
    mock_chain = MagicMock()
    mock_chain.run.return_value = chain_result
    mock_chain.initialized = True
    container = AppContainer(retrieval_chain=mock_chain)
    app = create_app(container=container)
    return app, mock_chain


class TestChatEndpoint:

    def test_text_chat_success(self):
        app, mock_chain = _make_app({
            "answer": "我是 Echo Intellect",
            "query_id": "q-001",
            "session_id": "s-001",
            "processing_time": 0.5,
            "tokens_used": 42,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "metadata": {},
        })
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/chat", json={"message": "你好"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["answer"] == "我是 Echo Intellect"
            assert data["speech"] is None

    def test_voice_mode_returns_speech_info(self):
        app, _ = _make_app({
            "answer": "你好呀",
            "query_id": "q-002",
            "session_id": "s-002",
            "processing_time": 0.3,
            "tokens_used": 10,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "metadata": {},
        })
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/chat", json={
                "message": "你好",
                "response_mode": "voice",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["speech"] is not None
            assert data["speech"]["text"] == "你好呀"
            assert "/speech/audio" in data["speech"]["endpoint"]

    def test_chain_error_returns_500(self):
        app, _ = _make_app({
            "answer": "LLM 挂了",
            "error": True,
            "query_id": "q-003",
            "session_id": "s-003",
            "processing_time": 0.0,
            "tokens_used": 0,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "metadata": {},
        })
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/chat", json={"message": "test"})
            assert resp.status_code == 500

    def test_empty_message_rejected(self):
        app, _ = _make_app({"answer": "不该到这里"})
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/chat", json={"message": ""})
            assert resp.status_code == 422

    def test_session_id_passthrough(self):
        app, mock_chain = _make_app({
            "answer": "ok",
            "query_id": "q-004",
            "session_id": "custom-session",
            "processing_time": 0.1,
            "tokens_used": 5,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "metadata": {},
        })
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/chat", json={
                "message": "hello",
                "session_id": "custom-session",
            })
            assert resp.status_code == 200
            mock_chain.run.assert_called_once()
            call_kwargs = mock_chain.run.call_args
            assert call_kwargs.kwargs.get("session_id") == "custom-session" or \
                   (call_kwargs[1].get("session_id") == "custom-session" if len(call_kwargs) > 1 else True)

    def test_model_passthrough(self):
        app, mock_chain = _make_app({
            "answer": "ok",
            "query_id": "q-005",
            "session_id": "s-005",
            "processing_time": 0.1,
            "tokens_used": 5,
            "relevance_score": 0.0,
            "retrieved_chunks_count": 0,
            "metadata": {},
        })
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/chat", json={
                "message": "hello",
                "model": "gpt-5.4-pro",
            })
            assert resp.status_code == 200
            kwargs = mock_chain.run.call_args.kwargs
            assert kwargs["model"] == "gpt-5.4-pro"
