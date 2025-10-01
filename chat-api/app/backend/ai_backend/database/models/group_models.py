# _*_ coding: utf-8 _*_
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql.expression import func, true, false
from ai_backend.database.base import Base

__all__ = [
    "Group",
]


class Group(Base):
    __tablename__ = "GROUPS"
    
    group_id = Column('GROUP_ID', String(50), primary_key=True)  # 그룹 ID
    group_name = Column('GROUP_NAME', String(100), nullable=False)  # 그룹명
    description = Column('DESCRIPTION', Text, nullable=True)  # 그룹 설명
    
    # 그룹 권한
    sit_auth = Column('SIT_AUTH', JSON, default=[])  # sitAuth 권한 리스트
    nct_auth = Column('NCT_AUTH', String(1), default='N')  # nct 권한 (Y/N)
    service_permissions = Column('SERVICE_PERMISSIONS', JSON, default=[])  # 서비스 권한
    
    create_dt = Column('CREATE_DT', DateTime, nullable=False, server_default=func.now())  # 생성일시
    update_dt = Column('UPDATE_DT', DateTime, nullable=True)  # 수정일시
    is_active = Column('IS_ACTIVE', Boolean, nullable=False, server_default=true())  # 활성 상태
    is_deleted = Column('IS_DELETED', Boolean, nullable=False, server_default=false())  # 삭제 여부
