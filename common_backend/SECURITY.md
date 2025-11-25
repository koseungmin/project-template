# 보안 가이드

## 클러스터 내부 전용 서비스 보안 고려사항

### ✅ 보안 위배가 아닌 이유

클러스터 내부 전용 서비스에서 JWT 인증 없이 사용하는 것은 **보안 위배가 아닙니다**. 다만, 적절한 보안 조치가 필요합니다.

#### 1. Kubernetes 네트워크 격리
- **NetworkPolicy**: 특정 파드/네임스페이스에서만 접근 허용
- **Service (ClusterIP)**: 외부 노출 차단, 클러스터 내부 통신만 허용
- **Pod Security**: RBAC, Pod Security Standards로 파드 실행 제한

#### 2. 클러스터 내부 신뢰 모델
- 클러스터 내부 파드는 기본적으로 **신뢰할 수 있는 환경**으로 간주
- 네트워크 정책으로 추가 격리 가능
- 서비스 메시(mTLS)로 더 강화 가능

### 🔒 권장 보안 조치

#### 필수 (Minimum)
1. **NetworkPolicy 적용**
   ```yaml
   # k8s-network-policy-example.yaml 참조
   # 특정 네임스페이스/파드에서만 접근 허용
   ```

2. **Service 타입: ClusterIP**
   ```yaml
   spec:
     type: ClusterIP  # 외부 노출 차단
   ```

3. **RBAC 설정**
   - 서비스 계정에 최소 권한 부여
   - 불필요한 권한 제거

#### 권장 (Recommended)
1. **서비스 메시 (Service Mesh)**
   - Istio, Linkerd 등으로 mTLS 적용
   - 자동 인증/인가 정책 관리

2. **Pod Security Standards**
   ```yaml
   # Pod Security Policy 또는 Pod Security Standards
   securityContext:
     runAsNonRoot: true
     readOnlyRootFilesystem: true
   ```

3. **네임스페이스 격리**
   - 별도 네임스페이스에 배포
   - 네임스페이스 레벨 리소스 쿼터 설정

#### 선택 (Optional)
1. **JWT 인증 활성화**
   - 다중 테넌트 환경
   - 추가 인증이 필요한 경우
   - `JWT_ENABLED=true` 설정

2. **API 키 기반 인증**
   - 간단한 인증이 필요한 경우
   - 헤더 기반 API 키 검증

### ⚠️ 주의사항

#### 보안 위험이 있는 경우
1. **네트워크 정책 미적용**
   - 모든 파드에서 접근 가능
   - 악의적인 파드가 있다면 위험

2. **다중 테넌트 환경**
   - 다른 팀/프로젝트가 같은 클러스터 사용
   - 추가 인증/인가 필요

3. **민감한 데이터 처리**
   - 암호화 키, 개인정보 등
   - 추가 보안 계층 권장

#### 안전한 경우
1. **단일 테넌트 클러스터**
   - 동일 조직/팀만 사용
   - 네트워크 정책으로 충분

2. **내부 인프라 서비스**
   - 공통 유틸리티 서비스
   - 네트워크 격리로 보호

3. **서비스 메시 사용**
   - mTLS로 자동 암호화
   - 정책 기반 접근 제어

### 📋 보안 체크리스트

배포 전 확인사항:

- [ ] NetworkPolicy 적용 (특정 파드/네임스페이스만 허용)
- [ ] Service 타입이 ClusterIP (외부 노출 차단)
- [ ] RBAC 설정 (최소 권한 원칙)
- [ ] Pod Security Standards 적용
- [ ] 네임스페이스 격리 (필요시)
- [ ] 로깅/모니터링 설정 (비정상 접근 감지)
- [ ] JWT 인증 필요 여부 판단
- [ ] 서비스 메시 사용 여부 검토

### 🎯 시나리오별 권장사항

#### 시나리오 1: 단일 팀 내부 서비스
```
✅ NetworkPolicy + ClusterIP Service
✅ JWT 불필요 (네트워크 정책으로 충분)
```

#### 시나리오 2: 다중 팀 공유 클러스터
```
✅ NetworkPolicy + ClusterIP Service
✅ JWT 또는 서비스 메시 권장
✅ 네임스페이스 격리
```

#### 시나리오 3: 민감한 데이터 처리
```
✅ NetworkPolicy + ClusterIP Service
✅ JWT 필수 또는 서비스 메시 (mTLS)
✅ 추가 감사 로깅
```

### 📚 참고 자료

- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Service Mesh Security](https://istio.io/latest/docs/concepts/security/)

### 결론

**클러스터 내부 전용 서비스에서 JWT 없이 사용하는 것은 보안 위배가 아닙니다.**

다만, 다음을 보장해야 합니다:
1. ✅ NetworkPolicy로 접근 제한
2. ✅ ClusterIP Service로 외부 노출 차단
3. ✅ RBAC 및 Pod Security 적용
4. ✅ 환경에 맞는 추가 보안 계층 고려

적절한 네트워크 정책과 격리 조치가 있다면, 클러스터 내부 서비스 간 통신에서 JWT는 선택사항입니다.

