#!/usr/bin/env python3
"""
배치 문서 처리 파이프라인
- 폴더의 모든 PDF 파일을 일괄 처리
- 기존 document_processing_pipeline의 내부 태스크들을 직접 사용
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 설정 및 데이터베이스
from config import config
from database import Document, get_db_session

# 기존 document_processing_pipeline의 태스크들 import
from document_processing_pipeline import (
    capture_page_images,
    complete_processing_job,
    create_document_metadata,
    create_processing_job,
    create_vector_database,
    extract_text_from_document,
    generate_image_descriptions,
    initialize_database,
    save_document_chunk,
    update_document_processing_status,
)
from prefect import flow, get_run_logger, task
from prefect.context import get_run_context
from prefect.task_runners import ConcurrentTaskRunner

# Vector DB (Milvus)
from pymilvus import Collection, connections

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@task(name="폴더_PDF_파일_검색")
def find_pdf_files(folder_path: str) -> List[str]:
    """폴더에서 모든 PDF 파일을 찾습니다"""
    logger = get_run_logger()
    
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"경로가 폴더가 아닙니다: {folder_path}")
    
    # PDF 파일 검색 (대소문자 구분 없이)
    pdf_files = []
    for ext in ['*.pdf', '*.PDF']:
        pdf_files.extend(folder.glob(ext))
    
    # 재귀적 검색 (하위 폴더도 포함)
    for ext in ['**/*.pdf', '**/*.PDF']:
        pdf_files.extend(folder.glob(ext))
    
    # 중복 제거 및 문자열로 변환
    pdf_paths = sorted(list(set([str(f) for f in pdf_files])))
    
    logger.info(f"📂 폴더 '{folder_path}'에서 {len(pdf_paths)}개의 PDF 파일 발견")
    for i, pdf_path in enumerate(pdf_paths, 1):
        logger.info(f"   {i}. {Path(pdf_path).name}")
    
    return pdf_paths

@task(name="파일_크기_필터링")
def filter_files_by_size(pdf_files: List[str], max_size_mb: float = 50.0) -> List[str]:
    """파일 크기로 필터링 (너무 큰 파일 제외)"""
    logger = get_run_logger()
    
    filtered_files = []
    max_size_bytes = max_size_mb * 1024 * 1024
    
    for pdf_file in pdf_files:
        file_path = Path(pdf_file)
        if file_path.exists():
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size <= max_size_bytes:
                filtered_files.append(pdf_file)
                logger.info(f"✅ {file_path.name} ({file_size_mb:.1f}MB) - 처리 대상")
            else:
                logger.warning(f"⚠️ {file_path.name} ({file_size_mb:.1f}MB) - 크기 초과로 제외")
        else:
            logger.error(f"❌ 파일이 존재하지 않음: {pdf_file}")
    
    logger.info(f"📊 필터링 결과: {len(filtered_files)}/{len(pdf_files)} 파일이 처리 대상")
    return filtered_files

@task(name="단일_문서_완전_처리")
def process_single_document_complete(document_path: str, max_pages: int = None, skip_image_processing: bool = False, document_type: str = 'common') -> Dict[str, Any]:
    """단일 문서의 전체 처리 과정을 실행하는 태스크"""
    logger = get_run_logger()
    
    try:
        logger.info(f"🚀 문서 처리 시작: {Path(document_path).name}")
        
        # 입력 파일 존재 확인
        if not Path(document_path).exists():
            raise FileNotFoundError(f"문서 파일을 찾을 수 없습니다: {document_path}")
        
        # 환경 변수 검증
        if not config.validate_config():
            raise ValueError("환경 변수 설정을 확인해주세요.")
        
        # 0단계: 데이터베이스 초기화
        logger.info("🗄️ 데이터베이스 초기화")
        db_initialized = initialize_database()
        if not db_initialized:
            logger.warning("⚠️ PostgreSQL 연결 실패, 메타데이터 저장 없이 진행")
        
        # 문서 메타데이터 생성
        doc_metadata = None
        job_id = None
        if db_initialized:
            try:
                doc_metadata = create_document_metadata(document_path, document_type)
                flow_run_context = get_run_context()
                flow_run_id = str(flow_run_context.flow_run.id) if flow_run_context and flow_run_context.flow_run else "batch_run"
                job_id = create_processing_job(doc_metadata["doc_id"], flow_run_id)
                logger.info(f"📋 문서 ID: {doc_metadata['doc_id']}")
                
                # 이미 완료된 문서인지 확인
                if not doc_metadata["is_new"]:
                    logger.info(f"⏭️ 이미 완료된 문서 건너뛰기: {Path(document_path).name}")
                    return {
                        "document_path": document_path,
                        "status": "skipped",
                        "reason": "already_completed",
                        "doc_id": doc_metadata["doc_id"]
                    }
            except Exception as e:
                logger.warning(f"⚠️ 문서 메타데이터 생성 실패: {str(e)}")
                db_initialized = False
        
        # 1단계: 텍스트 추출
        if job_id:
            update_job_progress(job_id, "텍스트 추출 시작", 0)
            
        logger.info("📄 1단계: 텍스트 추출")
        text_result = extract_text_from_document(document_path, max_pages)
        
        if job_id:
            update_job_progress(job_id, f"텍스트 추출 완료 - {text_result['total_pages']}페이지", 1,
                              {"extracted_pages": text_result['total_pages']})
        
        if skip_image_processing:
            # 이미지 처리 건너뛰기
            logger.info("⏭️ 2-3단계: 이미지 처리 건너뛰기")
            image_result = {"image_paths": []}
            description_result = {"image_descriptions": {}, "total_images": 0}
            
            if job_id:
                update_job_progress(job_id, "이미지 처리 건너뛰기", 3)
                
        else:
            # 2단계: 페이지별 이미지 캡처
            if job_id:
                update_job_progress(job_id, "페이지별 이미지 캡처 시작", 1)
                
            logger.info("🖼️ 2단계: 페이지별 이미지 캡처")
            image_result = capture_page_images(document_path, max_pages=max_pages)
            
            if job_id:
                update_job_progress(job_id, f"이미지 캡처 완료 - {len(image_result['image_paths'])}개", 2,
                                  {"captured_images": len(image_result['image_paths'])})
            
            # 3단계: GPT를 이용한 이미지 설명 생성
            if job_id:
                update_job_progress(job_id, "GPT 이미지 설명 생성 시작", 2)
                
            logger.info("🤖 3단계: GPT 이미지 설명 생성")
            description_result = generate_image_descriptions(image_result["image_paths"])
            
            if job_id:
                update_job_progress(job_id, f"GPT 설명 생성 완료 - {description_result['total_images']}개", 3,
                                  {"generated_descriptions": description_result['total_images']})
        
        # 4단계: Vector DB 구성
        if job_id:
            update_job_progress(job_id, "Vector DB 구성 시작 (임베딩 생성)", 3)
            
        logger.info("🗄️ 4단계: Vector DB 구성")
        vector_result = create_vector_database(
            text_result, 
            description_result, 
            document_path
        )
        
        if job_id:
            update_job_progress(job_id, f"Vector DB 구성 완료 - {vector_result['total_documents']}개 벡터", 4,
                              {"vector_documents": vector_result['total_documents'],
                               "embedding_model": vector_result['embedding_model']})
        
        # 5단계: PostgreSQL에 청크 데이터 저장
        saved_chunks = 0
        if db_initialized and doc_metadata and vector_result.get("total_documents", 0) > 0:
            logger.info("💾 5단계: PostgreSQL에 청크 데이터 저장")
            try:
                # Milvus에서 방금 삽입된 데이터를 읽어와서 PostgreSQL에 저장
                connections.connect("default", uri=config.MILVUS_URI)
                collection = Collection(config.MILVUS_COLLECTION_NAME)
                collection.load()
                
                # 현재 문서의 모든 청크 데이터 조회
                results = collection.query(
                    expr=f'document_path == "{document_path}"',
                    output_fields=["id", "document_path", "page_number", "content_type", 
                                 "content", "text_content", "image_description", "image_path"]
                )
                
                for doc_data in results:
                    chunk_data = {
                        "content_type": doc_data.get("content_type", "combined"),
                        "content": doc_data.get("content", ""),
                        "text_content": doc_data.get("text_content", ""),
                        "image_description": doc_data.get("image_description", ""),
                        "image_path": doc_data.get("image_path", ""),
                        "milvus_id": str(doc_data.get("id", ""))
                    }
                    
                    save_document_chunk(
                        doc_metadata["doc_id"], 
                        doc_data.get("page_number", 0), 
                        chunk_data
                    )
                    saved_chunks += 1
                    
                # 문서 처리 상태 업데이트
                update_document_processing_status(
                    doc_metadata["doc_id"], 
                    "completed",
                    total_pages=text_result['total_pages'],
                    processed_pages=text_result['total_pages'],
                    vector_count=vector_result['total_documents']
                )
                
                # 작업 완료 처리
                if job_id:
                    complete_processing_job(job_id, saved_chunks, vector_result['total_documents'])
                    
                logger.info(f"✅ PostgreSQL 저장 완료: {saved_chunks}개 청크")
                
            except Exception as e:
                logger.error(f"❌ PostgreSQL 저장 실패: {str(e)}")
                if doc_metadata and job_id:
                    try:
                        update_document_processing_status(doc_metadata["doc_id"], "failed", error_log=str(e))
                        complete_processing_job(job_id, saved_chunks, vector_result['total_documents'], str(e))
                    except:
                        pass
        
        # 성공 결과 반환
        result = {
            "document_path": document_path,
            "status": "success",
            "doc_id": doc_metadata.get("doc_id") if doc_metadata else None,
            "total_pages": text_result['total_pages'],
            "captured_images": len(image_result['image_paths']),
            "generated_descriptions": description_result['total_images'],
            "vector_documents": vector_result['total_documents'],
            "saved_chunks": saved_chunks,
            "processing_time": datetime.now().isoformat()
        }
        
        logger.info(f"✅ 문서 처리 완료: {Path(document_path).name}")
        logger.info(f"   📊 페이지: {result['total_pages']}, 이미지: {result['captured_images']}, 벡터: {result['vector_documents']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 문서 처리 실패: {Path(document_path).name} - {str(e)}")
        
        # 실패 시 메타데이터 업데이트
        if db_initialized and doc_metadata and job_id:
            try:
                update_document_processing_status(doc_metadata["doc_id"], "failed", error_log=str(e))
                complete_processing_job(job_id, 0, 0, str(e))
            except:
                pass
        
        return {
            "document_path": document_path,
            "status": "failed",
            "error": str(e),
            "failure_time": datetime.now().isoformat()
        }

@flow(
    name="batch_document_processing_pipeline",
    description="폴더의 모든 PDF 파일을 일괄 처리하는 배치 파이프라인",
    task_runner=ConcurrentTaskRunner(max_workers=2)  # 동시 처리 파일 수 제한
)
def batch_document_processing_pipeline(
    folder_path: str,
    max_pages: int = None,
    max_file_size_mb: float = 50.0,
    skip_existing: bool = True
):
    """
    폴더 배치 문서 처리 파이프라인 메인 함수
    
    Args:
        folder_path: 처리할 폴더 경로
        max_pages: 각 문서당 처리할 최대 페이지 수
        max_file_size_mb: 처리할 최대 파일 크기 (MB)
        skip_existing: 이미 처리된 파일 건너뛰기 여부
    """
    logger = get_run_logger()
    logger.info(f"📁 배치 문서 처리 파이프라인 시작: {folder_path}")
    
    # 환경 변수 검증
    if not config.validate_config():
        raise ValueError("환경 변수 설정을 확인해주세요.")
    
    start_time = datetime.now()
    
    # 1단계: PDF 파일 검색
    logger.info("🔍 1단계: PDF 파일 검색")
    pdf_files = find_pdf_files(folder_path)
    
    if not pdf_files:
        logger.warning(f"⚠️ '{folder_path}' 폴더에서 PDF 파일을 찾을 수 없습니다.")
        return {
            "folder_path": folder_path,
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "status": "no_files_found",
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    # 2단계: 파일 크기 필터링
    logger.info("📏 2단계: 파일 크기 필터링")
    filtered_files = filter_files_by_size(pdf_files, max_file_size_mb)
    
    if not filtered_files:
        logger.warning("⚠️ 크기 조건을 만족하는 파일이 없습니다.")
        return {
            "folder_path": folder_path,
            "total_files": len(pdf_files),
            "processed_files": 0,
            "failed_files": 0,
            "status": "no_valid_files",
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    # 3단계: 배치 처리 (동시 처리)
    logger.info(f"⚡ 3단계: {len(filtered_files)}개 파일 배치 처리 시작")
    
    # 각 파일을 병렬로 처리 (실제 태스크들 직접 실행)
    processing_futures = []
    for pdf_file in filtered_files:
        future = process_single_document_complete.submit(
            pdf_file, 
            max_pages=max_pages,
            skip_image_processing=False
        )
        processing_futures.append(future)
    
    # 모든 처리 완료 대기
    processing_results = [future.result() for future in processing_futures]
    
    # 결과 집계
    successful_files = [r for r in processing_results if r["status"] == "success"]
    failed_files = [r for r in processing_results if r["status"] == "failed"]
    skipped_files = [r for r in processing_results if r["status"] == "skipped"]
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    # 최종 결과
    batch_result = {
        "folder_path": folder_path,
        "total_files_found": len(pdf_files),
        "total_files_processed": len(filtered_files),
        "successful_files": len(successful_files),
        "failed_files": len(failed_files),
        "skipped_files": len(skipped_files),
        "processing_results": processing_results,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_duration_seconds": total_duration,
        "status": "completed",
        "settings": {
            "max_pages": max_pages,
            "max_file_size_mb": max_file_size_mb,
            "max_concurrent_workers": 2,
            "skip_existing": skip_existing
        }
    }
    
    # 상세 통계 계산
    total_pages_processed = sum(r.get("total_pages", 0) for r in successful_files)
    total_vectors_created = sum(r.get("vector_documents", 0) for r in successful_files)
    total_chunks_saved = sum(r.get("saved_chunks", 0) for r in successful_files)
    
    # 결과 요약 출력
    logger.info("📊 배치 처리 완료 요약:")
    logger.info(f"   - 총 PDF 파일: {len(pdf_files)}개")
    logger.info(f"   - 처리 대상: {len(filtered_files)}개")
    logger.info(f"   - 성공: {len(successful_files)}개")
    logger.info(f"   - 실패: {len(failed_files)}개")
    logger.info(f"   - 건너뜀: {len(skipped_files)}개 (이미 완료된 문서)")
    logger.info(f"   - 총 페이지: {total_pages_processed}페이지")
    logger.info(f"   - 총 벡터: {total_vectors_created}개")
    logger.info(f"   - 총 청크: {total_chunks_saved}개")
    logger.info(f"   - 총 처리 시간: {total_duration:.1f}초")
    
    if successful_files:
        logger.info("✅ 성공한 파일들:")
        for success in successful_files:
            logger.info(f"   - {Path(success['document_path']).name}: "
                       f"{success['total_pages']}페이지, {success['vector_documents']}벡터")
    
    if skipped_files:
        logger.info("⏭️ 건너뛴 파일들:")
        for skipped in skipped_files:
            logger.info(f"   - {Path(skipped['document_path']).name}: {skipped.get('reason', 'unknown')}")
    
    if failed_files:
        logger.warning("❌ 실패한 파일들:")
        for failed in failed_files:
            logger.warning(f"   - {Path(failed['document_path']).name}: {failed['error']}")
    
    # 상세 결과도 batch_result에 추가
    batch_result.update({
        "detailed_stats": {
            "total_pages_processed": total_pages_processed,
            "total_vectors_created": total_vectors_created,
            "total_chunks_saved": total_chunks_saved
        }
    })
    
    return batch_result

# ===============================
# 실행 예제
# ===============================
if __name__ == "__main__":
    # 설정 확인
    config.print_config()
    
    # 테스트 실행 - 환경변수 또는 기본값 사용
    import os
    test_folder = os.getenv("TEST_FOLDER_PATH", "./test_folder")
    
    print(f"🧪 테스트 폴더 배치 처리 시작: {test_folder}")
    result = batch_document_processing_pipeline(
        folder_path=test_folder,
        max_pages=3,  # 테스트용으로 3페이지만
        max_file_size_mb=100.0
    )
    print(f"🎯 배치 처리 결과: {result['status']}")
    print(f"   성공: {result['successful_files']}/{result['total_files_processed']} 파일")
