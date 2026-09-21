# WBCP 0.4.0a1 최종 후보 상태

## 판정

```text
STATUS=SAFE_SIGNUP_CANDIDATE_COMPLETE_PRODUCTION_BLOCKED
UNIT_INTEGRATION_SECURITY_TESTS=172_PASS
REAL_CHROMIUM_OFFLINE_SIGNUP=PASS
SYNTHETIC_OFFLINE_BROWSER_RESPONSE=PASS
REAL_PROVIDER_ACCOUNT_TRANSACTION=NOT_RUN
REPEATED_SHORT_SOAK=1000_OF_1000_PASS
TAR_RECONSTRUCTION=172_PASS
ZIP_RECONSTRUCTION=172_PASS
GIT_BUNDLE_RECONSTRUCTION=172_PASS
PRODUCTION_READY=false
PRODUCTION_PROMOTION_GRANTED=false
```

## 구현 범위

일반 공개 회원가입 흐름을 준비하고, 비밀번호·패스키·OTP·이메일 인증·CAPTCHA·KYC·복구 설정은 사용자가 브라우저에서 직접 처리하도록 멈춥니다. 민감 입력 전에 Playwright trace를 중지하며, 입력값 대신 전후 브라우저 지문만 일회성 proof로 보관합니다.

최종 계정 생성은 정확한 제공자 호스트, 페이지 revision, DOM·픽셀 digest, 사용자 handoff digest, 대상 버튼, 약관 해시, `billing_effect=none`, 세 가지 사후조건, 단일 호출 permit, 일회성 high-impact approval가 모두 결속되어야 합니다.

대량·병렬 가입, 합성/일회용 신원, CAPTCHA 우회, 모델 문맥의 비밀번호·OTP·결제정보, 결제 또는 구독 활성화는 차단됩니다. 유료 가입은 별도의 비용 결속 구매 흐름이 필요합니다.

## 실제 검증

- 172개 단위·통합·보안 회귀: PASS
- 실제 Chromium 오프라인 DOM·픽셀·handoff 경로: PASS
- 합성 blob 브라우저 응답 영수증: PASS
- 사용자 비밀번호 문자열의 파일·trace 잔류 검사: PASS, 잔류 0
- worker-router acceptance: PASS
- 정적 보안 검사: PASS, 발견 0
- 비밀정보 검사: PASS, 발견 0
- 8 workers × 250 operations × 4 runs: 1000/1000 PASS
- source tar.gz, ZIP, Git bundle 재구성 후 각각 172 tests PASS
- 두 독립 빌드의 모든 배포 파일 SHA-256: 동일

## 정확한 소스 identity

```text
SOURCE_TAR_SHA256=ec006c9080a87c9ef1c6a49b5559b5eb328b456ed2391d755c2b3cc7ef06282e
SOURCE_ZIP_SHA256=64f81d147b292641f65b110f4142afb3f6a1d7d408a21f5d90e4da8680aaf015
GIT_BUNDLE_SHA256=f45e1736d35acc0554f9d5ecedee933c5d84f7bacd525a0f4412cf33e10213ff
SOURCE_TREE_SHA256=2350cb43562a33852498f1ddd9ef17ad76c3e165437bb3fd10ab82a5e28d2c00
PACKAGE_TREE_SHA256=cd0ae9b6789803e411ef9830156e98baa5cd7faf532f336f5e8febaf28a276e0
DETERMINISTIC_GIT_COMMIT=2f6460760ef4ac8a10ae614aca425a4f113e485f
DETERMINISTIC_GIT_TREE=8bb7826c2282637374faf6c78c7e083058b05f2c
```

## 아직 남은 게이트

1. target Mac의 설치된 `wbcp-stdio` identity 확인
2. CUA Driver 버전·health와 macOS Accessibility·Screen Recording 확인
3. 격리 profile의 Playwright·Jev·CUA smoke
4. 명시 승인된 일회용 무료 서비스 계정 1개 실제 E2E
5. 실제 제공자 영수증과 증거 원장 대조
6. 페이지 drift·중복 제출 음성 테스트
7. 플러그인 원자적 설치와 이전판 rollback
8. 독립 보안·릴리스 검토
9. 24시간 혼합 경로 soak
10. 별도 사용자 생산 승격 승인

이 문서는 실제 계정 생성 성공이나 production 승격을 주장하지 않습니다.
