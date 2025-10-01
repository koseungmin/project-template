#!/usr/bin/env python3
"""
4단계 문서 처리 파이프라인
1. 문서 텍스트 추출 (Azure AI Search)
2. 페이지별 이미지 캡처 및 저장
3. GPT를 이용한 이미지 설명 생성
4. 텍스트와 설명을 합쳐서 Vector DB 구성 (Azure OpenAI 임베딩 사용)
"""

import asyncio
import base64
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

# Azure OpenAI (통합 openai 패키지 사용)
import openai

# 환경 설정
from config import config

# 데이터베이스 관리 (공통 모듈 사용)
from database import db_manager, get_db_session
from pdf2image import convert_from_path
from PIL import Image
from prefect import flow, get_run_logger, task
from prefect.futures import PrefectFuture
from prefect.task_runners import ConcurrentTaskRunner

# Vector DB (Milvus)
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from shared_core import (
    Document,
    DocumentChunk,
    DocumentChunkService,
    DocumentService,
    ProcessingJob,
    ProcessingJobService,
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# PostgreSQL 관련 태스크
# ===============================

@task(name="초기화_데이터베이스_연결")
def initialize_database():
    """데이터베이스 연결 초기화"""
    logger = get_run_logger()
    try:
        db_manager.initialize()
        if db_manager.test_connection():
            logger.info("✅ PostgreSQL 데이터베이스 연결 성공")
            return True
        else:
            logger.error("❌ PostgreSQL 데이터베이스 연결 실패")
            return False
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 오류: {str(e)}")
        return False

@task(name="생성_문서_메타데이터")
def create_document_metadata(document_path: str, document_type: str = 'common') -> Dict[str, Any]:
    """문서 메타데이터 생성 및 저장 (공통 모듈 사용)"""
    logger = get_run_logger()
    
    try:
        # 공통 모듈의 DocumentService 사용
        with next(get_db_session()) as session:
            doc_service = DocumentService(session)
            
            # 문서 생성 (파일 경로 기반)
            result = doc_service.create_document_from_path(
                file_path=document_path,
                user_id="system",  # 시스템 사용자
                document_type=document_type,
                is_public=True  # Prefect에서 처리하는 문서는 공개
            )
            
            logger.info(f"✅ 문서 메타데이터 생성 완료: {result['document_id']}")
            return {
                "doc_id": result["document_id"],
                "doc_name": result["document_name"],
                "file_size": result["file_size"],
                "file_type": result["file_type"],
                "file_hash": result["file_hash"],
                "status": result["status"]
            }
            
    except Exception as e:
        logger.error(f"❌ 문서 메타데이터 생성 실패: {str(e)}")
        raise

@task(name="생성_처리_작업_로그")
def create_processing_job(doc_id: str, flow_run_id: str) -> str:
    """처리 작업 로그 생성 (공통 모듈 사용)"""
    logger = get_run_logger()
    
    try:
        with next(get_db_session()) as session:
            job_service = ProcessingJobService(session)
            
            result = job_service.create_job(
                doc_id=doc_id,
                job_type="document_processing",
                flow_run_id=flow_run_id,
                total_steps=4  # 텍스트 추출, 이미지 캡처, GPT 설명, Vector DB
            )
            
            logger.info(f"✅ 처리 작업 로그 생성: {result['job_id']}")
            return result["job_id"]
            
    except Exception as e:
        logger.error(f"❌ 처리 작업 로그 생성 실패: {str(e)}")
        raise

@task(name="저장_문서_청크")
def save_document_chunk(doc_id: str, page_number: int, chunk_data: Dict[str, Any]) -> str:
    """문서 청크 정보를 PostgreSQL에 저장 (공통 모듈 사용)"""
    logger = get_run_logger()
    
    try:
        with next(get_db_session()) as session:
            chunk_service = DocumentChunkService(session)
            
            result = chunk_service.create_chunk(
                doc_id=doc_id,
                page_number=page_number,
                chunk_type=chunk_data.get("content_type", "unknown"),
                content=chunk_data.get("content", ""),
                image_description=chunk_data.get("image_description", ""),
                image_path=chunk_data.get("image_path", ""),
                milvus_id=chunk_data.get("milvus_id", ""),
                embedding_model="text-embedding-3-large",
                vector_dimension=3072,
                metadata_json={
                    "processing_timestamp": datetime.utcnow().isoformat(),
                    "original_data": chunk_data
                }
            )
            
            logger.info(f"✅ 문서 청크 저장: {result['chunk_id']}")
            return result["chunk_id"]
            
    except Exception as e:
        logger.error(f"❌ 문서 청크 저장 실패: {str(e)}")
        raise

@task(name="업데이트_문서_처리_상태")
def update_document_processing_status(doc_id: str, status: str, **kwargs):
    """문서 처리 상태 업데이트 (공통 모듈 사용)"""
    logger = get_run_logger()
    
    try:
        with next(get_db_session()) as session:
            doc_service = DocumentService(session)
            
            success = doc_service.update_document_processing_status(
                document_id=doc_id,
                status=status,
                **kwargs
            )
            
            if success:
                logger.info(f"✅ 문서 처리 상태 업데이트: {doc_id} -> {status}")
            else:
                logger.warning(f"⚠️ 문서 처리 상태 업데이트 실패: {doc_id}")
            
    except Exception as e:
        logger.error(f"❌ 문서 처리 상태 업데이트 실패: {str(e)}")
        raise

@task(name="업데이트_작업_진행률")
def update_job_progress(job_id: str, current_step: str, completed_steps: int = None, additional_data: dict = None):
    """작업 진행률 실시간 업데이트"""
    logger = get_run_logger()
    
    try:
        with next(get_db_session()) as session:
            job_service = ProcessingJobService(session)
            
            # 업데이트할 데이터 준비
            update_data = {
                "current_step": current_step,
                "updated_at": datetime.utcnow()
            }
            
            if completed_steps is not None:
                update_data["completed_steps"] = completed_steps
            
            if additional_data:
                update_data.update(additional_data)
            
            success = job_service.update_job_status(job_id, "running", **update_data)
            
            if success:
                progress_percent = 0
                if completed_steps is not None:
                    # total_steps는 4로 고정 (텍스트 추출, 이미지 캡처, GPT 설명, Vector DB)
                    progress_percent = (completed_steps / 4) * 100
                logger.info(f"📊 작업 진행률 업데이트: {job_id} - {current_step} ({progress_percent:.0f}%)")
            else:
                logger.warning(f"⚠️ 작업 진행률 업데이트 실패: {job_id}")
            
            return success
            
    except Exception as e:
        logger.error(f"❌ 작업 진행률 업데이트 실패: {str(e)}")
        # 진행률 업데이트 실패가 전체 파이프라인을 중단시키지 않도록 예외를 삼킴
        return False

@task(name="완료_처리_작업")
def complete_processing_job(job_id: str, success_count: int, total_count: int, error_message: str = None):
    """처리 작업 완료"""
    logger = get_run_logger()
    
    try:
        with next(get_db_session()) as session:
            job = session.query(ProcessingJob).filter_by(job_id=job_id).first()
            if not job:
                raise ValueError(f"처리 작업을 찾을 수 없습니다: {job_id}")
            
            # 작업 상태 업데이트
            job.status = "completed" if error_message is None else "failed"
            job.completed_at = datetime.utcnow()
            job.completed_steps = 4  # 모든 단계 완료
            job.current_step = "완료" if error_message is None else f"실패: {error_message}"
            
            # 결과 데이터 저장
            job.result_data = {
                "total_chunks": total_count,
                "successful_chunks": success_count,
                "failed_chunks": total_count - success_count,
                "duration_seconds": int((datetime.utcnow() - job.started_at).total_seconds()),
                "completion_time": datetime.utcnow().isoformat()
            }
            
            if error_message:
                job.error_message = error_message
            
            session.commit()
            logger.info(f"✅ 처리 작업 완료: {job_id} - 성공: {success_count}/{total_count} 청크")
            
    except Exception as e:
        logger.error(f"❌ 처리 작업 완료 처리 실패: {str(e)}")
        raise

# ===============================
# Azure OpenAI 임베딩 함수 (별도 API 버전 사용)
# ===============================
def get_azure_openai_embedding(text: str) -> List[float]:
    """Azure OpenAI를 사용하여 텍스트 임베딩을 생성합니다. (임베딩 전용 API 버전)"""
    try:
        # Azure OpenAI 클라이언트 생성 (새로운 API 방식)
        client = openai.AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_KEY,
            api_version=config.AZURE_OPENAI_EMBEDDING_API_VERSION
        )
        
        logger.info(f"🔗 임베딩 API 버전: {config.AZURE_OPENAI_EMBEDDING_API_VERSION}")
        
        response = client.embeddings.create(
            model=config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"❌ 임베딩 생성 실패: {str(e)}")
        raise

# ===============================
# 1단계: 텍스트 추출 (Azure AI Search)
# ===============================
@task(name="extract_text_from_document")
def extract_text_from_document(document_path: str, max_pages: int = None) -> Dict[str, Any]:
    """문서에서 텍스트를 추출합니다."""
    logger = get_run_logger()
    logger.info(f"📄 텍스트 추출 시작: {document_path}")
    
    try:
        # PDF 파일 열기
        doc = fitz.open(document_path)
        total_pages = len(doc)  # 문서 닫기 전에 페이지 수 저장
        
        # 처리할 페이지 수 제한
        if max_pages and max_pages < total_pages:
            pages_to_process = max_pages
            logger.info(f"📄 페이지 수 제한: {pages_to_process}/{total_pages} 페이지만 처리")
        else:
            pages_to_process = total_pages
        
        extracted_text = {}
        
        for page_num in range(pages_to_process):
            page = doc.load_page(page_num)
            text = page.get_text()
            extracted_text[f"page_{page_num + 1}"] = {
                "text": text,
                "page_number": page_num + 1,
                "word_count": len(text.split())
            }
        
        doc.close()
        
        logger.info(f"✅ 텍스트 추출 완료: {len(extracted_text)} 페이지")
        return {
            "document_path": document_path,
            "total_pages": total_pages,
            "extracted_text": extracted_text,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 텍스트 추출 실패: {str(e)}")
        raise

# ===============================
# 2단계: 페이지별 이미지 캡처 및 저장
# ===============================
@task(name="capture_page_images")
def capture_page_images(document_path: str, output_dir: str = None, max_pages: int = None) -> Dict[str, Any]:
    """PDF의 각 페이지를 이미지로 캡처하여 저장합니다."""
    logger = get_run_logger()
    logger.info(f"️ 페이지별 이미지 캡처 시작: {document_path}")
    
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # PDF를 이미지로 변환 (페이지 수 제한)
        if max_pages:
            logger.info(f"🖼️ 페이지 수 제한: 처음 {max_pages}페이지만 이미지 변환")
            images = convert_from_path(document_path, dpi=300, first_page=1, last_page=max_pages)
        else:
            images = convert_from_path(document_path, dpi=300)
        
        image_paths = []
        document_name = Path(document_path).stem
        
        for i, image in enumerate(images):
            # 페이지별 이미지 저장
            image_filename = f"{document_name}_page_{i+1}.png"
            image_path = output_path / image_filename
            image.save(image_path, "PNG", quality=95)
            image_paths.append(str(image_path))
            
            logger.info(f"💾 페이지 {i+1} 이미지 저장: {image_path}")
        
        logger.info(f"✅ 이미지 캡처 완료: {len(image_paths)}개 페이지")
        return {
            "document_path": document_path,
            "image_paths": image_paths,
            "output_directory": str(output_path),
            "capture_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 이미지 캡처 실패: {str(e)}")
        raise

# ===============================
# 3단계: GPT를 이용한 이미지 설명 생성 (별도 API 버전 사용)
# ===============================
@task(name="generate_image_descriptions")
def generate_image_descriptions(image_paths: List[str]) -> Dict[str, Any]:
    """이미지들을 GPT Vision API를 통해 설명을 생성합니다. (GPT Vision 전용 API 버전)"""
    logger = get_run_logger()
    logger.info(f"🤖 GPT 이미지 설명 생성 시작: {len(image_paths)}개 이미지")
    
    try:
        # Azure OpenAI 클라이언트 생성 (새로운 API 방식)
        client = openai.AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION
        )
        
        logger.info(f"🔗 GPT Vision API 버전: {config.AZURE_OPENAI_API_VERSION}")
        
        descriptions = {}
        
        for image_path in image_paths:
            try:
                # 이미지를 base64로 인코딩
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                # GPT Vision API 호출 (새로운 API 방식)
                response = client.chat.completions.create(
                    model=config.AZURE_OPENAI_DEPLOYMENT_NAME,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "이 이미지의 내용을 자세히 설명해주세요. 텍스트, 차트, 그래프, 표 등 모든 요소를 포함하여 설명해주세요."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )
                
                description = response.choices[0].message.content
                descriptions[image_path] = {
                    "description": description,
                    "page_number": int(Path(image_path).stem.split('_')[-1].replace('page_', '')),
                    "generation_timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"📝 페이지 {descriptions[image_path]['page_number']} 설명 생성 완료")
                
            except Exception as e:
                logger.error(f"❌ 이미지 설명 생성 실패 ({image_path}): {str(e)}")
                descriptions[image_path] = {
                    "description": f"설명 생성 실패: {str(e)}",
                    "page_number": 0,
                    "generation_timestamp": datetime.now().isoformat()
                }
        
        logger.info(f"✅ 이미지 설명 생성 완료: {len(descriptions)}개")
        return {
            "image_descriptions": descriptions,
            "total_images": len(image_paths),
            "generation_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ GPT 이미지 설명 생성 실패: {str(e)}")
        raise

# ===============================
# 4단계: Vector DB 구성 (Azure OpenAI 임베딩 사용)
# ===============================
@task(name="create_vector_database")
def create_vector_database(
    extracted_text: Dict[str, Any], 
    image_descriptions: Dict[str, Any],
    document_path: str
) -> Dict[str, Any]:
    """추출된 텍스트와 이미지 설명을 합쳐서 Vector DB를 구성합니다."""
    logger = get_run_logger()
    logger.info(f"🗄️ Vector DB 구성 시작 (Azure OpenAI 임베딩 사용)")
    
    try:
        # Milvus Lite 연결
        connections.connect("default", uri=config.MILVUS_URI)
        
        # 기존 컬렉션이 있다면 삭제 (차원 불일치 해결)
        collection_name = config.MILVUS_COLLECTION_NAME
        if utility.has_collection(collection_name):
            logger.info(f"🗑️ 기존 컬렉션 삭제: {collection_name}")
            utility.drop_collection(collection_name)
        
        # 컬렉션 스키마 정의 (페이지별 통합 벡터)
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="document_path", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="page_number", dtype=DataType.INT64),
            FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=50),  # "combined"
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=15000),  # 통합 콘텐츠
            FieldSchema(name="text_content", dtype=DataType.VARCHAR, max_length=10000),  # 원본 텍스트
            FieldSchema(name="image_description", dtype=DataType.VARCHAR, max_length=10000),  # 이미지 설명
            FieldSchema(name="image_path", dtype=DataType.VARCHAR, max_length=1000),  # 이미지 파일 경로
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=3072)  # Azure OpenAI text-embedding-3-large
        ]
        
        schema = CollectionSchema(fields, "Document processing pipeline vector collection")
        
        # 컬렉션 생성
        collection = Collection(collection_name, schema)
        
        # Milvus Lite 최적화 FLAT 벡터 인덱스 생성
        index_params = {
            "metric_type": "COSINE",  # Azure OpenAI 임베딩은 코사인 유사도 사용
            "index_type": "FLAT",     # Milvus Lite에서 최고 성능
            "params": {}
        }
        collection.create_index("embedding", index_params)
        logger.info(f"📚 새 컬렉션 생성: {collection_name} (3072차원)")
        
        # 데이터 준비 - 페이지별 통합 벡터 방식
        documents_to_insert = []
        embeddings_to_insert = []
        
        # 페이지별로 텍스트와 이미지 설명을 통합
        page_data_map = {}
        
        # 텍스트 데이터 수집
        for page_key, page_data in extracted_text["extracted_text"].items():
            page_num = page_data["page_number"]
            if page_num not in page_data_map:
                page_data_map[page_num] = {
                    "text_content": "",
                    "image_description": "",
                    "image_path": ""
                }
            if page_data["text"].strip():
                page_data_map[page_num]["text_content"] = page_data["text"][:10000]
        
        # 이미지 설명 데이터 수집
        for image_path, desc_data in image_descriptions["image_descriptions"].items():
            page_num = desc_data["page_number"]
            if page_num not in page_data_map:
                page_data_map[page_num] = {
                    "text_content": "",
                    "image_description": "",
                    "image_path": ""
                }
            if desc_data["description"].strip():
                page_data_map[page_num]["image_description"] = desc_data["description"][:10000]
                page_data_map[page_num]["image_path"] = image_path
        
        # 페이지별 통합 콘텐츠 생성 및 벡터화
        for page_num, page_data in page_data_map.items():
            # 텍스트와 이미지 설명을 결합
            combined_content = ""
            if page_data["text_content"]:
                combined_content += f"텍스트: {page_data['text_content']}"
            if page_data["image_description"]:
                if combined_content:
                    combined_content += " "
                combined_content += f"이미지: {page_data['image_description']}"
            
            if combined_content.strip():
                embedding = get_azure_openai_embedding(combined_content)
                
                documents_to_insert.append({
                    "document_path": document_path,
                    "page_number": page_num,
                    "content_type": "combined",  # 통합된 콘텐츠
                    "content": combined_content[:15000],  # 더 긴 길이 허용
                    "text_content": page_data["text_content"][:10000],
                    "image_description": page_data["image_description"][:10000],
                    "image_path": page_data["image_path"]
                })
                embeddings_to_insert.append(embedding)
        
        # 데이터 삽입
        if documents_to_insert:
            # 컬렉션 로드
            collection.load()
            
            # 데이터 삽입
            insert_data = [
                [doc["document_path"] for doc in documents_to_insert],
                [doc["page_number"] for doc in documents_to_insert],
                [doc["content_type"] for doc in documents_to_insert],
                [doc["content"] for doc in documents_to_insert],
                [doc["text_content"] for doc in documents_to_insert],
                [doc["image_description"] for doc in documents_to_insert],
                [doc["image_path"] for doc in documents_to_insert],
                embeddings_to_insert
            ]
            
            collection.insert(insert_data)
            collection.flush()
            
            logger.info(f"✅ Vector DB 구성 완료: {len(documents_to_insert)}개 항목 삽입")
        else:
            logger.warning("⚠️ 삽입할 데이터가 없습니다.")
        
        return {
            "collection_name": config.MILVUS_COLLECTION_NAME,
            "total_documents": len(documents_to_insert),
            "combined_documents": len([d for d in documents_to_insert if d["content_type"] == "combined"]),
            "embedding_model": "Azure OpenAI text-embedding-3-large",
            "embedding_api_version": config.AZURE_OPENAI_EMBEDDING_API_VERSION,
            "embedding_dimension": 3072,
            "structure": "page_combined_vectors",  # 페이지별 통합 벡터 구조
            "creation_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Vector DB 구성 실패: {str(e)}")
        raise


# ===============================
# 하이브리드 검색 함수들
# ===============================
@task(name="search_combined_vectors")
def search_combined_vectors(query: str, top_k: int = 5) -> Dict[str, Any]:
    """통합 벡터에서 검색 (페이지별 통합 검색)"""
    logger = get_run_logger()
    logger.info(f"🔍 통합 벡터 검색: {query}")
    
    try:
        # Milvus Lite 연결
        connections.connect("default", uri=config.MILVUS_URI)
        collection = Collection(config.MILVUS_COLLECTION_NAME)
        collection.load()
        
        # 쿼리를 벡터로 변환
        query_embedding = get_azure_openai_embedding(query)
        
        # 검색 실행
        search_params = {"metric_type": "COSINE", "params": {}}
        results = collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["document_path", "page_number", "content_type", "content", 
                          "text_content", "image_description", "image_path"]
        )
        
        # 결과 정리
        search_results = []
        for hits in results:
            for hit in hits:
                search_results.append({
                    "score": float(hit.score),
                    "document_path": hit.entity.get("document_path"),
                    "page_number": hit.entity.get("page_number"),
                    "content_type": hit.entity.get("content_type"),
                    "content": hit.entity.get("content"),
                    "text_content": hit.entity.get("text_content"),
                    "image_description": hit.entity.get("image_description"),
                    "image_path": hit.entity.get("image_path")
                })
        
        logger.info(f"✅ 통합 벡터 검색 완료: {len(search_results)}개 결과")
        return {
            "search_type": "combined_vectors",
            "query": query,
            "results": search_results,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"❌ 통합 벡터 검색 실패: {str(e)}")
        raise


@task(name="search_text_only")
def search_text_only(query: str, top_k: int = 5) -> Dict[str, Any]:
    """텍스트 콘텐츠만 검색"""
    logger = get_run_logger()
    logger.info(f"📝 텍스트 전용 검색: {query}")
    
    try:
        # Milvus Lite 연결
        connections.connect("default", uri=config.MILVUS_URI)
        collection = Collection(config.MILVUS_COLLECTION_NAME)
        collection.load()
        
        # 쿼리를 벡터로 변환
        query_embedding = get_azure_openai_embedding(query)
        
        # 검색 실행
        search_params = {"metric_type": "COSINE", "params": {}}
        results = collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["document_path", "page_number", "content_type", "content", 
                          "text_content", "image_description", "image_path"]
        )
        
        # 텍스트가 있는 결과만 필터링
        search_results = []
        for hits in results:
            for hit in hits:
                text_content = hit.entity.get("text_content", "")
                if text_content.strip():  # 텍스트가 있는 경우만
                    search_results.append({
                        "score": float(hit.score),
                        "document_path": hit.entity.get("document_path"),
                        "page_number": hit.entity.get("page_number"),
                        "content_type": "text_only",
                        "text_content": text_content,
                        "image_path": hit.entity.get("image_path")
                    })
        
        logger.info(f"✅ 텍스트 전용 검색 완료: {len(search_results)}개 결과")
        return {
            "search_type": "text_only",
            "query": query,
            "results": search_results,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"❌ 텍스트 전용 검색 실패: {str(e)}")
        raise


@task(name="search_image_only")
def search_image_only(query: str, top_k: int = 5) -> Dict[str, Any]:
    """이미지 설명만 검색"""
    logger = get_run_logger()
    logger.info(f"🖼️ 이미지 전용 검색: {query}")
    
    try:
        # Milvus Lite 연결
        connections.connect("default", uri=config.MILVUS_URI)
        collection = Collection(config.MILVUS_COLLECTION_NAME)
        collection.load()
        
        # 쿼리를 벡터로 변환
        query_embedding = get_azure_openai_embedding(query)
        
        # 검색 실행
        search_params = {"metric_type": "COSINE", "params": {}}
        results = collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["document_path", "page_number", "content_type", "content", 
                          "text_content", "image_description", "image_path"]
        )
        
        # 이미지 설명이 있는 결과만 필터링
        search_results = []
        for hits in results:
            for hit in hits:
                image_description = hit.entity.get("image_description", "")
                image_path = hit.entity.get("image_path", "")
                if image_description.strip() and image_path:  # 이미지 설명과 경로가 있는 경우만
                    search_results.append({
                        "score": float(hit.score),
                        "document_path": hit.entity.get("document_path"),
                        "page_number": hit.entity.get("page_number"),
                        "content_type": "image_only",
                        "image_description": image_description,
                        "image_path": image_path
                    })
        
        logger.info(f"✅ 이미지 전용 검색 완료: {len(search_results)}개 결과")
        return {
            "search_type": "image_only",
            "query": query,
            "results": search_results,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"❌ 이미지 전용 검색 실패: {str(e)}")
        raise


@task(name="hybrid_search")
def hybrid_search(query: str, top_k: int = 5, text_weight: float = 0.5, image_weight: float = 0.5) -> Dict[str, Any]:
    """하이브리드 검색: 텍스트와 이미지를 별도 검색 후 결과 통합"""
    logger = get_run_logger()
    logger.info(f"🔄 하이브리드 검색: {query} (텍스트 가중치: {text_weight}, 이미지 가중치: {image_weight})")
    
    try:
        # 텍스트와 이미지를 별도로 검색
        text_results = search_text_only(query, top_k)
        image_results = search_image_only(query, top_k)
        
        # 결과 통합 및 가중치 적용
        combined_results = []
        
        # 텍스트 결과 추가
        for result in text_results["results"]:
            result["weighted_score"] = result["score"] * text_weight
            result["search_source"] = "text"
            combined_results.append(result)
        
        # 이미지 결과 추가
        for result in image_results["results"]:
            result["weighted_score"] = result["score"] * image_weight
            result["search_source"] = "image"
            combined_results.append(result)
        
        # 가중치 점수로 정렬
        combined_results.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        # 상위 결과만 반환
        final_results = combined_results[:top_k]
        
        logger.info(f"✅ 하이브리드 검색 완료: {len(final_results)}개 통합 결과")
        return {
            "search_type": "hybrid",
            "query": query,
            "text_results_count": len(text_results["results"]),
            "image_results_count": len(image_results["results"]),
            "combined_results": final_results,
            "total_results": len(final_results),
            "weights": {"text": text_weight, "image": image_weight}
        }
        
    except Exception as e:
        logger.error(f"❌ 하이브리드 검색 실패: {str(e)}")
        raise


def comprehensive_search(query: str) -> Dict[str, Any]:
    """통합 검색: 4가지 검색 방식을 모두 실행하고 설정에 따라 결과 반환"""
    logger.info(f"🔍 통합 검색 시작: '{query}'")
    
    try:
        색 = {
            "query": query,
            "search_config": {
                "combined_enabled": config.SEARCH_COMBINED,
                "text_only_enabled": config.SEARCH_TEXT_ONLY,
                "image_only_enabled": config.SEARCH_IMAGE_ONLY,
                "hybrid_enabled": config.SEARCH_HYBRID,
                "hybrid_weights": {
                    "text": config.HYBRID_TEXT_WEIGHT,
                    "image": config.HYBRID_IMAGE_WEIGHT
                },
                "top_k": config.SEARCH_TOP_K
            },
            "results": {}
        }
        
        # 1. 통합 벡터 검색
        if config.SEARCH_COMBINED:
            logger.info("1️⃣ 통합 벡터 검색 실행")
            try:
                combined_results = search_combined_vectors(query, config.SEARCH_TOP_K)
                search_results["results"]["combined"] = combined_results
                logger.info(f"✅ 통합 검색 완료: {combined_results['total_results']}개 결과")
            except Exception as e:
                logger.error(f"❌ 통합 검색 실패: {str(e)}")
                search_results["results"]["combined"] = {"error": str(e)}
        
        # 2. 텍스트 전용 검색
        if config.SEARCH_TEXT_ONLY:
            logger.info("2️⃣ 텍스트 전용 검색 실행")
            try:
                text_results = search_text_only(query, config.SEARCH_TOP_K)
                search_results["results"]["text_only"] = text_results
                logger.info(f"✅ 텍스트 검색 완료: {text_results['total_results']}개 결과")
            except Exception as e:
                logger.error(f"❌ 텍스트 검색 실패: {str(e)}")
                search_results["results"]["text_only"] = {"error": str(e)}
        
        # 3. 이미지 전용 검색
        if config.SEARCH_IMAGE_ONLY:
            logger.info("3️⃣ 이미지 전용 검색 실행")
            try:
                image_results = search_image_only(query, config.SEARCH_TOP_K)
                search_results["results"]["image_only"] = image_results
                logger.info(f"✅ 이미지 검색 완료: {image_results['total_results']}개 결과")
            except Exception as e:
                logger.error(f"❌ 이미지 검색 실패: {str(e)}")
                search_results["results"]["image_only"] = {"error": str(e)}
        
        # 4. 하이브리드 검색
        if config.SEARCH_HYBRID:
            logger.info("4️⃣ 하이브리드 검색 실행")
            try:
                hybrid_results = hybrid_search(
                    query, 
                    config.SEARCH_TOP_K,
                    config.HYBRID_TEXT_WEIGHT,
                    config.HYBRID_IMAGE_WEIGHT
                )
                search_results["results"]["hybrid"] = hybrid_results
                logger.info(f"✅ 하이브리드 검색 완료: {hybrid_results['total_results']}개 결과")
            except Exception as e:
                logger.error(f"❌ 하이브리드 검색 실패: {str(e)}")
                search_results["results"]["hybrid"] = {"error": str(e)}
        
        # 결과 요약
        enabled_searches = []
        if config.SEARCH_COMBINED:
            enabled_searches.append("통합")
        if config.SEARCH_TEXT_ONLY:
            enabled_searches.append("텍스트")
        if config.SEARCH_IMAGE_ONLY:
            enabled_searches.append("이미지")
        if config.SEARCH_HYBRID:
            enabled_searches.append("하이브리드")
        
        logger.info(f"🎯 검색 완료: {', '.join(enabled_searches)} 검색 실행됨")
        
        return search_results
        
    except Exception as e:
        logger.error(f"❌ 통합 검색 실패: {str(e)}")
        raise


# ===============================
# 메인 파이프라인 Flow
# ===============================
@flow(
    name="document_processing_pipeline",
    description="4단계 문서 처리 파이프라인: 텍스트 추출 → 이미지 캡처 → GPT 설명 → Vector DB (분리된 API 버전)",
    task_runner=ConcurrentTaskRunner()
)
def document_processing_pipeline(document_path: str, skip_image_processing: bool = False, max_pages: int = None, document_type: str = 'common'):
    """
    문서 처리 파이프라인 메인 함수
    
    Args:
        document_path: 처리할 문서 파일 경로
        skip_image_processing: 이미지 처리 단계를 건너뛸지 여부 (기본값: False)
        max_pages: 처리할 최대 페이지 수 (기본값: None, 전체 페이지 처리)
    """
    logger = get_run_logger()
    logger.info(f" 문서 처리 파이프라인 시작: {document_path}")
    
    # 환경 변수 검증
    if not config.validate_config():
        raise ValueError("환경 변수 설정을 확인해주세요.")
    
    # API 버전 정보 출력
    logger.info(f"🔗 GPT Vision API 버전: {config.AZURE_OPENAI_API_VERSION}")
    logger.info(f"🔗 임베딩 API 버전: {config.AZURE_OPENAI_EMBEDDING_API_VERSION}")
    
    # 입력 파일 존재 확인
    if not Path(document_path).exists():
        raise FileNotFoundError(f"문서 파일을 찾을 수 없습니다: {document_path}")
    
    # 0단계: 데이터베이스 초기화 및 문서 메타데이터 생성
    logger.info("🗄️ 0단계: 데이터베이스 초기화 및 문서 메타데이터 생성")
    db_initialized = initialize_database()
    if not db_initialized:
        logger.warning("⚠️ PostgreSQL 연결 실패, 메타데이터 저장 없이 진행")
    
    # 문서 메타데이터 생성
    doc_metadata = None
    job_id = None
    if db_initialized:
        try:
            from prefect.context import get_run_context
            flow_run_context = get_run_context()
            flow_run_id = str(flow_run_context.flow_run.id) if flow_run_context and flow_run_context.flow_run else "unknown"
            
            doc_metadata = create_document_metadata(document_path, document_type)
            job_id = create_processing_job(doc_metadata["doc_id"], flow_run_id)
            logger.info(f"📋 문서 ID: {doc_metadata['doc_id']}, 작업 ID: {job_id}")
        except Exception as e:
            logger.warning(f"⚠️ 문서 메타데이터 생성 실패, 계속 진행: {str(e)}")
            db_initialized = False
    
    try:
        # 1단계: 텍스트 추출
        if job_id:
            update_job_progress(job_id, "텍스트 추출 시작", 0)
        
        logger.info("📄 1단계: 텍스트 추출 시작")
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
                
            logger.info("🖼️ 2단계: 페이지별 이미지 캡처 시작")
            image_result = capture_page_images(document_path, max_pages=max_pages)
            
            if job_id:
                update_job_progress(job_id, f"이미지 캡처 완료 - {len(image_result['image_paths'])}개", 2,
                                  {"captured_images": len(image_result['image_paths'])})
            
            # 3단계: GPT를 이용한 이미지 설명 생성
            if job_id:
                update_job_progress(job_id, "GPT 이미지 설명 생성 시작", 2)
                
            logger.info("🤖 3단계: GPT 이미지 설명 생성 시작")
            description_result = generate_image_descriptions(image_result["image_paths"])
            
            if job_id:
                update_job_progress(job_id, f"GPT 설명 생성 완료 - {description_result['total_images']}개", 3,
                                  {"generated_descriptions": description_result['total_images']})
        
        # 4단계: Vector DB 구성
        if job_id:
            update_job_progress(job_id, "Vector DB 구성 시작 (임베딩 생성)", 3)
            
        logger.info("🗄️ 4단계: Vector DB 구성 시작 (Azure OpenAI 임베딩)")
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
                    
                    chunk_id = save_document_chunk(
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
        
        # 결과 요약
        pipeline_result = {
            "document_path": document_path,
            "document_metadata": doc_metadata,
            "text_extraction": text_result,
            "image_capture": image_result,
            "image_descriptions": description_result,
            "vector_database": vector_result,
            "postgresql_storage": {
                "enabled": db_initialized,
                "saved_chunks": saved_chunks,
                "job_id": job_id
            },
            "pipeline_completion_time": datetime.now().isoformat(),
            "status": "success"
        }
        
        logger.info("✅ 문서 처리 파이프라인 완료!")
        logger.info(f"📊 결과 요약:")
        logger.info(f"   - 문서 ID: {doc_metadata.get('doc_id', 'N/A') if doc_metadata else 'N/A'}")
        logger.info(f"   - 총 페이지 수: {text_result['total_pages']}")
        logger.info(f"   - 캡처된 이미지 수: {len(image_result['image_paths'])}")
        logger.info(f"   - 생성된 설명 수: {description_result['total_images']}")
        logger.info(f"   - Vector DB 항목 수: {vector_result['total_documents']}")
        logger.info(f"   - PostgreSQL 저장 청크 수: {saved_chunks}")
        logger.info(f"   - 사용된 임베딩 모델: {vector_result['embedding_model']}")
        logger.info(f"   - 임베딩 API 버전: {vector_result['embedding_api_version']}")
        
        return pipeline_result
        
    except Exception as e:
        logger.error(f"❌ 파이프라인 실행 실패: {str(e)}")
        return {
            "document_path": document_path,
            "status": "failed",
            "error": str(e),
            "failure_time": datetime.now().isoformat()
        }

# ===============================
# 실행 예제
# ===============================
if __name__ == "__main__":
    # 설정 확인
    config.print_config()
    
    # 테스트 실행 - 환경변수 또는 기본값 사용
    import os
    test_document = os.getenv("TEST_DOCUMENT_PATH", "./test.pdf")
    
    if Path(test_document).exists():
        print(f"🧪 테스트 문서 처리 시작: {test_document}")
        result = document_processing_pipeline(test_document)
        print(f" 처리 결과: {result['status']}")
    else:
        print(f"⚠️ 테스트 문서를 찾을 수 없습니다: {test_document}")
