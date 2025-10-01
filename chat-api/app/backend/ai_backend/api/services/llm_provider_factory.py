# _*_ coding: utf-8 _*_
"""LLM Provider Factory for supporting multiple LLM providers."""
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp
from ai_backend.types.response.exceptions import HandledException
from ai_backend.types.response.response_code import ResponseCode
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class BaseLLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, model, max_tokens=1000, temperature=0.7):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    async def create_completion(self, messages, stream=False):
        """Create completion from LLM provider"""
        raise NotImplementedError("Subclasses must implement create_completion")
    
    async def create_title_completion(self, message):
        """Create title completion from LLM provider"""
        raise NotImplementedError("Subclasses must implement create_title_completion")
    
    def process_stream_chunk(self, chunk):
        """Process streaming chunk and extract content"""
        raise NotImplementedError("Subclasses must implement process_stream_chunk")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: str, model: str, max_tokens: int = 1000, temperature: float = 0.7):
        super().__init__(model, max_tokens, temperature)
        
        if not api_key:
            raise HandledException(ResponseCode.LLM_CONFIG_ERROR, msg="OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI provider initialized with model: " + str(model))
    
    async def create_completion(self, messages: list, stream: bool = False):
        """Create completion using OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=stream
            )
            return response
        except Exception as e:
            logger.error("OpenAI API error: " + str(e))
            raise HandledException(ResponseCode.CHAT_AI_RESPONSE_ERROR, e=e)
    
    async def create_title_completion(self, message: str):
        """Create title completion using OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "다음 질문을 기반으로 간단하고 명확한 채팅방 제목을 생성해주세요. 20자 이내로 만들어주세요."
                    },
                    {
                        "role": "user",
                        "content": "질문: " + str(message)
                    }
                ],
                max_tokens=50,
                temperature=self.temperature
            )
            return response
        except Exception as e:
            logger.error("OpenAI title generation error: " + str(e))
            raise HandledException(ResponseCode.CHAT_AI_RESPONSE_ERROR, e=e)
    
    def process_stream_chunk(self, chunk) -> str:
        """Process OpenAI streaming chunk and extract content"""
        if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
            return chunk.choices[0].delta.content
        return None


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider implementation"""
    
    def __init__(self, api_key: str, endpoint: str, deployment_name: str, 
                 api_version: str, max_tokens: int = 1000, temperature: float = 0.7):
        super().__init__(deployment_name, max_tokens, temperature)
        
        if not api_key:
            raise HandledException(ResponseCode.LLM_CONFIG_ERROR, msg="Azure OpenAI API key is required")
        if not endpoint:
            raise HandledException(ResponseCode.LLM_CONFIG_ERROR, msg="Azure OpenAI endpoint is required")
        if not deployment_name:
            raise HandledException(ResponseCode.LLM_CONFIG_ERROR, msg="Azure OpenAI deployment name is required")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=endpoint.rstrip('/') + "/openai/deployments/" + deployment_name,
            default_query={"api-version": api_version}
        )
        logger.info("Azure OpenAI provider initialized with deployment: " + str(deployment_name))
    
    async def create_completion(self, messages: list, stream: bool = False):
        """Create completion using Azure OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,  # deployment name
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=stream
            )
            return response
        except Exception as e:
            logger.error("Azure OpenAI API error: " + str(e))
            raise HandledException(ResponseCode.CHAT_AI_RESPONSE_ERROR, e=e)
    
    async def create_title_completion(self, message: str):
        """Create title completion using Azure OpenAI API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,  # deployment name
                messages=[
                    {
                        "role": "system",
                        "content": "다음 질문을 기반으로 간단하고 명확한 채팅방 제목을 생성해주세요. 20자 이내로 만들어주세요."
                    },
                    {
                        "role": "user",
                        "content": "질문: " + str(message)
                    }
                ],
                max_tokens=50,
                temperature=self.temperature
            )
            return response
        except Exception as e:
            logger.error("Azure OpenAI title generation error: " + str(e))
            raise HandledException(ResponseCode.CHAT_AI_RESPONSE_ERROR, e=e)
    
    def process_stream_chunk(self, chunk) -> str:
        """Process Azure OpenAI streaming chunk and extract content"""
        # Azure OpenAI의 첫 번째 청크는 빈 choices 배열을 가질 수 있음
        if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
            return chunk.choices[0].delta.content
        return None


class ExternalAPIProvider(BaseLLMProvider):
    """External API Agent provider implementation"""
    
    def __init__(self, api_url: str, authorization_header: str, 
                 max_tokens: int = 1000, temperature: float = 0.7):
        super().__init__("external_api", max_tokens, temperature)
        
        if not api_url:
            raise HandledException(ResponseCode.LLM_CONFIG_ERROR, msg="External API URL is required")
        if not authorization_header:
            raise HandledException(ResponseCode.LLM_CONFIG_ERROR, msg="Authorization header is required")
        
        self.api_url = api_url.rstrip('/')
        self.authorization_header = authorization_header
        logger.info("External API provider initialized with URL: " + str(self.api_url))
    
    async def create_completion(self, messages: list, stream: bool = False):
        """Create completion using External API"""
        try:
            # OpenAI 형식의 messages를 External API 형식으로 변환
            formatted_messages = []
            for msg in messages:
                formatted_msg = {
                    "content": msg["content"],
                    "type": "human" if msg["role"] == "user" else "ai"
                }
                formatted_messages.append(formatted_msg)
            
            # External API 요청 바디 구성
            request_body = {
                "config": {},
                "input": {
                    "messages": formatted_messages,
                    "additional_kwargs": {}
                },
                "kwargs": {}
            }
            
            headers = {
                "Authorization": self.authorization_header,
                "Content-Type": "application/json"
            }
            
            if stream:
                return await self._create_streaming_completion(request_body, headers)
            else:
                return await self._create_non_streaming_completion(request_body, headers)
                
        except Exception as e:
            logger.error("External API error: " + str(e))
            raise HandledException(ResponseCode.CHAT_AI_RESPONSE_ERROR, e=e)
    
    async def _create_streaming_completion(self, request_body: dict, headers: dict):
        """Create streaming completion"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url + "/stream",
                json=request_body,
                headers=headers
            ) as response:
                if response.status != 200:
                    raise HandledException(
                        ResponseCode.CHAT_AI_RESPONSE_ERROR, 
                        msg="External API returned status " + str(response.status)
                    )
                
                # 스트리밍 응답을 청크별로 처리
                async for line in response.content:
                    if line:
                        try:
                            chunk_data = json.loads(line.decode('utf-8'))
                            yield self._create_chunk_object(chunk_data)
                        except json.JSONDecodeError:
                            continue
    
    async def _create_non_streaming_completion(self, request_body: dict, headers: dict):
        """Create non-streaming completion"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                json=request_body,
                headers=headers
            ) as response:
                if response.status != 200:
                    raise HandledException(
                        ResponseCode.CHAT_AI_RESPONSE_ERROR, 
                        msg="External API returned status " + str(response.status)
                    )
                
                response_data = await response.json()
                return self._create_completion_object(response_data)
    
    def _create_chunk_object(self, chunk_data: dict):
        """External API 응답을 OpenAI 스타일 청크 객체로 변환"""
        class ChunkObject:
            def __init__(self, content):
                self.choices = [type('Choice', (), {
                    'delta': type('Delta', (), {'content': content})()
                })()]
        
        # External API 응답에서 content 추출 (실제 응답 구조에 따라 조정 필요)
        content = chunk_data.get('content', '') or chunk_data.get('text', '')
        return ChunkObject(content)
    
    def _create_completion_object(self, response_data: dict):
        """External API 응답을 OpenAI 스타일 completion 객체로 변환"""
        class CompletionObject:
            def __init__(self, content):
                self.choices = [type('Choice', (), {
                    'message': type('Message', (), {'content': content})()
                })()]
        
        # External API 응답에서 content 추출 (실제 응답 구조에 따라 조정 필요)
        content = response_data.get('content', '') or response_data.get('text', '') or response_data.get('response', '')
        return CompletionObject(content)
    
    async def create_title_completion(self, message: str):
        """Create title completion using External API"""
        try:
            # 제목 생성을 위한 간단한 메시지 구성
            messages = [
                {
                    "content": "다음 질문을 기반으로 간단하고 명확한 채팅방 제목을 생성해주세요. 20자 이내로 만들어주세요.",
                    "type": "human"
                },
                {
                    "content": "질문: " + str(message),
                    "type": "human"
                }
            ]
            
            request_body = {
                "config": {},
                "input": {
                    "messages": messages,
                    "additional_kwargs": {}
                },
                "kwargs": {}
            }
            
            headers = {
                "Authorization": self.authorization_header,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=request_body,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        raise HandledException(
                            ResponseCode.CHAT_AI_RESPONSE_ERROR, 
                            msg="External API title generation returned status " + str(response.status)
                        )
                    
                    response_data = await response.json()
                    return self._create_completion_object(response_data)
                    
        except Exception as e:
            logger.error("External API title generation error: " + str(e))
            raise HandledException(ResponseCode.CHAT_AI_RESPONSE_ERROR, e=e)
    
    def process_stream_chunk(self, chunk) -> str:
        """Process External API streaming chunk and extract content"""
        if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                return delta.content
        return None


class LLMProviderFactory:
    """Factory class for creating LLM providers"""
    
    @staticmethod
    def create_provider(provider_type: str = None) -> BaseLLMProvider:
        """Create LLM provider based on configuration"""
        
        # 환경 변수에서 제공자 타입 가져오기
        if not provider_type:
            provider_type = os.getenv("LLM_PROVIDER", "openai").lower()
        
        logger.info("Creating LLM provider: " + str(provider_type))
        
        if provider_type == "openai":
            return LLMProviderFactory._create_openai_provider()
        elif provider_type == "azure_openai":
            return LLMProviderFactory._create_azure_openai_provider()
        elif provider_type == "external_api":
            return LLMProviderFactory._create_external_api_provider()
        else:
            raise HandledException(
                ResponseCode.LLM_CONFIG_ERROR, 
                msg="Unsupported LLM provider: " + str(provider_type) + ". Supported providers: openai, azure_openai, external_api"
            )
    
    @staticmethod
    def _create_openai_provider() -> OpenAIProvider:
        """Create OpenAI provider"""
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        
        return OpenAIProvider(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    @staticmethod
    def _create_azure_openai_provider() -> AzureOpenAIProvider:
        """Create Azure OpenAI provider"""
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "1000"))
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.7"))
        
        return AzureOpenAIProvider(
            api_key=api_key,
            endpoint=endpoint,
            deployment_name=deployment_name,
            api_version=api_version,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    @staticmethod
    def _create_external_api_provider() -> ExternalAPIProvider:
        """Create External API provider"""
        api_url = os.getenv("EXTERNAL_API_URL")
        authorization_header = os.getenv("EXTERNAL_API_AUTHORIZATION")
        max_tokens = int(os.getenv("EXTERNAL_API_MAX_TOKENS", "1000"))
        temperature = float(os.getenv("EXTERNAL_API_TEMPERATURE", "0.7"))
        
        return ExternalAPIProvider(
            api_url=api_url,
            authorization_header=authorization_header,
            max_tokens=max_tokens,
            temperature=temperature
        )
