#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    import src.main
    print("✅ src.main 임포트 성공")
except SyntaxError as e:
    print(f"❌ 문법 오류: {e}")
    print(f"   파일: {e.filename}")
    print(f"   줄: {e.lineno}")
    print(f"   위치: {e.offset}")
except Exception as e:
    print(f"❌ 기타 오류: {e}")
