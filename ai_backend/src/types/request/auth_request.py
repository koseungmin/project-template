# _*_ coding: utf-8 _*_
"""Authentication request models."""
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class LoginInfo(BaseModel):
    """프론트엔드에서 전달되는 로그인 정보."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    user_id: str = Field(
        ...,
        validation_alias=AliasChoices("user_id", "userId", "id"),
        description="사용자 ID",
        min_length=1,
        max_length=100,
    )
    employee_id: str = Field(
        ...,
        validation_alias=AliasChoices("employee_id", "employeeId", "empId", "sabun"),
        description="사번",
        min_length=1,
        max_length=50,
    )
    name: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("name", "userName", "displayName"),
        description="사용자 이름",
        max_length=100,
    )
    department: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("department", "dept", "departmentName", "team"),
        description="부서명",
        max_length=100,
    )
    email: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("email", "mail", "emailAddress"),
        description="이메일",
        max_length=200,
    )

    @field_validator("user_id", "employee_id", mode="before")
    @classmethod
    def _validate_not_blank(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("값은 공백일 수 없습니다.")
            return stripped
        raise ValueError("문자열 값이 필요합니다.")

    @field_validator("name", "department", "email", mode="before")
    @classmethod
    def _strip_optional(cls, value: Optional[str]) -> Optional[str]:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class LoginRequest(BaseModel):
    """로그인 요청 모델."""

    model_config = ConfigDict(populate_by_name=True)

    login_info: LoginInfo = Field(
        ..., validation_alias=AliasChoices("login_info", "loginInfo"), description="로그인 정보"
    )


class TokenRefreshRequest(BaseModel):
    """기존 액세스 토큰을 기반으로 재발급 요청."""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(
        ...,
        validation_alias=AliasChoices("access_token", "accessToken", "token"),
        description="기존 액세스 토큰",
        min_length=10,
    )

