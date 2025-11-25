from enum import Enum, unique

__all__ = [
    "ResponseCode"
]


@unique
class ResponseCode(Enum):
    """응답 코드 정의 (암복호화 서비스용)"""

    SUCCESS = (1, "성공")
    FAIL = (-1, "실패")
    UNDEFINED_ERROR = (-2, "정의되지 않은 오류입니다.")
    
    # 암복호화 관련 에러 코드 (-2000 ~ -2099)
    CRYPTO_ENCRYPT_ERROR = (-2001, "암호화 중 오류가 발생했습니다.")
    CRYPTO_DECRYPT_ERROR = (-2002, "복호화 중 오류가 발생했습니다.")
    CRYPTO_KEY_ERROR = (-2003, "암호화 키 오류가 발생했습니다.")
    CRYPTO_INVALID_DATA = (-2004, "유효하지 않은 암호화 데이터입니다.")
    CRYPTO_ALGORITHM_NOT_SUPPORTED = (-2005, "지원하지 않는 암호화 알고리즘입니다.")
    
    # VALIDATION_ERROR = (-1600 ~ -1699)
    VALIDATION_ERROR = (-1601, "입력 데이터 검증 오류가 발생했습니다.")
    REQUIRED_FIELD_MISSING = (-1602, "필수 필드가 누락되었습니다.")
    INVALID_DATA_FORMAT = (-1603, "잘못된 데이터 형식입니다.")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

