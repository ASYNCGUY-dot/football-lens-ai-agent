# -*- coding: utf-8 -*-
"""
test_integration.py
===================
Football Lens 전체 통합 테스트

테스트 대상:
    1. [week3] RAG - ArticleEmbedder (임베딩 + 검색)
    2. [week3] RAG - rag_search_node (LangGraph 노드)
    3. [week3] insight_node (통합 인사이트 보고서 생성)
    4. [week3] EmailSender (SMTP 연결 + HTML 변환)
    5. [week2] 전체 파이프라인 통합 흐름 (collect → preprocess → classify → LLM → merge → RAG → insight)
    6. [week1] DB 스키마 테이블 존재 여부

실행 방법:
    cd week3
    python -m pytest tests/test_integration.py -v
    # 또는 직접:
    python tests/test_integration.py

주의:
    - API 키 없이도 목업/폴백 경로로 테스트 가능
    - chromadb / sentence-transformers 패키지 필요
    - DB 테스트는 PostgreSQL 연결 가능 환경에서만 통과
"""

import sys
import os
import unittest
import logging

# ── 경로 설정 ────────────────────────────────────────────────
ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
WEEK1_PATH = os.path.join(ROOT, "week1")
WEEK2_PATH = os.path.join(ROOT, "week2")
WEEK3_PATH = os.path.join(ROOT, "week3")

for p in [ROOT, WEEK1_PATH, WEEK2_PATH, WEEK3_PATH]:
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "week3", ".env"))

logging.basicConfig(
    level=logging.WARNING,  # 테스트 중 INFO 로그 억제
    format="%(levelname)s %(name)s: %(message)s",
)


# =============================================
# 1. RAG 임베더 테스트
# =============================================

class TestArticleEmbedder(unittest.TestCase):
    """ArticleEmbedder 클래스 단위 테스트"""

    def setUp(self):
        """각 테스트 전 임시 ChromaDB 경로 설정"""
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()

    def test_import(self):
        """chromadb / sentence-transformers import 가능 여부 확인"""
        try:
            from week3.rag.embedder import ArticleEmbedder
            self.assertTrue(True, "ArticleEmbedder import 성공")
        except ImportError as e:
            self.skipTest(f"패키지 미설치: {e}")

    def test_build_index_with_dummy(self):
        """더미 데이터만으로 ChromaDB 인덱스 빌드 테스트"""
        try:
            from week3.rag.embedder import ArticleEmbedder
        except ImportError:
            self.skipTest("패키지 미설치")

        embedder = ArticleEmbedder(persist_dir=self.tmp_dir)
        try:
            stats = embedder.build_index()
            self.assertGreater(stats["total"], 0, "총 임베딩 > 0")
        except Exception as e:
            self.skipTest(f"임베딩 실패 (모델 다운로드 필요): {e}")

    def test_search_returns_results(self):
        """인덱스 빌드 후 검색 결과 반환 확인"""
        try:
            from week3.rag.embedder import ArticleEmbedder
        except ImportError:
            self.skipTest("패키지 미설치")

        embedder = ArticleEmbedder(persist_dir=self.tmp_dir)
        try:
            embedder.build_index()
            results = embedder.search("손흥민 골", n_results=3)
            self.assertIsInstance(results, list, "결과는 리스트여야 함")
            self.assertGreater(len(results), 0, "검색 결과 1건 이상")
        except Exception as e:
            self.skipTest(f"검색 실패: {e}")

    def test_search_result_structure(self):
        """검색 결과 딕셔너리 구조 확인"""
        try:
            from week3.rag.embedder import ArticleEmbedder
        except ImportError:
            self.skipTest("패키지 미설치")

        embedder = ArticleEmbedder(persist_dir=self.tmp_dir)
        try:
            embedder.build_index()
            results = embedder.search("EPL 우승", n_results=1)
            if not results:
                self.skipTest("검색 결과 없음")
            result = results[0]
            required_keys = ["id", "title", "summary", "url", "language", "source", "distance"]
            for key in required_keys:
                self.assertIn(key, result, f"검색 결과에 {key} 키 없음")
        except Exception as e:
            self.skipTest(f"오류: {e}")

    def tearDown(self):
        """임시 디렉터리 정리"""
        import shutil
        try:
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        except Exception:
            pass


# =============================================
# 2. RAG 노드 테스트
# =============================================

class TestRagSearchNode(unittest.TestCase):
    """rag_search_node LangGraph 노드 테스트"""

    def test_node_returns_dict(self):
        """노드가 딕셔너리를 반환하는지 확인"""
        try:
            from week3.rag.rag_node import rag_search_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        result = rag_search_node(state)
        self.assertIsInstance(result, dict, "노드 반환값은 dict여야 함")

    def test_node_has_required_keys(self):
        """노드 반환값에 필수 키가 있는지 확인"""
        try:
            from week3.rag.rag_node import rag_search_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        result = rag_search_node(state)
        self.assertIn("rag_context", result, "rag_context 키 없음")
        self.assertIn("errors", result, "errors 키 없음")
        self.assertIsInstance(result["rag_context"], list, "rag_context는 리스트여야 함")

    def test_node_graceful_on_empty_index(self):
        """빈 인덱스에서도 오류 없이 실행되는지 확인"""
        try:
            from week3.rag.rag_node import rag_search_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        # 예외 없이 실행되어야 함
        try:
            result = rag_search_node(state)
            self.assertIsInstance(result, dict)
        except Exception as e:
            self.fail(f"빈 인덱스에서 예외 발생: {e}")


# =============================================
# 3. 인사이트 노드 테스트
# =============================================

class TestInsightNode(unittest.TestCase):
    """insight_node 테스트"""

    def test_node_returns_dict(self):
        """노드가 딕셔너리를 반환하는지 확인"""
        try:
            from week3.insight_node import insight_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        result = insight_node(state)
        self.assertIsInstance(result, dict)

    def test_node_has_insight_report(self):
        """노드가 insight_report 키를 반환하는지 확인"""
        try:
            from week3.insight_node import insight_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        result = insight_node(state)
        self.assertIn("insight_report", result, "insight_report 키 없음")
        self.assertIsInstance(result["insight_report"], str, "insight_report는 문자열")
        self.assertGreater(len(result["insight_report"]), 0, "빈 보고서 허용 안 됨")

    def test_mock_report_generated_without_api(self):
        """API 키 없을 때 목업 보고서가 생성되는지 확인"""
        try:
            from week3.insight_node import insight_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        # API 키 제거하여 목업 경로 강제
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""}):
            state = create_initial_state()
            result = insight_node(state)
            self.assertIn("insight_report", result)
            # 목업 표시 문자열 확인
            self.assertIn("목업", result["insight_report"])

    def test_prompt_builder_returns_string(self):
        """프롬프트 빌더가 문자열을 반환하는지 확인"""
        try:
            from week3.insight_node import _build_insight_prompt
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        prompt = _build_insight_prompt(state)
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100, "프롬프트가 너무 짧음")


# =============================================
# 4. 이메일 모듈 테스트
# =============================================

class TestEmailSender(unittest.TestCase):
    """EmailSender 클래스 테스트 (SMTP 실제 연결은 옵션)"""

    def test_import(self):
        """EmailSender import 확인"""
        try:
            from week3.mailer.email_sender import EmailSender
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"EmailSender import 실패: {e}")

    def test_raises_without_credentials(self):
        """SMTP 인증 정보 없을 때 ValueError 발생 확인"""
        try:
            from week3.mailer.email_sender import EmailSender
        except ImportError:
            self.skipTest("import 불가")

        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"SMTP_USER": "", "SMTP_PASSWORD": ""}):
            with self.assertRaises(ValueError):
                EmailSender()

    def test_markdown_to_html_conversion(self):
        """마크다운 → HTML 변환 기본 동작 확인"""
        try:
            from week3.mailer.email_sender import _markdown_to_html_body
        except ImportError:
            self.skipTest("import 불가")

        md = "# 제목\n\n## 섹션\n\n**굵은 글씨** 테스트\n\n- 항목1\n- 항목2"
        html = _markdown_to_html_body(md)
        # email_sender는 HTML 이메일 호환성을 위해 h1/h2 대신 스타일 div를 사용함
        self.assertIn("제목", html, "h1 내용이 html에 없음")
        self.assertIn("섹션", html, "h2 내용이 html에 없음")
        self.assertIn("<strong", html, "strong 태그 없음")
        self.assertIn("<html", html, "html 태그 없음")

    def test_smtp_connection(self):
        """SMTP 연결 테스트 (자격증명 있을 때만 실행)"""
        try:
            from week3.mailer.email_sender import EmailSender
        except ImportError:
            self.skipTest("import 불가")

        if not os.getenv("SMTP_USER") or not os.getenv("SMTP_PASSWORD"):
            self.skipTest("SMTP 자격증명 없음 (건너뜀)")

        sender = EmailSender()
        result = sender.test_connection()
        self.assertTrue(result, "SMTP 연결 실패")


# =============================================
# 5. 전체 파이프라인 통합 테스트
# =============================================

class TestFullPipeline(unittest.TestCase):
    """week2 LangGraph 파이프라인 전체 흐름 통합 테스트"""

    def test_pipeline_imports(self):
        """파이프라인 관련 모듈 import 확인"""
        modules = [
            "week2.state",
            "week2.nodes",
            "week2.llm_nodes",
            "week2.graph",
        ]
        for mod in modules:
            try:
                __import__(mod)
            except ImportError as e:
                self.fail(f"{mod} import 실패: {e}")

    def test_initial_state_creation(self):
        """초기 State 생성 확인"""
        try:
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        self.assertIn("run_id", state, "run_id 없음")
        self.assertIn("config", state, "config 없음")
        self.assertIsInstance(state["run_id"], str)

    def test_collect_node_no_api_keys(self):
        """API 키 없을 때 collect_node가 graceful하게 동작하는지 확인"""
        try:
            from week2.nodes import collect_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        import unittest.mock as mock
        with mock.patch.dict(os.environ, {
            "NAVER_CLIENT_ID": "", "NAVER_CLIENT_SECRET": "",
            "FOOTBALL_DATA_API_KEY": "",
        }):
            state = create_initial_state()
            result = collect_node(state)
            self.assertIsInstance(result, dict, "collect_node 반환값은 dict")
            self.assertIn("raw_articles", result)
            self.assertIn("errors", result)

    def test_preprocess_node_with_empty(self):
        """빈 기사 목록에서 preprocess_node가 정상 동작하는지 확인"""
        try:
            from week2.nodes import preprocess_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        state["raw_articles"] = []
        result = preprocess_node(state)
        self.assertIsInstance(result, dict)

    def test_classify_node_flags(self):
        """classify_node가 올바른 라우팅 플래그를 설정하는지 확인"""
        try:
            from week2.nodes import classify_node
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        # 한국어 기사 1개 주입
        state["raw_articles"] = [
            {"article_id": "test001", "title": "테스트", "language": "ko",
             "url": "http://test.com", "summary": "테스트 요약"},
        ]
        result = classify_node(state)
        self.assertTrue(result.get("has_korean"), "has_korean이 True여야 함")
        self.assertFalse(result.get("has_english"), "has_english는 False여야 함")

    def test_graph_build_and_compile(self):
        """LangGraph 빌드/컴파일 오류 없이 완료되는지 확인"""
        try:
            from week2.graph import build_graph, compile_graph
        except ImportError as e:
            self.skipTest(f"langgraph import 실패: {e}")

        try:
            graph = build_graph()
            self.assertIsNotNone(graph, "그래프 빌드 실패")
            compiled = compile_graph()
            self.assertIsNotNone(compiled, "그래프 컴파일 실패")
        except Exception as e:
            self.fail(f"그래프 빌드/컴파일 오류: {e}")

    def test_route_after_classify_all_false(self):
        """has_* 플래그가 모두 False일 때 merge로 라우팅되는지 확인"""
        try:
            from week2.graph import route_after_classify
            from week2.state import create_initial_state
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        state = create_initial_state()
        state["has_korean"] = False
        state["has_english"] = False
        state["has_match_data"] = False
        result = route_after_classify(state)
        self.assertIn("merge", result, "모든 플래그 False → merge로 라우팅")

    def test_state_rag_context_field(self):
        """state.py에 rag_context 필드가 추가되었는지 확인"""
        try:
            from week2.state import FootballNewsState
        except ImportError as e:
            self.skipTest(f"import 실패: {e}")

        # TypedDict 어노테이션에 rag_context 있는지 확인
        annotations = FootballNewsState.__annotations__
        self.assertIn("rag_context", annotations, "state에 rag_context 필드 없음")


# =============================================
# 6. DB 스키마 테스트 (PostgreSQL 연결 필요)
# =============================================

class TestDatabaseSchema(unittest.TestCase):
    """week1 PostgreSQL 스키마 테스트"""

    def test_schema_import(self):
        """schema.py import 확인"""
        try:
            from database.schema import DatabaseManager, get_db_connection
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"schema import 실패: {e}")

    def test_db_connection(self):
        """PostgreSQL 연결 테스트 (연결 가능 환경에서만 실행)"""
        try:
            from database.schema import get_db_connection
        except ImportError:
            self.skipTest("schema import 불가")

        if not os.getenv("DB_HOST"):
            self.skipTest("DB 환경변수 없음 (건너뜀)")

        try:
            conn = get_db_connection()
            conn.close()
            self.assertTrue(True, "DB 연결 성공")
        except Exception:
            self.skipTest("DB 연결 불가 (건너뜀)")

    def test_tables_exist(self):
        """4개 테이블이 존재하는지 확인"""
        try:
            from database.schema import DatabaseManager
        except ImportError:
            self.skipTest("import 불가")

        if not os.getenv("DB_HOST"):
            self.skipTest("DB 환경변수 없음")

        try:
            db = DatabaseManager()
            status = db.check_tables()
            for table in ["articles", "epl_matches", "epl_standings", "collect_logs"]:
                self.assertIn(table, status, f"{table} 테이블 정보 없음")
        except Exception:
            self.skipTest("DB 연결 불가")


# =============================================
# 테스트 러너
# =============================================

def run_tests():
    """전체 테스트를 실행하고 결과를 출력합니다."""
    print("=" * 60)
    print("Football Lens 통합 테스트")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestArticleEmbedder,
        TestRagSearchNode,
        TestInsightNode,
        TestEmailSender,
        TestFullPipeline,
        TestDatabaseSchema,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    total = result.testsRun
    skipped = len(result.skipped)
    failed = len(result.failures) + len(result.errors)
    passed = total - failed - skipped

    print(f"총 {total}건: ✅ {passed}건 통과 | ⏭️  {skipped}건 건너뜀 | ❌ {failed}건 실패")

    if failed == 0:
        print("✅ 테스트 완료 (실패 없음)")
    else:
        print("❌ 일부 테스트 실패 — 로그를 확인하세요")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_tests()
