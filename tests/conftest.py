# -*- coding: utf-8 -*-
"""
conftest.py
===========
week1/week2/week3가 서로 sys.path.insert()로 상대 경로 임포트를
하는 이 프로젝트의 구조에 맞춰, 테스트 실행 전에 필요한 경로를
전부 sys.path에 넣어둔다. 각 테스트 파일은 이 경로 설정에 의존하고
바로 `from nodes import ...` 같은 식으로 임포트하면 된다.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in [
    ROOT,
    os.path.join(ROOT, "week1"),
    os.path.join(ROOT, "week2"),
    os.path.join(ROOT, "week3"),
    os.path.join(ROOT, "week3", "dashboard"),
    os.path.join(ROOT, "week3", "dashboard", "tabs"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)
