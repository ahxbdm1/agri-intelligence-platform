from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RetrievedDoc:
    source: str
    title: str
    excerpt: str
    score: float


class AgriKnowledgeRAG:
    def __init__(self, knowledge_dir: str | Path) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self.docs: list[dict] = []
        self.vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", ngram_range=(1, 2))
        self.matrix = None
        self.reload()

    def reload(self) -> None:
        self.docs.clear()
        for path in sorted(self.knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = self._title(text, path.stem)
            self.docs.append({"source": f"knowledge_base/{path.name}", "title": title, "content": text})
        if self.docs:
            self.matrix = self.vectorizer.fit_transform([self._normalize(d["content"]) for d in self.docs])
        else:
            self.matrix = None

    def search(self, query: str, top_k: int = 3) -> list[RetrievedDoc]:
        if not self.docs or self.matrix is None:
            return []
        q = self.vectorizer.transform([self._normalize(query)])
        scores = cosine_similarity(q, self.matrix).flatten()
        indexes = scores.argsort()[::-1][:top_k]
        results = []
        for idx in indexes:
            doc = self.docs[int(idx)]
            results.append(
                RetrievedDoc(
                    source=doc["source"],
                    title=doc["title"],
                    excerpt=self._excerpt(doc["content"], query),
                    score=round(float(scores[idx]), 4),
                )
            )
        return results

    def answer(self, query: str, system_context: dict | None = None) -> dict:
        results = self.search(query)
        context = system_context or {}
        risk_text = ""
        if context.get("high_risk_farms"):
            farms = "、".join(context["high_risk_farms"][:5])
            risk_text = f"结合当前系统数据，高风险地块优先关注：{farms}。"
        if context.get("weather_hint"):
            risk_text += f" 近期气象提示：{context['weather_hint']}。"

        if not results:
            return {
                "answer": f"{risk_text}知识库暂未检索到直接条目，建议由农技专家复核后补充到本地知识库。",
                "citations": [],
            }
        bullets = []
        for doc in results:
            bullets.append(f"依据《{doc.title}》：{doc.excerpt}")
        answer = (
            f"{risk_text}建议按“风险识别、现场复核、分区处置、效果回访”闭环处理。"
            + " ".join(bullets)
            + " 同时在预警中心生成巡检任务，记录处理状态和防治效果，便于后续模型校准。"
        )
        return {
            "answer": answer,
            "citations": [{"source": d.source, "title": d.title, "score": d.score} for d in results],
        }

    def _title(self, text: str, fallback: str) -> str:
        for line in text.splitlines():
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return fallback

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.lower())

    def _excerpt(self, content: str, query: str, length: int = 150) -> str:
        cleaned = re.sub(r"\s+", " ", content.replace("#", ""))
        terms = [t for t in re.split(r"\W+", query) if t]
        index = 0
        for term in terms:
            found = cleaned.find(term)
            if found >= 0:
                index = max(0, found - 30)
                break
        return cleaned[index : index + length].strip()
