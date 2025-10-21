#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배치 문서 처리 파이프라인 실행 스크립트
"""

import sys
from pathlib import Path

# flow 모듈을 import path에 추가
sys.path.append(str(Path(__file__).parent / "flow"))

# 공통 모듈을 찾기 위해 상위 경로를 sys.path에 추가
parent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent_dir))

from batch_document_processing_pipeline import batch_document_processing_pipeline


def main():
    """배치 파이프라인 실행"""
    
    # 명령행 인수 처리
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='배치 문서 처리 파이프라인 실행')
    parser.add_argument('--folder', '-f', 
                       default=os.getenv('DEFAULT_FOLDER_PATH', './uploads'),
                       help='처리할 폴더 경로')
    parser.add_argument('--max-pages', '-p', 
                       type=int, 
                       default=5,
                       help='처리할 최대 페이지 수')
    parser.add_argument('--max-file-size', '-s', 
                       type=float, 
                       default=50.0,
                       help='처리할 최대 파일 크기 (MB)')
    
    args = parser.parse_args()
    folder_path = args.folder
    
    print("📁 배치 문서 처리 파이프라인")
    print(f"   폴더: {folder_path}")
    print(f"   최대 페이지: {args.max_pages}페이지")
    print(f"   최대 파일 크기: {args.max_file_size}MB")
    print("=" * 50)
    
    try:
        # 배치 처리 실행
        result = batch_document_processing_pipeline(
            folder_path=folder_path,
            max_pages=5,
            max_file_size_mb=50.0,
            skip_existing=True
        )
        
        # 결과 출력
        print("\n📊 최종 결과:")
        print(f"   - 상태: {result['status']}")
        print(f"   - 발견된 파일: {result['total_files_found']}개")
        print(f"   - 처리 대상: {result['total_files_processed']}개")
        print(f"   - 성공: {result['successful_files']}개")
        print(f"   - 실패: {result['failed_files']}개")
        print(f"   - 건너뜀: {result['skipped_files']}개")
        print(f"   - 총 시간: {result['total_duration_seconds']:.1f}초")
        
        if 'detailed_stats' in result:
            stats = result['detailed_stats']
            print(f"\n📈 상세 통계:")
            print(f"   - 처리된 페이지: {stats['total_pages_processed']}페이지")
            print(f"   - 생성된 벡터: {stats['total_vectors_created']}개")
            print(f"   - 저장된 청크: {stats['total_chunks_saved']}개")
        
        return 0
        
    except Exception as e:
        print(f"❌ 배치 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
