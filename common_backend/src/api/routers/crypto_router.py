# _*_ coding: utf-8 _*_
"""암복호화 API 엔드포인트."""
import logging

from fastapi import APIRouter, Depends
from src.api.services.crypto_service import CryptoService
from src.core.dependencies import get_current_user_id
from src.types.request.crypto_request import EncryptRequest, DecryptRequest
from src.types.response.crypto_response import EncryptResponse, DecryptResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["crypto"])


def get_crypto_service() -> CryptoService:
    """암복호화 서비스 의존성 주입"""
    return CryptoService()


@router.post("/crypto/encrypt", response_model=EncryptResponse)
def encrypt(
    request: EncryptRequest,
    crypto_service: CryptoService = Depends(get_crypto_service),
    # user_id: str = Depends(get_current_user_id),  # JWT_ENABLED=true인 경우 주석 해제
) -> EncryptResponse:
    """
    데이터를 암호화합니다.
    
    Args:
        request: 암호화 요청 데이터
        crypto_service: 암복호화 서비스
        user_id: 사용자 ID (인증이 필요한 경우)
    
    Returns:
        EncryptResponse: 암호화된 데이터와 알고리즘 정보
    """
    logger.info("암호화 요청 수신")
    result = crypto_service.encrypt(
        data=request.data,
        algorithm=request.algorithm
    )
    return EncryptResponse(**result)


@router.post("/crypto/decrypt", response_model=DecryptResponse)
def decrypt(
    request: DecryptRequest,
    crypto_service: CryptoService = Depends(get_crypto_service),
    # user_id: str = Depends(get_current_user_id),  # JWT_ENABLED=true인 경우 주석 해제
) -> DecryptResponse:
    """
    암호화된 데이터를 복호화합니다.
    
    Args:
        request: 복호화 요청 데이터
        crypto_service: 암복호화 서비스
        user_id: 사용자 ID (인증이 필요한 경우)
    
    Returns:
        DecryptResponse: 복호화된 데이터와 알고리즘 정보
    """
    logger.info("복호화 요청 수신")
    result = crypto_service.decrypt(
        encrypted_data=request.encrypted_data,
        algorithm=request.algorithm
    )
    return DecryptResponse(**result)

