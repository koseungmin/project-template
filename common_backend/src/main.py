# -*- coding: utf-8 -*-
import glob
import logging
import logging.config
import os
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.core.global_exception_handlers import set_global_exception_handlers
from src.middleware.auth_middleware import JWTAuthMiddleware


def cleanup_old_logs():
    """
    오래된 로그 파일을 삭제하는 함수
    
    ==========================================
    기능:
    - LOG_RETENTION_DAYS 설정에 따라 오래된 로그 파일 자동 삭제
    - TimedRotatingFileHandler로 생성된 로그 파일들을 날짜 기반으로 정리
    - 파일명 형식: app.log.2025-09-15 (날짜별 로테이션)
    """
    # 파일 로깅이 비활성화된 경우 실행하지 않음
    if not settings.log_to_file:
        logger.debug("파일 로깅이 비활성화되어 로그 정리를 건너뜁니다")
        return
    
    try:
        # 설정값 가져오기
        log_dir = settings.log_dir
        log_file = settings.log_file
        retention_days = settings.log_retention_days
        
        logger.debug("로그 정리 시작 - 디렉토리: {}, 보관 기간: {}일".format(log_dir, retention_days))
        
        # 로그 파일 패턴 생성 (app.log.2025-09-15 형태)
        log_pattern = os.path.join(log_dir, "{log_file}.*".format(log_file=log_file))
        log_files = glob.glob(log_pattern)
        
        if not log_files:
            logger.debug("정리할 로그 파일이 없습니다")
            return
        
        # 현재 날짜에서 보관 기간을 뺀 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        logger.debug("삭제 기준 날짜: {}".format(cutoff_date.strftime('%Y-%m-%d')))
        
        deleted_count = 0
        skipped_count = 0
        
        for log_file_path in log_files:
            try:
                # 파일명에서 날짜 추출 (app.log.2025-09-15 -> 2025-09-15)
                filename = os.path.basename(log_file_path)
                
                # 현재 로그 파일 (app.log)은 건너뛰기
                if filename == log_file:
                    logger.debug("현재 로그 파일은 보호됩니다: {}".format(filename))
                    continue
                
                # 파일명에 점이 있는 경우 날짜 부분 추출
                if '.' in filename:
                    date_part = filename.split('.')[-1]
                    try:
                        # 날짜 파싱 (YYYY-MM-DD 형식)
                        file_date = datetime.strptime(date_part, '%Y-%m-%d')
                        
                        # 보관 기간이 지난 파일 삭제
                        if file_date < cutoff_date:
                            os.remove(log_file_path)
                            deleted_count += 1
                            logger.debug("오래된 로그 파일 삭제: {} (날짜: {})".format(log_file_path, date_part))
                        else:
                            logger.debug("보관 기간 내 파일 유지: {} (날짜: {})".format(log_file_path, date_part))
                    except ValueError:
                        # 날짜 형식이 맞지 않는 파일은 건너뛰기
                        skipped_count += 1
                        logger.debug("날짜 형식이 맞지 않아 건너뛰기: {}".format(filename))
                        continue
                else:
                    # 파일명에 점이 없는 경우도 건너뛰기
                    skipped_count += 1
                    logger.debug("예상하지 못한 파일명 형식으로 건너뛰기: {}".format(filename))
                    
            except Exception as e:
                # 개별 파일 삭제 실패 시 경고 로그만 출력하고 계속 진행
                logger.warning("로그 파일 삭제 중 오류: {}, 오류: {}".format(log_file_path, e))
        
        # 정리 결과 로그 출력
        if deleted_count > 0:
            logger.info("오래된 로그 파일 {}개 삭제 완료 (보관 기간: {}일)".format(deleted_count, retention_days))
        else:
            logger.debug("삭제할 오래된 로그 파일이 없습니다")
            
        if skipped_count > 0:
            logger.debug("날짜 형식이 맞지 않아 건너뛴 파일: {}개".format(skipped_count))
            
    except Exception as e:
        # 전체 프로세스 실패 시에도 애플리케이션 중단 없이 에러 로그만 출력
        logger.error("로그 정리 중 오류 발생: {}".format(e))
        logger.error("로그 정리 실패로 인해 디스크 공간이 부족할 수 있습니다. 수동으로 확인해주세요.")


def setup_logging():
    """ConfigMap 환경변수 기반 동적 로깅 설정"""
    
    # 환경변수에서 로그 레벨 가져오기
    app_log_level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    server_log_level = getattr(logging, settings.server_log_level.upper(), logging.INFO)
    
    # 로그 설정 (Pydantic Settings 사용)
    log_to_file = settings.log_to_file
    log_dir = settings.log_dir
    log_file = settings.log_file
    log_path = os.path.join(log_dir, log_file)
    
    # 로그 디렉토리 생성 (파일 로깅이 활성화된 경우만)
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
    
    # 핸들러 설정
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": app_log_level,
            "formatter": "colored",
            "stream": "ext://sys.stdout"
        }
    }
    
    # 파일 로깅이 활성화된 경우 파일 핸들러 추가
    if log_to_file:
        # 로그 로테이션 설정 가져오기
        log_rotation = settings.log_rotation
        log_retention_days = settings.log_retention_days
        
        if log_rotation == "size":
            # 크기 기반 로테이션 (RotatingFileHandler)
            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": app_log_level,
                "formatter": "default",
                "filename": log_path,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5       # 최대 5개 파일 보관
            }
        else:
            # 시간 기반 로테이션 (TimedRotatingFileHandler)
            when_map = {
                "daily": "midnight",   # 매일 자정 (00:00)
                "weekly": "W0",        # 매주 월요일 (W0 = 월요일)
                "monthly": "M1"        # 매월 1일 (M1 = 매월 1일)
            }
            when = when_map.get(log_rotation, "midnight")
            
            handlers["file"] = {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": app_log_level,
                "formatter": "default",
                "filename": log_path,
                "when": when,                    # 로테이션 시점
                "interval": 1,                   # 간격 (1일/1주/1월)
                "backupCount": log_retention_days,  # 보관 기간
                "encoding": "utf-8"              # UTF-8 인코딩
            }
    
    # 동적 로깅 설정
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[%(asctime)s.%(msecs)03d] %(levelname)s [%(thread)d] - %(message)s",
            },
            "colored": {
                "()": "coloredlogs.ColoredFormatter",
                "format": "%(asctime)s.%(msecs)03d %(levelname)-5s %(process)5d --- [%(funcName)20s] %(name)-40s : %(message)s"
            }
        },
        "handlers": handlers,
        "loggers": {
            "": {  # root logger (앱 로그)
                "level": app_log_level,
                "handlers": ["console"] + (["file"] if log_to_file else [])
            },
            "uvicorn": {  # uvicorn 서버 로그
                "level": server_log_level,
                "handlers": ["console"] + (["file"] if log_to_file else []),
                "propagate": False
            },
            "uvicorn.access": {  # uvicorn access 로그
                "level": server_log_level,
                "handlers": ["console"] + (["file"] if log_to_file else []),
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # 로깅 설정 완료 로그
    logger = logging.getLogger(__name__)
    logger.info("로깅 설정 완료 - 앱 로그 레벨: {}, 서버 로그 레벨: {}".format(settings.app_log_level.upper(), settings.server_log_level.upper()))


# 동적 로깅 설정 적용
setup_logging()
logger = logging.getLogger(__name__)

# 애플리케이션 시작 시 오래된 로그 파일 정리
cleanup_old_logs()


def create_app():
    logger.info("Creating FastAPI application...")
    
    # 디버그 모드 설정
    debug_mode = settings.app_debug
    logger.info("애플리케이션 디버그 모드: {}".format('활성화' if debug_mode else '비활성화'))
    
    app = FastAPI(
        title="Common Backend API",
        description="암복호화 공통 서비스",
        version="1.0.0",
        debug=debug_mode,
        root_path=settings.app_root_path
    )
    
    logger.info("FastAPI application created successfully")
    
    # Global exception handlers 등록
    app = set_global_exception_handlers(app)
    logger.info("Global exception handlers registered successfully")
    
    # JWT 인증 미들웨어 등록 (클러스터 내부 서비스는 기본 비활성화)
    # 보안은 Kubernetes 네트워크 정책과 CoreDNS로 관리
    if settings.jwt_enabled:
        app.add_middleware(JWTAuthMiddleware)
        logger.info("JWT authentication middleware registered successfully")
    else:
        logger.info("JWT authentication is disabled (클러스터 내부 전용 서비스)")
  
    # API 버전 경로 설정
    api_prefix = "/v1"
    
    # 암복호화 라우터 추가
    from src.api.routers.crypto_router import router as crypto_router
    app.include_router(crypto_router, prefix=api_prefix)
    
    # CORS 설정
    origins = settings.get_cors_origins()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "common-backend"}
    
    # 디버그 모드에서만 추가 엔드포인트 제공
    if debug_mode:
        @app.get("/debug/info")
        async def debug_info():
            """디버그 모드에서만 사용 가능한 시스템 정보"""
            import platform
            import sys
            return {
                "debug_mode": True,
                "python_version": sys.version,
                "platform": platform.platform(),
                "app_version": settings.app_version,
                "log_level": settings.app_log_level,
                "server_log_level": settings.server_log_level,
                "crypto_algorithm": settings.crypto_algorithm,
            }
        
        @app.get("/debug/logs")
        async def debug_logs():
            """디버그 모드에서만 사용 가능한 로그 레벨 테스트"""
            logger.debug("DEBUG 로그 테스트")
            logger.info("INFO 로그 테스트")
            logger.warning("WARNING 로그 테스트")
            logger.error("ERROR 로그 테스트")
            return {"message": "로그 테스트 완료 - 콘솔을 확인하세요"}
        
        @app.post("/debug/cleanup-logs")
        async def debug_cleanup_logs():
            """
            디버그 모드에서만 사용 가능한 로그 정리 엔드포인트
            """
            logger.info("수동 로그 정리 요청됨 (디버그 엔드포인트)")
            cleanup_old_logs()
            return {"message": "로그 정리 완료 - 콘솔을 확인하세요"}
    
    return app

app = create_app()

