#!/usr/bin/env python3
"""
Milvus 벡터 검색 실행 스크립트 (Prefect 없이)
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import logging
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

# Milvus
from pymilvus import Collection, connections, utility

# Azure OpenAI (임베딩용)
import openai

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Milvus Lite 설정 (파일 기반)
MILVUS_URI = os.getenv("MILVUS_URI", "./milvus_lite.db")  # 파일 기반 DB
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "document_vectors")

# Azure OpenAI 설정
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2023-12-01-preview")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

def get_azure_openai_embedding(text: str) -> List[float]:
    """Azure OpenAI를 사용하여 텍스트 임베딩을 생성합니다."""
    try:
        # Azure OpenAI 클라이언트 생성
        client = openai.AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_EMBEDDING_API_VERSION
        )
        
        response = client.embeddings.create(
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"❌ 임베딩 생성 실패: {str(e)}")
        raise

def _get_embedding_dim_from_schema(collection: Collection) -> int:
    """컬렉션 스키마에서 임베딩 차원을 추출합니다."""
    try:
        for field in collection.schema.fields:
            if field.name == "embedding":
                # PyMilvus 버전에 따라 dim 속성 또는 params 사용
                dim_value = getattr(field, "dim", None)
                if dim_value:
                    return int(dim_value)
                params = getattr(field, "params", None)
                if isinstance(params, dict) and "dim" in params:
                    return int(params["dim"])
    except Exception:
        pass
    # 파이프라인 기본값
    return 3072

def debug_and_prepare_collection() -> Collection:
    """컬렉션 로드, 인덱스/스키마 점검 및 준비 (Milvus Lite)."""
    connections.connect("default", uri=MILVUS_URI)
    collection = Collection(MILVUS_COLLECTION_NAME)

    # flush/load 보장
    try:
        collection.flush()
    except Exception:
        pass

    collection.load()

    # 인덱스/스키마 로깅
    try:
        index_types = []
        for ix in collection.indexes:
            ix_type = getattr(ix, "index_type", None) or str(ix)
            index_types.append(ix_type)
        logger.info(f"📋 인덱스: {index_types}")
    except Exception:
        logger.info("📋 인덱스 정보를 가져오지 못함")

    try:
        field_names = [f.name for f in collection.schema.fields]
        logger.info(f"🧬 스키마 필드: {field_names}")
    except Exception:
        logger.info("🧬 스키마 정보를 가져오지 못함")

    return collection

def validate_query_embedding_dim(collection: Collection, embedding: List[float]):
    """임베딩 차원 검증."""
    col_dim = _get_embedding_dim_from_schema(collection)
    if len(embedding) != col_dim:
        raise ValueError(f"임베딩 차원 불일치: query={len(embedding)}, collection={col_dim}")

def choose_search_params(collection: Collection) -> Dict[str, Any]:
    """인덱스 유형에 맞는 최적화된 검색 파라미터 선택."""
    index_type = None
    try:
        if collection.indexes:
            index_type = getattr(collection.indexes[0], "index_type", None)
    except Exception:
        pass

    # Milvus Lite는 FLAT, IVF_FLAT, AUTOINDEX만 지원
    if index_type and "IVF" in str(index_type).upper():
        return {"metric_type": "COSINE", "params": {"nprobe": 16}}
    # FLAT 또는 AUTOINDEX (기본값)
    return {"metric_type": "COSINE", "params": {}}

def check_milvus_connection():
    """Milvus Lite 연결 상태를 확인합니다."""
    try:
        connections.connect("default", uri=MILVUS_URI)
        logger.info(f"✅ Milvus Lite 연결 성공: {MILVUS_URI}")
        return True
    except Exception as e:
        logger.error(f"❌ Milvus Lite 연결 실패: {str(e)}")
        return False

def check_collection_exists():
    """컬렉션이 존재하는지 확인합니다."""
    try:
        if utility.has_collection(MILVUS_COLLECTION_NAME):
            collection = Collection(MILVUS_COLLECTION_NAME)
            collection.load()
            
            # 컬렉션 정보 출력
            logger.info(f"✅ 컬렉션 '{MILVUS_COLLECTION_NAME}' 존재")
            
            # 데이터 개수 확인
            num_entities = collection.num_entities
            logger.info(f"📊 컬렉션 내 데이터 개수: {num_entities}개")
            
            return True, num_entities
        else:
            logger.warning(f"⚠️ 컬렉션 '{MILVUS_COLLECTION_NAME}'이 존재하지 않습니다.")
            return False, 0
    except Exception as e:
        logger.error(f"❌ 컬렉션 확인 실패: {str(e)}")
        return False, 0

def search_combined_vectors(query: str, top_k: int = 5) -> Dict[str, Any]:
    """통합 벡터에서 검색"""
    logger.info(f"🔍 통합 벡터 검색: {query}")
    
    try:
        collection = debug_and_prepare_collection()

        # 쿼리 임베딩 및 차원 검증
        query_embedding = get_azure_openai_embedding(query)
        validate_query_embedding_dim(collection, query_embedding)

        # 인덱스에 맞는 검색 파라미터 선택
        search_params = choose_search_params(collection)

        t0 = time.time()
        results = collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["document_path", "page_number", "content_type", "content", 
                          "text_content", "image_description", "image_path"]
        )
        logger.info(f"⏱️ 검색 시간: {time.time()-t0:.3f}s")
        
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

def search_text_only(query: str, top_k: int = 5) -> Dict[str, Any]:
    """텍스트 콘텐츠만 검색"""
    logger.info(f"📝 텍스트 전용 검색: {query}")
    
    try:
        collection = debug_and_prepare_collection()

        query_embedding = get_azure_openai_embedding(query)
        validate_query_embedding_dim(collection, query_embedding)

        search_params = choose_search_params(collection)

        t0 = time.time()
        results = collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["document_path", "page_number", "content_type", "content", 
                          "text_content", "image_description", "image_path"]
        )
        logger.info(f"⏱️ 검색 시간: {time.time()-t0:.3f}s")
        
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

def search_image_only(query: str, top_k: int = 5) -> Dict[str, Any]:
    """이미지 설명만 검색"""
    logger.info(f"🖼️ 이미지 전용 검색: {query}")
    
    try:
        collection = debug_and_prepare_collection()

        query_embedding = get_azure_openai_embedding(query)
        validate_query_embedding_dim(collection, query_embedding)

        search_params = choose_search_params(collection)

        t0 = time.time()
        results = collection.search(
            [query_embedding],
            "embedding",
            search_params,
            limit=top_k,
            output_fields=["document_path", "page_number", "content_type", "content", 
                          "text_content", "image_description", "image_path"]
        )
        logger.info(f"⏱️ 검색 시간: {time.time()-t0:.3f}s")
        
        # 이미지 설명이 있는 결과만 필터링 (오류 메시지 제외)
        search_results = []
        for hits in results:
            for hit in hits:
                image_description = hit.entity.get("image_description", "")
                image_path = hit.entity.get("image_path", "")
                # 이미지 설명이 있고, 오류 메시지가 아닌 경우만
                if (image_description.strip() and image_path and 
                    not image_description.startswith("죄송합니다. 이미지를 인식할 수 없습니다")):
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

def print_search_results(results):
    """검색 결과를 출력합니다."""
    print(f"\n🔍 검색 쿼리: '{results['query']}'")
    print("=" * 80)
    
    # 각 검색 결과 출력
    for search_type, search_result in results["results"].items():
        if "error" in search_result:
            print(f"\n❌ {search_type.upper()} 검색 오류: {search_result['error']}")
            continue
            
        print(f"\n📊 {search_type.upper()} 검색 결과:")
        print("-" * 50)
        
        for i, result in enumerate(search_result["results"][:3], 1):
            print(f"{i}. 페이지 {result['page_number']} (점수: {result['score']:.3f})")
            print(f"   🔧 타입: {result.get('content_type', 'unknown')}")
            
            # 텍스트 내용 (있는 경우)
            if result.get('text_content') and result['text_content'].strip():
                text_content = result['text_content'].strip()
                if len(text_content) > 150:
                    text_preview = text_content[:150] + "..."
                else:
                    text_preview = text_content
                print(f"   📝 텍스트: {text_preview}")
            
            # 이미지 설명 (있는 경우)
            if result.get('image_description') and result['image_description'].strip():
                img_desc = result['image_description'].strip()
                # 오류 메시지 제외
                if not img_desc.startswith("죄송합니다. 이미지를 인식할 수 없습니다"):
                    if len(img_desc) > 150:
                        img_preview = img_desc[:150] + "..."
                    else:
                        img_preview = img_desc
                    print(f"   🖼️ 이미지: {img_preview}")
            
            # 이미지 경로 (있는 경우)
            if result.get('image_path') and result['image_path'].strip():
                image_filename = result['image_path'].split('/')[-1]
                print(f"   📁 이미지: {image_filename}")
            
            # 전체 내용 (combined 내용)
            if result.get('content') and result['content'].strip():
                content = result['content'].strip()
                if len(content) > 100:
                    content_preview = content[:100] + "..."
                else:
                    content_preview = content
                print(f"   📋 전체: {content_preview}")
            
            print()

def main():
    """메인 함수"""
    print("🚀 Milvus 벡터 검색 시스템 시작")
    print("=" * 80)
    
    # 1. Milvus 연결 확인
    if not check_milvus_connection():
        print("❌ Milvus 연결에 실패했습니다.")
        return
    
    # 2. 컬렉션 존재 확인
    collection_exists, num_entities = check_collection_exists()
    if not collection_exists:
        print("❌ 검색할 컬렉션이 존재하지 않습니다.")
        print("💡 먼저 run_document_pipeline.py를 실행하여 데이터를 구축해주세요.")
        return
    
    if num_entities == 0:
        print("⚠️ 컬렉션에 데이터가 없습니다.")
        print("💡 먼저 run_document_pipeline.py를 실행하여 데이터를 구축해주세요.")
        return
    
    # 3. 검색 쿼리 입력
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("\n🔍 검색할 내용을 입력하세요: ")
    
    if not query.strip():
        print("❌ 검색 쿼리를 입력해주세요.")
        return
    
    try:
        # 4. 검색 실행
        print(f"\n🔄 검색 실행 중...")
        
        search_results = {
            "query": query,
            "results": {}
        }
        
        # 통합 검색
        try:
            combined_results = search_combined_vectors(query, 5)
            search_results["results"]["combined"] = combined_results
        except Exception as e:
            search_results["results"]["combined"] = {"error": str(e)}
        
        # 텍스트 전용 검색
        try:
            text_results = search_text_only(query, 5)
            search_results["results"]["text_only"] = text_results
        except Exception as e:
            search_results["results"]["text_only"] = {"error": str(e)}
        
        # 이미지 전용 검색
        try:
            image_results = search_image_only(query, 5)
            search_results["results"]["image_only"] = image_results
        except Exception as e:
            search_results["results"]["image_only"] = {"error": str(e)}
        
        # 결과 출력
        print_search_results(search_results)
        print("\n✅ 검색 완료!")
        
    except Exception as e:
        print(f"\n❌ 검색 실행 실패: {str(e)}")

if __name__ == "__main__":
    main()