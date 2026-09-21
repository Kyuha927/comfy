# WBCP 0.4.0a1 최종 후보 상태

## 결론

회원가입 전용 상태기계와 안전 경계를 구현한 **검증 가능한 후보 코드**는 완성되었습니다.

```text
STATUS=SAFE_SIGNUP_CANDIDATE_COMPLETE_PRODUCTION_BLOCKED
TESTS=172_PASS
OFFLINE_CHROMIUM_SIGNUP=PASS
REPEATED_SHORT_SOAK=1000_OF_1000_PASS
SOURCE_ARCHIVE_REPRODUCIBLE=true
PRODUCTION_READY=false
PRODUCTION_PROMOTION_GRANTED=false
```

## 이제 가능한 것

- 일반 공개 회원가입 페이지 탐색
- 비민감 입력란과 흐름 준비
- 회원가입 여정 생성, 상태 조회, 취소, 재개
- 비밀번호·OTP·CAPTCHA·약관 같은 사용자 직접 구간에서 안전 정지
- 사용자 직접 입력 뒤 페이지 변화와 현재 페이지 지문 확인
- 정확한 최종 버튼, 약관 해시, 예상 결과를 하나의 액션 다이제스트로 결속
- 단일 R4 permit과 1회 승인 뒤 최종 제출 1회
- DOM 또는 URL 변화, 픽셀 변화, 제공자 또는 네트워크 영수증의 3중 검증
- 동일 제출 재호출 시 두 번째 계정 생성을 막는 idempotency

## 자동으로 하지 않는 것

- CAPTCHA 우회
- OTP·문자·이메일 인증 코드 읽기 또는 입력
- 비밀번호·패스키·복구 코드 수집
- KYC 신분증 처리
- 사용자를 대신한 약관 동의
- 결제수단 입력 또는 유료 호출
- 대량·병렬·가짜 계정 생성
- 개인 Chrome 프로필 무승인 연결

## 검증 영수증

- 전체 단위·통합·보안 회귀: 172/172 PASS
- 실제 오프라인 Chromium과 로컬 mock provider POST 영수증: PASS
- 250작업 × 8워커 × 4회: 1000/1000 PASS
- 원장 체인 검증: 4회 모두 PASS
- 소스 117개·패키지 119개 매니페스트: PASS
- 정적 보안 검사: PASS, 발견 0
- 비밀정보 검사: PASS, 발견 0
- tar.gz 재구성 후 172 테스트: PASS
- ZIP 재구성 후 172 테스트: PASS
- Git bundle clone 후 172 테스트: PASS
- 두 번 독립 빌드의 모든 배포 파일 SHA-256 일치: PASS

## 남은 실제 Mac 게이트

1. 설치된 `wbcp-stdio`와 게시 커밋의 정확한 identity 결속
2. CUA Driver 버전·health와 macOS Accessibility·Screen Recording 확인
3. 격리 브라우저 프로필에서 Playwright·Jev·CUA 비파괴 smoke
4. 사용자 승인 아래 일회용 테스트 제공자 계정 1개 E2E
5. 페이지 drift 음성 테스트와 중복 제출 방지 확인
6. 실제 제공자 영수증 검증
7. 플러그인 원자적 설치와 이전판 rollback 복원
8. 독립 보안·릴리스 검토
9. 24시간 혼합 경로 soak
10. 선생님의 별도 생산 승격 승인

이 열 항목이 통과되기 전에는 로컬 기본 플러그인 교체와 생산 승격을 계속 차단합니다.
