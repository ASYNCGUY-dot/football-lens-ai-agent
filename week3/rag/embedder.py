# -*- coding: utf-8 -*-
"""
embedder.py
===========
ChromaDB 벡터 DB에 축구 뉴스 기사를 임베딩하고 저장합니다.

동작 방식:
    1. week1 PostgreSQL articles 테이블에서 기사를 가져옴
    2. sentence-transformers 모델로 텍스트 임베딩
    3. ChromaDB 컬렉션에 저장 (metadata.source = "real")

사용법:
    from week3.rag.embedder import ArticleEmbedder

    embedder = ArticleEmbedder()
    embedder.build_index()          # DB 기사 임베딩
    results = embedder.search("손흥민 골", n_results=5)
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── ChromaDB / sentence-transformers 임포트 ─────────────────
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("chromadb 미설치. pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers 미설치. pip install sentence-transformers")

# ── week1 DB 임포트 ──────────────────────────────────────────
WEEK1_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "week1")
if WEEK1_PATH not in sys.path:
    sys.path.insert(0, WEEK1_PATH)




# =============================================
# ArticleEmbedder 클래스
# =============================================

class ArticleEmbedder:
    """
    ChromaDB 기반 축구 뉴스 기사 임베더

    주요 메서드:
        build_index()      : DB 기사 + 더미 데이터 임베딩 → ChromaDB 저장
        search(query)      : 자연어 쿼리로 유사 기사 검색
        get_stats()        : 컬렉션 통계 반환
        clear_collection() : 컬렉션 초기화

    환경변수:
        CHROMA_PERSIST_DIR : ChromaDB 저장 경로 (기본: ./chroma_db)
        EMBEDDING_MODEL    : sentence-transformers 모델명
    """

    COLLECTION_NAME = "football_news"

    def __init__(
        self,
        persist_dir: str = None,
        model_name: str = None,
    ):
        """
        ChromaDB 클라이언트와 임베딩 모델을 초기화합니다.

        Parameters
        ----------
        persist_dir : str, optional
            ChromaDB 저장 경로. 미입력 시 환경변수 CHROMA_PERSIST_DIR 사용.
        model_name : str, optional
            sentence-transformers 모델명. 미입력 시 EMBEDDING_MODEL 환경변수 사용.
        """
        self.persist_dir = persist_dir or os.getenv(
            "CHROMA_PERSIST_DIR", "./chroma_db"
        )
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._client = None
        self._collection = None
        self._model = None

    def _get_client(self):
        """ChromaDB 클라이언트를 반환합니다. 최초 호출 시 초기화됩니다."""
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb 패키지가 필요합니다: pip install chromadb")
        if self._client is None:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            logger.info(f"ChromaDB 클라이언트 초기화: {self.persist_dir}")
        return self._client

    def _get_collection(self):
        """ChromaDB 컬렉션을 반환합니다. 없으면 생성합니다."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},  # 코사인 유사도 사용
            )
            logger.info(
                f"컬렉션 '{self.COLLECTION_NAME}' 로드: {self._collection.count()}건"
            )
        return self._collection

    def _get_model(self):
        """sentence-transformers 임베딩 모델을 반환합니다."""
        if not ST_AVAILABLE:
            raise ImportError(
                "sentence-transformers 패키지가 필요합니다: "
                "pip install sentence-transformers"
            )
        if self._model is None:
            logger.info(f"임베딩 모델 로딩: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("임베딩 모델 로딩 완료")
        return self._model

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        텍스트 목록을 벡터로 변환합니다.

        Parameters
        ----------
        texts : list[str]
            임베딩할 텍스트 목록

        Returns
        -------
        list[list[float]]
            각 텍스트의 임베딩 벡터
        """
        try:
            model = self._get_model()
            embeddings = model.encode(texts, show_progress_bar=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"[_embed_texts] 임베딩 오류: {e}")
            raise

    def _articles_to_documents(self, articles: list[dict], source_tag: str) -> tuple:
        """
        기사 딕셔너리를 ChromaDB 입력 형식으로 변환합니다.

        Parameters
        ----------
        articles : list[dict]
            기사 딕셔너리 목록
        source_tag : str
            "real" 또는 "dummy"

        Returns
        -------
        tuple
            (ids, documents, metadatas) — ChromaDB add()에 전달할 형식
        """
        ids, documents, metadatas = [], [], []
        for a in articles:
            try:
                article_id = str(a.get("article_id", ""))
                title = a.get("title", "")
                summary = a.get("summary", "") or ""
                # 임베딩 텍스트: 제목 + 요약 결합
                text = f"{title} {summary}".strip()
                if not text or not article_id:
                    continue
                ids.append(article_id)
                documents.append(text)
                metadatas.append({
                    "source": source_tag,
                    "title": title[:200],           # ChromaDB 메타데이터 길이 제한
                    "url": str(a.get("url", ""))[:500],
                    "language": a.get("language", "unknown"),
                    "source_name": str(a.get("source_name", ""))[:100],
                    "category": str(a.get("category", ""))[:50],
                    "published_at": str(a.get("published_at", ""))[:30],
                })
            except Exception as e:
                logger.warning(f"[_articles_to_documents] 기사 변환 오류 (건너뜀): {e}")
                continue
        return ids, documents, metadatas

    def _fetch_db_articles(self, limit: int = 500) -> list[dict]:
        """
        week1 PostgreSQL DB에서 기사를 가져옵니다.

        Returns
        -------
        list[dict]
            기사 딕셔너리 목록. DB 연결 실패 시 빈 리스트.
        """
        try:
            from database.schema import get_db_connection
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT article_id, title, summary, url, language,
                           source_name, category,
                           published_at::text
                    FROM articles
                    ORDER BY published_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
            conn.close()
            articles = [
                {
                    "article_id": r[0], "title": r[1], "summary": r[2],
                    "url": r[3], "language": r[4], "source_name": r[5],
                    "category": r[6], "published_at": r[7],
                }
                for r in rows
            ]
            logger.info(f"DB에서 기사 {len(articles)}건 로드")
            return articles
        except Exception as e:
            logger.warning(f"[_fetch_db_articles] DB 조회 실패 (더미 데이터로 대체): {e}")
            return []

    def _upsert_batch(self, ids, documents, metadatas, embeddings):
        """
        ChromaDB에 배치 upsert합니다. 이미 존재하는 ID는 업데이트됩니다.

        Parameters
        ----------
        ids : list[str]
        documents : list[str]
        metadatas : list[dict]
        embeddings : list[list[float]]
        """
        try:
            collection = self._get_collection()
            # 배치 크기 100으로 분할 (대용량 처리 시 안정성)
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                batch_docs = documents[i:i+batch_size]
                batch_meta = metadatas[i:i+batch_size]
                batch_emb = embeddings[i:i+batch_size]
                collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_meta,
                    embeddings=batch_emb,
                )
            logger.info(f"ChromaDB upsert 완료: {len(ids)}건")
        except Exception as e:
            logger.error(f"[_upsert_batch] ChromaDB upsert 오류: {e}")
            raise

    def build_index(self) -> dict:
        """
        ChromaDB 인덱스를 빌드합니다.

        실행 순서:
            1. week1 DB에서 실제 기사 가져오기 (실패 시 빈 리스트)
            2. 임베딩 생성
            3. ChromaDB에 upsert

        Returns
        -------
        dict
            {"real_count": N, "total": N}
        """
        logger.info("[build_index] ChromaDB 인덱스 빌드 시작")
        stats = {"real_count": 0, "total": 0}

        # ── 실제 기사 처리 ─────────────────────────────────────
        db_articles = self._fetch_db_articles()
        if db_articles:
            ids_r, docs_r, meta_r = self._articles_to_documents(db_articles, "real")
            if ids_r:
                logger.info(f"실제 기사 {len(ids_r)}건 임베딩 중...")
                embs_r = self._embed_texts(docs_r)
                self._upsert_batch(ids_r, docs_r, meta_r, embs_r)
                stats["real_count"] = len(ids_r)
        else:
            logger.info("DB 기사 없음")

        stats["total"] = stats["real_count"]
        logger.info(f"[build_index] 완료 | 실제:{stats['real_count']}건")
        return stats

    def index_articles(self, articles: list[dict]) -> dict:
        """
        DB를 거치지 않고, 이번 파이프라인 실행에서 수집한 기사를 바로
        인덱싱한다.

        build_index()는 week1 PostgreSQL에서 기사를 읽어오도록 설계돼
        있는데, 실제 파이프라인은 그 DB에 기사를 저장하는 단계가 없어서
        (_fetch_db_articles가 항상 실패 → 더미 데이터로 대체) RAG 검색이
        영구히 초기 데모 10건만 대상으로 동작하는 문제가 있었다. 이 메서드는
        rag_search_node가 이미 들고 있는 state의 실제 기사를 바로 넘겨받아
        인덱싱함으로써 DB 단계를 우회한다.

        upsert이므로 매 실행마다 호출해도 같은 기사는 덮어쓸 뿐 중복되지
        않는다.

        Parameters
        ----------
        articles : list[dict]
            이번 실행에서 수집된 기사 (article_id 필수)

        Returns
        -------
        dict
            {"indexed": N}
        """
        if not articles:
            return {"indexed": 0}
        ids, docs, metas = self._articles_to_documents(articles, "real")
        if not ids:
            return {"indexed": 0}
        embs = self._embed_texts(docs)
        self._upsert_batch(ids, docs, metas, embs)
        logger.info(f"[index_articles] 이번 실행 기사 {len(ids)}건 인덱싱 완료")
        return {"indexed": len(ids)}

    def search(
        self,
        query: str,
        n_results: int = 5,
        language_filter: str = None,
        source_filter: str = None,
    ) -> list[dict]:
        """
        자연어 쿼리로 유사 기사를 검색합니다.

        Parameters
        ----------
        query : str
            검색 쿼리 (예: "손흥민 골", "EPL 우승 경쟁")
        n_results : int
            반환할 결과 수 (기본 5)
        language_filter : str, optional
            언어 필터 ("ko" / "en"). None이면 전체.
        source_filter : str, optional
            데이터 출처 필터 ("real" / "dummy"). None이면 전체.

        Returns
        -------
        list[dict]
            검색 결과 목록. 각 항목:
            - id, title, summary, url, language, source, distance
        """
        try:
            model = self._get_model()
            query_embedding = model.encode([query]).tolist()

            # 필터 조건 구성
            where = {}
            if language_filter:
                where["language"] = language_filter
            if source_filter:
                where["source"] = source_filter

            collection = self._get_collection()
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=min(n_results, collection.count() or 1),
                where=where if where else None,
                include=["documents", "metadatas", "distances"],
            )

            items = []
            if results and results.get("ids"):
                for i, doc_id in enumerate(results["ids"][0]):
                    meta = results["metadatas"][0][i]
                    items.append({
                        "id": doc_id,
                        "title": meta.get("title", ""),
                        "summary": results["documents"][0][i],
                        "url": meta.get("url", ""),
                        "language": meta.get("language", ""),
                        "source": meta.get("source", ""),
                        "source_name": meta.get("source_name", ""),
                        "category": meta.get("category", ""),
                        "distance": round(results["distances"][0][i], 4),
                    })
            return items

        except Exception as e:
            logger.error(f"[search] 검색 오류: {e}")
            return []

    def get_stats(self) -> dict:
        """
        ChromaDB 컬렉션 통계를 반환합니다.

        Returns
        -------
        dict
            {"total": N, "real": N, "collection_name": str}
        """
        try:
            collection = self._get_collection()
            total = collection.count()
            return {
                "total": total,
                "real": total,
                "collection_name": self.COLLECTION_NAME,
                "persist_dir": self.persist_dir,
            }
        except Exception as e:
            logger.error(f"[get_stats] 오류: {e}")
            return {"total": 0, "real": 0}

    def clear_collection(self, confirm: bool = False):
        """
        ChromaDB 컬렉션을 초기화합니다.

        Parameters
        ----------
        confirm : bool
            True로 설정해야 실제로 삭제됩니다.
        """
        if not confirm:
            logger.warning("[clear_collection] confirm=True 필요. 취소됨.")
            return
        try:
            client = self._get_client()
            client.delete_collection(self.COLLECTION_NAME)
            self._collection = None
            logger.info(f"컬렉션 '{self.COLLECTION_NAME}' 삭제 완료")
        except Exception as e:
            logger.error(f"[clear_collection] 오류: {e}")


# =============================================
# 직접 실행 시 인덱스 빌드 테스트
# =============================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    embedder = ArticleEmbedder()

    print("=== ChromaDB 인덱스 빌드 ===\n")
    stats = embedder.build_index()
    print(f"빌드 결과: 실제={stats['real_count']}건\n")

    print("=== 검색 테스트 ===")
    queries = ["손흥민 골", "EPL 우승", "transfer news"]
    for q in queries:
        results = embedder.search(q, n_results=3)
        print(f"\n쿼리: '{q}'")
        for r in results:
            print(f"  [{r['source']}][{r['language']}] {r['title'][:50]}  (거리: {r['distance']})")
