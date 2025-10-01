# _*_ coding: utf-8 _*_
"""Group Service for handling group operations."""
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from ai_backend.database.crud.group_crud import GroupCRUD
from ai_backend.types.response.exceptions import HandledException
from ai_backend.types.response.response_code import ResponseCode
from ai_backend.utils.uuid_gen import gen
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GroupService:
    """그룹 서비스를 관리하는 클래스"""
    
    def __init__(self, db: Session):
        if db is None:
            raise ValueError("Database session is required")
        
        self.db = db
        self.group_crud = GroupCRUD(db)
        # GroupMemberCRUD는 GroupMember 모델이 삭제되어 제거됨
    
    def create_group(self, group_name: str, owner_id: str, description: str = None, 
                    max_members: int = None):
        """그룹 생성"""
        try:
            # 그룹명 중복 체크
            if self.group_crud.check_group_name_exists(group_name):
                raise HandledException(ResponseCode.GROUP_NAME_ALREADY_EXISTS)
            
            # 그룹 생성
            group_id = gen()
            group = self.group_crud.create_group(
                group_id=group_id,
                group_name=group_name,
                description=description,
                owner_id=owner_id,
                max_members=max_members
            )
            
            return group
        except HandledException:
            raise
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def get_group(self, group_id: str):
        """그룹 조회"""
        try:
            group = self.group_crud.get_group(group_id)
            if not group:
                raise HandledException(ResponseCode.GROUP_NOT_FOUND)
            
            return group
        except HandledException:
            raise
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def get_groups(self, skip: int = 0, limit: int = 100, search: str = None):
        """그룹 목록 조회"""
        try:
            groups, total_count = self.group_crud.get_groups(skip, limit, search)
            return groups, total_count
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def update_group(self, group_id: str, group_name: str = None, 
                    description: str = None, max_members: int = None):
        """그룹 정보 수정"""
        try:
            # 그룹 존재 확인
            group = self.group_crud.get_group(group_id)
            if not group:
                raise HandledException(ResponseCode.GROUP_NOT_FOUND)
            
            # 그룹명 중복 체크 (변경하는 경우)
            if group_name and group_name != group.group_name:
                if self.group_crud.check_group_name_exists(group_name):
                    raise HandledException(ResponseCode.GROUP_NAME_ALREADY_EXISTS)
            
            # 그룹 정보 수정
            updated_group = self.group_crud.update_group(
                group_id=group_id,
                group_name=group_name,
                description=description,
                max_members=max_members
            )
            
            return updated_group
        except HandledException:
            raise
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def delete_group(self, group_id: str):
        """그룹 삭제"""
        try:
            # 그룹 존재 확인
            group = self.group_crud.get_group(group_id)
            if not group:
                raise HandledException(ResponseCode.GROUP_NOT_FOUND)
            
            # 그룹 삭제 (soft delete)
            success = self.group_crud.delete_group(group_id)
            
            return success
        except HandledException:
            raise
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def get_group_with_members(self, group_id: str):
        """그룹 정보와 멤버 목록 조회"""
        try:
            # 그룹 정보 조회
            group = self.group_crud.get_group(group_id)
            if not group:
                raise HandledException(ResponseCode.GROUP_NOT_FOUND)
            
            # 멤버 목록 조회 - GroupMember 모델이 삭제되어 빈 리스트 반환
            members = []
            
            return group, members
        except HandledException:
            raise
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def check_group_exists(self, group_id: str) -> bool:
        """그룹 존재 여부 확인"""
        try:
            return self.group_crud.check_group_exists(group_id)
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def get_group_count(self) -> int:
        """전체 그룹 수 조회"""
        try:
            return self.group_crud.get_group_count()
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
    
    def search_groups(self, search_term: str, skip: int = 0, limit: int = 100):
        """그룹 검색"""
        try:
            groups, total_count = self.group_crud.search_groups(search_term, skip, limit)
            return groups, total_count
        except Exception as e:
            raise HandledException(ResponseCode.UNDEFINED_ERROR, e=e)
