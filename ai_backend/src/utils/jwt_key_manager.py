# _*_ coding: utf-8 _*_
"""JWT 퍼블릭 키 관리 클래스 (RS256 지원)"""
import logging
from typing import Dict, Optional

import httpx
import jwt
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class JWTKeyManager:
    """JWT 퍼블릭 키 관리 클래스
    
    RS256 알고리즘을 사용할 때 kid(Key ID) 기반으로 퍼블릭 키를 관리합니다.
    - 키 캐싱: 메모리 캐시에 저장하여 성능 최적화
    - 키 갱신: 캐시에 없으면 자동으로 갱신 시도
    """
    
    def __init__(self, jwks_uri: Optional[str] = None):
        """
        Args:
            jwks_uri: JWKS (JSON Web Key Set) 엔드포인트 URL
                     예: https://auth.example.com/.well-known/jwks.json
        """
        self._cache: Dict[str, str] = {}  # kid -> PEM 형식 퍼블릭 키
        self.jwks_uri = jwks_uri
    
    async def get_public_key(self, kid: str) -> str:
        """
        캐시에 kid가 있으면 PEM 반환
        없으면 refresh_key로 갱신 후 다시 캐시에서 찾아 반환
        캐시에도 없으면 400 오류
        
        Args:
            kid: JWT 헤더의 Key ID
            
        Returns:
            str: PEM 형식의 퍼블릭 키
            
        Raises:
            HTTPException: kid가 유효하지 않거나 키를 찾을 수 없는 경우
        """
        # 캐시에 있으면 바로 반환
        if kid in self._cache:
            logger.debug(f"키 캐시에서 조회: kid={kid}")
            return self._cache[kid]
        
        # 캐시에 없으면 키 갱신 시도
        logger.info(f"키 캐시에 없음, 갱신 시도: kid={kid}")
        await self._refresh_key(kid)
        
        # 갱신 후 캐시에서 확인
        if kid in self._cache:
            logger.info(f"키 갱신 후 캐시에서 조회 성공: kid={kid}")
            return self._cache[kid]
        
        # 여전히 없으면 잘못된 kid
        logger.error(f"유효하지 않은 kid: {kid}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid kid: {kid}"
        )
    
    async def _refresh_key(self, kid: str) -> None:
        """
        JWKS 엔드포인트에서 키를 가져와서 캐시에 저장
        
        Args:
            kid: 조회할 Key ID
        """
        if not self.jwks_uri:
            logger.warning("JWKS URI가 설정되지 않았습니다.")
            return
        
        try:
            # JWKS 엔드포인트에서 키 세트 조회
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_uri, timeout=5.0)
                response.raise_for_status()
                jwks = response.json()
            
            # 키 세트에서 해당 kid 찾기
            for key_data in jwks.get("keys", []):
                if key_data.get("kid") == kid:
                    # JWK를 PEM 형식으로 변환
                    public_key = self._jwk_to_pem(key_data)
                    self._cache[kid] = public_key
                    logger.info(f"키 갱신 성공: kid={kid}")
                    return
            
            logger.warning(f"JWKS에서 kid를 찾을 수 없음: {kid}")
            
        except httpx.RequestError as e:
            logger.error(f"JWKS 엔드포인트 조회 실패: {e}")
        except Exception as e:
            logger.error(f"키 갱신 중 오류 발생: {e}")
    
    def _jwk_to_pem(self, jwk: dict) -> str:
        """
        JWK (JSON Web Key) 형식을 PEM 형식으로 변환
        
        Args:
            jwk: JWK 딕셔너리
            
        Returns:
            str: PEM 형식의 퍼블릭 키
        """
        try:
            import base64

            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # JWK에서 필요한 파라미터 추출
            n = base64.urlsafe_b64decode(jwk.get("n", "") + "==")
            e = base64.urlsafe_b64decode(jwk.get("e", "") + "==")
            
            # Big Endian으로 변환
            n_int = int.from_bytes(n, byteorder='big')
            e_int = int.from_bytes(e, byteorder='big')
            
            # RSA 공개 키 구성
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            
            # PEM 형식으로 직렬화
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem.decode('utf-8')
            
        except Exception as e:
            logger.error(f"JWK to PEM 변환 실패: {e}")
            raise ValueError(f"Invalid JWK format: {e}")
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        logger.info("JWT 키 캐시 초기화됨")
    
    def get_cache_size(self) -> int:
        """현재 캐시된 키 개수 반환"""
        return len(self._cache)

