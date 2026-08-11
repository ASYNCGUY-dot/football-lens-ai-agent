# -*- coding: utf-8 -*-
"""
test_embedder_e5_prefix.py
===========================
week3/rag/embedder.py의 e5 접두사 처리에 대한 테스트.

e5 계열 임베딩 모델은 문서에 "passage: ", 질의에 "query: " 접두사를
붙여서 학습됐기 때문에 검색할 때도 똑같이 붙여야 한다. 안 붙여도
에러가 전혀 안 나고 검색 품질만 조용히 떨어지기 때문에(2026-07-27
실측: 실제 기사 150건 기준 Precision@5가 0.867 → 크게 하락) 사람이
알아채기 어렵다. 그래서 회귀 테스트로 고정해 둔다.

동시에 e5가 아닌 모델(all-MiniLM 등)에는 접두사가 붙으면 안 된다 —
그 모델들은 접두사 없이 학습돼서 오히려 방해가 된다.
"""
import sys
import unittest.mock as mock

sys.path.insert(0, "week3")

from rag.embedder import ArticleEmbedder


def _embedder(model_name):
    return ArticleEmbedder(model_name=model_name)


def test_e5_model_detected_by_name():
    assert _embedder("intfloat/multilingual-e5-small")._is_e5_model() is True
    assert _embedder("intfloat/multilingual-e5-base")._is_e5_model() is True


def test_non_e5_model_not_detected():
    assert _embedder("sentence-transformers/all-MiniLM-L6-v2")._is_e5_model() is False
    assert _embedder("jhgan/ko-sroberta-multitask")._is_e5_model() is False


def test_documents_get_passage_prefix_for_e5():
    e = _embedder("intfloat/multilingual-e5-small")
    fake_model = mock.MagicMock()
    fake_model.encode.return_value = mock.MagicMock(tolist=lambda: [[0.1], [0.2]])
    with mock.patch.object(e, "_get_model", return_value=fake_model):
        e._embed_texts(["손흥민 멀티골", "K리그 순위"])
    passed = fake_model.encode.call_args[0][0]
    assert passed == ["passage: 손흥민 멀티골", "passage: K리그 순위"]


def test_documents_not_prefixed_for_non_e5():
    e = _embedder("sentence-transformers/all-MiniLM-L6-v2")
    fake_model = mock.MagicMock()
    fake_model.encode.return_value = mock.MagicMock(tolist=lambda: [[0.1]])
    with mock.patch.object(e, "_get_model", return_value=fake_model):
        e._embed_texts(["손흥민 멀티골"])
    passed = fake_model.encode.call_args[0][0]
    assert passed == ["손흥민 멀티골"]


def test_query_gets_query_prefix_for_e5():
    e = _embedder("intfloat/multilingual-e5-small")
    fake_model = mock.MagicMock()
    fake_model.encode.return_value = mock.MagicMock(tolist=lambda: [[0.1]])
    fake_collection = mock.MagicMock()
    fake_collection.count.return_value = 10
    fake_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]], "documents": [[]]}
    with mock.patch.object(e, "_get_model", return_value=fake_model), \
         mock.patch.object(e, "_get_collection", return_value=fake_collection):
        e.search("K리그1 경기 결과", n_results=3)
    passed = fake_model.encode.call_args[0][0]
    assert passed == ["query: K리그1 경기 결과"]


def test_query_not_prefixed_for_non_e5():
    e = _embedder("sentence-transformers/all-MiniLM-L6-v2")
    fake_model = mock.MagicMock()
    fake_model.encode.return_value = mock.MagicMock(tolist=lambda: [[0.1]])
    fake_collection = mock.MagicMock()
    fake_collection.count.return_value = 10
    fake_collection.query.return_value = {"ids": [[]], "metadatas": [[]], "distances": [[]], "documents": [[]]}
    with mock.patch.object(e, "_get_model", return_value=fake_model), \
         mock.patch.object(e, "_get_collection", return_value=fake_collection):
        e.search("K리그1 경기 결과", n_results=3)
    passed = fake_model.encode.call_args[0][0]
    assert passed == ["K리그1 경기 결과"]
