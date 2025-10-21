#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
문서 처리 파이프라인 실행 스크립트
"""

import argparse
import os
import sys
from pathlib import Path

# flow 경로 추가
flow_path = Path(__file__).parent / "flow"
sys.path.insert(0, str(flow_path))

# 공통 모듈을 찾기 위해 상위 경로를 sys.path에 추가
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from config import config
from document_processing_pipeline import document_processing_pipeline


def main():
    """메인 실행 함수"""
    print("🔧 환경 설정 확인 중...")
    config.print_config()
    
    if not config.validate_config():
        print("❌ 환경 변수 설정을 확인해주세요.")
        return
    
    # 명령행 인수 처리
    parser = argparse.ArgumentParser(description='문서 처리 파이프라인 실행')
    parser.add_argument('--document', '-d', 
                       default=os.getenv('DEFAULT_DOCUMENT_PATH', './test2.pdf'),
                       help='처리할 문서 경로')
    parser.add_argument('--max-pages', '-p', 
                       type=int, 
                       default=config.MAX_PAGES_TO_PROCESS,
                       help='처리할 최대 페이지 수')
    
    args = parser.parse_args()
    document_path = args.document
    
    print(f"🚀 문서 처리 파이프라인 시작")
    print(f"📄 처리할 문서: {document_path}")
    print(f"📊 페이지 처리 제한: {args.max_pages}페이지")
    
    try:
        # 파이프라인 실행 (이미지 처리 포함, 명령행 인수에서 페이지 수 가져오기)
        result = document_processing_pipeline(
            document_path, 
            skip_image_processing=False, 
            max_pages=args.max_pages
        )
        
        if result["status"] == "success":
            print("✅ 파이프라인 실행 성공!")
            print(f" 처리 결과:")
            print(f"   - 총 페이지 수: {result['text_extraction']['total_pages']}")
            print(f"   - 캡처된 이미지 수: {len(result['image_capture']['image_paths'])}")
            print(f"   - Vector DB 항목 수: {result['vector_database']['total_documents']}")
            print(f"   - 사용된 임베딩 모델: {result['vector_database']['embedding_model']}")
            print(f"   - 임베딩 차원: {result['vector_database']['embedding_dimension']}")
        else:
            print("❌ 파이프라인 실행 실패!")
            print(f"오류: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
