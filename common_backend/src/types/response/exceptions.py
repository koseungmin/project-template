from typing import Optional
import logging

from fastapi.exceptions import HTTPException

from .response_code import ResponseCode

logger = logging.getLogger(__name__)


__all__ = [
    "HandledException",
    "UnHandledException",
]


class HandledException(HTTPException):
    """Application-managed Exception, which is an exception wrapper.
    
    This Exception is designed to handle the exceptions raised from 
    application API is responsing. When it is raised, it is catched by
    exception handlers and `ErrorResponse` is responsed.

    Parameters
    ----------
    resp_code: ResponseCode
        An application-managed error case. it has its own `code` and `msg` to logging.

    e: Exception
        An system raised exception to wrap.

    code: int (default: None)
        It needed if `resp_code` is not given.

    msg: str (default: None)
        It needed if `resp_code` is not given.

    http_status_code: int (default: 400)
        HTTP status code for the response. Defaults to 400 (Bad Request).
    """

    # errorCode
    code: int
    # errorMessage
    message: str
    # HTTP status code
    http_status_code: int

    def __init__(self, resp_code: ResponseCode, e: Exception = None, code: int = None, msg: str = None, http_status_code: int = 400):
        # HTTP 상태 코드 매핑
        status_code = self._get_http_status_code(resp_code, http_status_code)
        super(HTTPException, self).__init__(status_code=status_code, detail=resp_code.message)
        
        self.code = resp_code.code
        self.message = resp_code.message
        self.http_status_code = status_code

        delimeter = ": "
        if msg is not None:
            self.message = delimeter.join([
                self.message,
                msg,
            ])
    
    def _get_http_status_code(self, resp_code: ResponseCode, default_status: int) -> int:
        """ResponseCode에 따라 적절한 HTTP 상태 코드를 반환"""
        # 4xx 클라이언트 에러
        if resp_code.code in [-1601, -1602, -1603, -2004, -2005]:  # 검증, 암복호화 데이터 에러
            return 400
        # 5xx 서버 에러  
        elif resp_code.code in [-2001, -2002, -2003]:  # 암복호화 서버 에러
            return 500
        else:
            return default_status
            
    @property
    def logMessage(self) -> str:
        return "\n".join([
            "=" * 50,
            f"CODE: {self.code}",
            f"MSG: {self.message}",
        ])


class UnHandledException(HandledException):
    def __init__(self, e: Exception = None, code: int = None, msg: str = None):
        super().__init__(ResponseCode.UNDEFINED_ERROR, e=e, code=code, msg=msg)

