from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import re
from threading import Lock
import time
from typing import Any

import httpx

from app.core.config import Settings
from rag.retriever import AgriKnowledgeRAG


@dataclass
class RAGFlowCitation:
    source: str
    title: str
    score: float


class RAGFlowClient:
    """RAGFlow chat client with an explicit local retrieval fallback."""

    def __init__(self, settings: Settings, local_rag: AgriKnowledgeRAG) -> None:
        self.settings = settings
        self.local_rag = local_rag
        self._cache_lock = Lock()
        self._status_cache: tuple[float, dict[str, Any]] | None = None
        self._answer_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._remote_disabled_until = 0.0

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.ragflow_enabled
            and self.settings.ragflow_base_url
            and self.settings.ragflow_api_key
            and self.settings.ragflow_chat_id
        )

    def status(self) -> dict[str, Any]:
        with self._cache_lock:
            if self._status_cache and time.monotonic() - self._status_cache[0] < 30:
                return deepcopy(self._status_cache[1])
        base = {
            "configured": self.configured,
            "available": False,
            "mode": "local",
            "provider": "本地 TF-IDF",
            "dataset_count": len(self.settings.ragflow_dataset_id_list),
            "chat_configured": bool(self.settings.ragflow_chat_id),
        }
        if not self.configured:
            result = {**base, "message": "RAGFlow 未配置，当前使用本地知识库"}
            self._remember_status(result)
            return result

        try:
            with self._client(timeout=self.settings.ragflow_status_timeout_seconds) as client:
                datasets_response = client.get("/api/v1/datasets", params={"page": 1, "page_size": 100})
                datasets_response.raise_for_status()
                datasets_payload = datasets_response.json()
                chats_response = client.get("/api/v1/chats", params={"page": 1, "page_size": 100})
                chats_response.raise_for_status()
                chats_payload = chats_response.json()

            if datasets_payload.get("code") != 0 or chats_payload.get("code") != 0:
                raise RuntimeError("RAGFlow 配置查询失败")

            dataset_ids = {item.get("id") for item in (datasets_payload.get("data") or [])}
            chats = (chats_payload.get("data") or {}).get("chats", [])
            chat_ids = {item.get("id") for item in chats}
            expected_datasets = set(self.settings.ragflow_dataset_id_list)
            dataset_ready = not expected_datasets or expected_datasets.issubset(dataset_ids)
            chat_ready = self.settings.ragflow_chat_id in chat_ids
            available = dataset_ready and chat_ready
            result = {
                **base,
                "available": available,
                "mode": "ragflow" if available else "local",
                "provider": "RAGFlow 远程知识库" if available else "本地 TF-IDF",
                "message": "RAGFlow 知识库与聊天助手已连接" if available else "RAGFlow 配置对象不存在，已启用本地降级",
            }
            self._remember_status(result)
            return result
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            result = {**base, "message": f"RAGFlow 暂不可用：{self._safe_error(exc)}"}
            self._remember_status(result)
            return result

    def answer(self, question: str, system_context: dict[str, Any] | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        if self.configured:
            if time.monotonic() < self._remote_disabled_until:
                return self._local_answer(
                    question,
                    system_context,
                    started,
                    "RAGFlow 最近一次请求超时，当前优先使用本地知识库；系统会自动重试远程服务。",
                )
            cache_key = self._normalize_question(question)
            with self._cache_lock:
                cached = self._answer_cache.get(cache_key)
                if cached and time.monotonic() - cached[0] < 300:
                    result = deepcopy(cached[1])
                    result["answer"] = self._append_system_context(result["answer"], system_context)
                    result["cached"] = True
                    result["latency_ms"] = round((time.perf_counter() - started) * 1000)
                    return result
            try:
                result = self._remote_answer(question)
                with self._cache_lock:
                    self._answer_cache[cache_key] = (time.monotonic(), deepcopy(result))
                result["answer"] = self._append_system_context(result["answer"], system_context)
                result["latency_ms"] = round((time.perf_counter() - started) * 1000)
                return result
            except (httpx.HTTPError, ValueError, KeyError, RuntimeError) as exc:
                self._remote_disabled_until = time.monotonic() + 60
                warning = f"RAGFlow 请求失败，已自动切换本地知识库：{self._safe_error(exc)}"
                return self._local_answer(question, system_context, started, warning)
        return self._local_answer(question, system_context, started, "RAGFlow 未配置，当前使用本地知识库")

    def _remote_answer(self, question: str) -> dict[str, Any]:
        with self._client() as client:
            response = client.post(
                f"/api/v1/chats/{self.settings.ragflow_chat_id}/completions",
                json={"question": question, "stream": False},
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("code") != 0:
            raise RuntimeError(payload.get("message") or "RAGFlow 返回业务错误")
        data = payload.get("data") or {}
        answer = self._clean_answer(str(data.get("answer") or ""))
        if not answer:
            raise RuntimeError("RAGFlow 未返回回答内容")

        reference = data.get("reference") or {}
        chunks = reference.get("chunks") or []
        citations: list[RAGFlowCitation] = []
        seen: set[str] = set()
        for chunk in chunks:
            document_name = str(chunk.get("document_name") or chunk.get("docnm_kwd") or "RAGFlow 知识文档")
            source = f"RAGFlow/{document_name}"
            if source in seen:
                continue
            seen.add(source)
            similarity = float(chunk.get("similarity") or chunk.get("score") or 0)
            citations.append(
                RAGFlowCitation(
                    source=source,
                    title=document_name.rsplit(".", 1)[0],
                    score=round(max(0.0, min(similarity, 1.0)), 4),
                )
            )

        return {
            "answer": answer,
            "citations": [citation.__dict__ for citation in citations],
            "mode": "ragflow",
            "provider": "RAGFlow 远程知识库",
            "warning": None,
        }

    def _local_answer(
        self,
        question: str,
        system_context: dict[str, Any] | None,
        started: float,
        warning: str,
    ) -> dict[str, Any]:
        result = self.local_rag.answer(question, system_context)
        return {
            **result,
            "mode": "local",
            "provider": "本地 TF-IDF",
            "warning": warning,
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }

    def _client(self, timeout: float | None = None) -> httpx.Client:
        total_timeout = timeout or self.settings.ragflow_timeout_seconds
        return httpx.Client(
            base_url=self.settings.ragflow_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.settings.ragflow_api_key}"},
            timeout=httpx.Timeout(total_timeout, connect=min(3.0, total_timeout)),
            verify=self.settings.ragflow_verify_ssl,
        )

    def _append_system_context(self, answer: str, context: dict[str, Any] | None) -> str:
        context = context or {}
        notes = []
        if context.get("high_risk_farms"):
            notes.append(f"当前高风险地块：{'、'.join(context['high_risk_farms'][:5])}")
        if context.get("weather_hint"):
            notes.append(f"近期气象：{context['weather_hint']}")
        if not notes:
            return answer
        return f"{answer}\n\n系统实时研判：{'；'.join(notes)}。"

    def _clean_answer(self, answer: str) -> str:
        answer = re.sub(r"##\d+\$\$", "", answer)
        answer = re.sub(r"\[ID:\d+\]", "", answer)
        answer = re.sub(r"(?m)^#{1,6}\s*", "", answer)
        answer = answer.replace("**", "")
        return re.sub(r"\n{3,}", "\n\n", answer).strip()

    def _safe_error(self, error: Exception) -> str:
        message = str(error).replace(self.settings.ragflow_api_key, "***")
        return message[:160] or error.__class__.__name__

    def _remember_status(self, result: dict[str, Any]) -> None:
        with self._cache_lock:
            self._status_cache = (time.monotonic(), deepcopy(result))

    def _normalize_question(self, question: str) -> str:
        return re.sub(r"\s+", " ", question.strip()).lower()
