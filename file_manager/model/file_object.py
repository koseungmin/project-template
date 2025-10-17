from shared.core.database import Base
from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text, func


class FileObject(Base):
    """
    파일 정보를 저장하는 ORM 모델
    """

    __tablename__ = "file_obj"

    id = Column(
        String(32),
        primary_key=True,
        comment="파일 ID (UUID: '-' 없는 32자리, Cloud STORAGE 내 파일명)",
    )
    user_id = Column(
        BigInteger,
        nullable=False,
        comment="유저 ID (유저 개인 파일에 대한 isolation 필요시 필터링에 사용)",
    )
    is_private = Column(
        Boolean,
        default=False,
        comment="개인 파일 여부 (1: 개인 파일 (user_id 소유), 0: 회사 공유 파일 (comp_id 기준))",
    )
    comp_id = Column(
        String(20),
        nullable=False,
        comment="회사 구분 (루트 디렉토리 결정, ex: SKT, SKCC, COMMON, ...)",
    )
    category = Column(
        String(20), nullable=False, comment="문서 종류 (proposal, etc...)"
    )
    relative_path = Column(Text, nullable=True, comment="사용자가 지정한 상대 경로")
    absolute_path = Column(
        Text,
        nullable=False,
        comment="실제 저장된 파일의 절대 경로 (/SKT/data/bpsource/... 형식)",
    )
    storage_type = Column(
        String(20),
        nullable=True,
        comment="파일 저장 유형 (ncp, null)",
    )
    filename = Column(Text, nullable=False, comment="파일명")
    size = Column(BigInteger, nullable=True, comment="파일 크기 (바이트)")
    is_deleted = Column(Boolean, default=False, comment="삭제 여부")
    created_at = Column(
        DateTime, default=func.now(), nullable=False, comment="생성 일시"
    )
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="수정 일시"
    )
    deleted_at = Column(DateTime, nullable=True, comment="삭제 일시")
    created_by = Column(BigInteger, nullable=True, comment="생성자 ID")
    updated_by = Column(BigInteger, nullable=True, comment="수정자 ID")
    deleted_by = Column(BigInteger, nullable=True, comment="삭제자 ID")
