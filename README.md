# Notion to Confluence Migration Tool

[![npm version](https://badge.fury.io/js/notion-to-confluence.svg)](https://www.npmjs.com/package/notion-to-confluence)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Migrate your Notion pages to Confluence seamlessly with support for images, tables, code blocks, and more!

**🌟 Perfect for teams transitioning from Notion to Confluence**

## ✨ Features

- Notion REST API를 사용하여 페이지 내용 가져오기
- Confluence REST API로 페이지 업로드
- 다양한 포맷 보존:
  - 제목 (H1, H2, H3)
  - 단락 및 텍스트 포맷팅 (굵게, 기울임, 밑줄, 취소선, 코드)
  - 불릿 리스트 및 번호 리스트
  - 코드 블록 (언어 하이라이팅 지원)
  - 표 (테이블)
  - 인용구
  - 구분선
  - 콜아웃 (정보 패널로 변환)
  - 토글 (확장 가능한 섹션)
  - 할 일 목록
  - 링크
- `.env` 파일로 API 토큰 관리
- `mapping.csv` 파일로 페이지 매핑 및 갱신 관리
- `history.csv` 파일로 마이그레이션 히스토리 기록
- 배치 실행 지원: 갱신 필요한 페이지만 선택적으로 마이그레이션

## 요구사항

- Python 3.7 이상
- `requests` 라이브러리
- `python-dotenv` 라이브러리

## 설치

1. 저장소 클론 또는 파일 다운로드

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
```bash
cp .env.example .env
```

`.env` 파일을 편집하여 API 토큰 정보 입력:
```
NOTION_API_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token
CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY
```

4. 매핑 파일 생성 (CSV 기반 설정):
```bash
cp mapping.csv mapping.csv
```

`mapping.csv` 파일을 편집하여 마이그레이션할 페이지 정보 입력:

> **참고:** 이전 버전의 `config.json`은 더 이상 사용하지 않습니다. 모든 페이지 설정은 `mapping.csv`로 관리됩니다.
```csv
id,notion_url,confluence_url,should_update,last_updated
1,https://www.notion.so/My-First-Page-abc123def456,,true,
2,https://www.notion.so/My-Second-Page-xyz789ghi012,https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456,false,2025-01-15 14:30:00
```

**필드 설명:**
- `id`: 페이지 식별자 (고유한 번호나 문자열)
- `notion_url`: Notion 페이지 전체 URL
- `confluence_url`: 마이그레이션 후 Confluence URL (자동으로 업데이트됨)
- `should_update`: 갱신 여부 (`true` 또는 `false`)
- `last_updated`: 최근 갱신일 (자동으로 업데이트됨)

## API 토큰 발급 방법

### Notion API Token

1. [Notion Integrations](https://www.notion.so/my-integrations) 페이지 방문
2. "New integration" 클릭
3. Integration 이름 설정 및 생성
4. "Internal Integration Token" 복사
5. Notion에서 마이그레이션할 페이지로 이동
6. 페이지 우측 상단 "..." 메뉴 > "Connections" > 생성한 Integration 추가

### Confluence API Token

1. [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens) 페이지 방문
2. "Create API token" 클릭
3. 토큰 이름 설정 및 생성
4. 생성된 토큰 복사

### Notion Page ID 찾기

Notion 페이지 URL에서 확인:
```
https://www.notion.so/My-Page-Title-abc123def456?pvs=4
                                   ^^^^^^^^^^^^
                                   이 부분이 Page ID
```

하이픈 포함하여 전체 ID를 사용하세요.

### Confluence Parent ID 찾기

1. Confluence에서 부모 페이지로 사용할 페이지 열기
2. URL에서 페이지 ID 확인:
```
https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title
                                                              ^^^^^^
                                                              Parent ID
```

## 사용법

### 배치 실행 (권장)

`mapping.csv`에서 `should_update=true`로 설정된 페이지만 마이그레이션합니다:

```bash
python migrate.py
```

**동작 방식:**
1. `mapping.csv`를 읽어서 `should_update=true`인 페이지만 선택
2. 선택된 페이지를 Notion에서 가져와 Confluence로 마이그레이션
3. 성공 시:
   - `mapping.csv`의 `confluence_url` 업데이트
   - `mapping.csv`의 `last_updated` 현재 시간으로 업데이트
   - `history.csv`에 성공 기록 추가
4. 실패 시:
   - `history.csv`에 실패 기록 추가
   - 다음 페이지 계속 진행

### 주기적 실행 설정 (cron)

배치 작업으로 주기적으로 실행하려면 cron을 설정하세요:

```bash
# crontab 편집
crontab -e

# 매일 새벽 2시에 실행
0 2 * * * cd /path/to/notion-to-confluence && /usr/bin/python3 migrate.py >> migration.log 2>&1
```

### 히스토리 확인

`history.csv` 파일에서 과거 마이그레이션 기록을 확인할 수 있습니다:

```csv
id,timestamp,success
1,2025-01-15 14:30:00,success
2,2025-01-15 14:31:15,failure
1,2025-01-16 02:00:05,success
```

## 주의사항

- 같은 제목의 페이지가 이미 존재하면 업데이트됩니다
- Notion의 일부 블록 타입은 아직 지원되지 않을 수 있습니다
- 이미지 및 파일 첨부는 현재 버전에서 지원되지 않습니다
- 대량 마이그레이션 시 API rate limit에 주의하세요

## 트러블슈팅

### 401 Unauthorized 오류
- API 토큰이 올바른지 확인
- Notion Integration이 페이지에 연결되었는지 확인
- Confluence API 토큰과 사용자명이 올바른지 확인

### 404 Not Found 오류
- Notion Page ID가 올바른지 확인
- Confluence Parent ID가 올바른지 확인
- Confluence Space Key가 올바른지 확인

### 포맷 변환 문제
- 지원되지 않는 블록 타입은 콘솔에 경고 메시지로 표시됩니다
- 필요한 경우 `format_converter.py`에 새로운 변환 메서드 추가 가능

## 아키텍처 및 코드 품질

이 프로젝트는 다음의 소프트웨어 엔지니어링 best practices를 따릅니다:

### 코드 구조
- **관심사의 분리**: 각 모듈이 명확한 단일 책임을 가짐
- **의존성 주입**: 설정 기반 클라이언트 초기화
- **타입 안정성**: 전체 코드베이스에 type hints 적용
- **에러 처리**: Custom exception 계층 구조로 명확한 에러 핸들링

### 주요 모듈

**Core Modules:**
- `migrate.py` - 메인 마이그레이션 오케스트레이션 (MigrationService)
- `config.py` - 중앙집중식 설정 관리 (dataclass 기반)
- `exceptions.py` - Custom exception 정의
- `logger.py` - Structured logging 설정

**API Clients:**
- `notion_client.py` - Notion API 클라이언트 (retry logic 포함)
- `confluence_client.py` - Confluence API 클라이언트 (retry logic 포함)
- `retry_utils.py` - Exponential backoff retry 데코레이터

**Data Processing:**
- `format_converter.py` - Notion → Confluence 포맷 변환
- `csv_manager.py` - CSV 파일 관리 (mapping, history)

### 기능 특징

- **Retry Logic**: Exponential backoff를 사용한 API 호출 재시도
- **Structured Logging**: 상세한 로깅으로 디버깅 용이
- **Validation**: 입력 데이터 검증 (page ID, URL, title 등)
- **Error Recovery**: 개별 페이지 실패 시에도 계속 진행
- **Type Safety**: mypy로 타입 체크 가능

## 파일 구조

```
.
├── migrate.py                      # 메인 실행 스크립트
├── requirements.txt                # Python 패키지 의존성
├── .env                            # 환경 변수 (생성 필요)
├── .env.example                    # 환경 변수 예시
├── mapping.csv                     # 페이지 매핑 및 갱신 관리 (생성 필요)
├── mapping.csv.example             # 매핑 파일 예시
├── history.csv                     # 마이그레이션 히스토리 (자동 생성)
├── README.md                       # 이 파일
│
└── src/                            # 소스 코드 디렉토리
    ├── __init__.py
    │
    ├── core/                       # 핵심 모듈
    │   ├── __init__.py
    │   ├── config.py              # 설정 관리 (dataclass)
    │   ├── exceptions.py          # Custom exceptions
    │   └── logger.py              # Logging 설정
    │
    ├── clients/                    # API 클라이언트
    │   ├── __init__.py
    │   ├── notion_client.py       # Notion API 클라이언트
    │   └── confluence_client.py   # Confluence API 클라이언트
    │
    └── utils/                      # 유틸리티 모듈
        ├── __init__.py
        ├── csv_manager.py         # CSV 파일 관리
        ├── format_converter.py    # 포맷 변환기
        └── retry_utils.py         # Retry 로직
```

### 디렉토리 구조 설명

**루트 디렉토리:**
- `migrate.py` - 실행 진입점
- 설정 파일들 (`.env`, `mapping.csv`, `history.csv`)

**src/core/** - 핵심 인프라
- 설정 관리
- 예외 정의
- 로깅 설정

**src/clients/** - 외부 API 클라이언트
- Notion API 통신
- Confluence API 통신

**src/utils/** - 유틸리티 함수들
- CSV 파일 관리
- 포맷 변환
- Retry 로직

## 사용 시나리오 예시

### 시나리오 1: 초기 마이그레이션

1. `mapping.csv`에 모든 페이지를 `should_update=true`로 설정
2. `python migrate.py` 실행
3. 마이그레이션 완료 후 필요에 따라 `should_update=false`로 변경

### 시나리오 2: 특정 페이지만 업데이트

1. 업데이트하고 싶은 페이지만 `should_update=true`로 변경
2. `python migrate.py` 실행
3. 완료 후 다시 `should_update=false`로 변경

### 시나리오 3: 주기적 배치 실행

1. 주기적으로 업데이트할 페이지는 `should_update=true` 유지
2. cron으로 자동 실행 설정
3. `history.csv`로 실행 결과 모니터링

## 모니터링 및 관리

### 성공률 확인

```bash
# 전체 히스토리에서 성공/실패 건수 확인
grep "success" history.csv | wc -l
grep "failure" history.csv | wc -l
```

### 특정 페이지 히스토리 확인

```bash
# 페이지 ID가 1인 것만 필터링
grep "^1," history.csv
```

## 개발자 가이드

### 타입 체크

```bash
# mypy를 사용한 타입 체크 (옵션)
pip install mypy
mypy migrate.py src/
```

### 로깅 레벨 조정

환경 변수로 로깅 레벨을 조정할 수 있습니다:

```bash
# .env 파일에 추가
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 설정 커스터마이징

`.env` 파일에서 추가 설정을 조정할 수 있습니다:

```bash
# API 설정
API_TIMEOUT=30              # API 호출 타임아웃 (초)
API_MAX_RETRIES=3           # 최대 재시도 횟수
API_RETRY_BACKOFF=2.0       # 재시도 백오프 배수
API_PAGE_SIZE=100           # 페이지당 블록 수

# 파일 경로
MAPPING_CSV=mapping.csv
HISTORY_CSV=history.csv
```

## 코드 품질 개선사항

### 이전 버전 대비 개선점

1. **에러 처리**
   - ❌ Before: `print()` 사용, `raise_for_status()` 의존
   - ✅ After: Custom exceptions, 구조화된 에러 핸들링

2. **설정 관리**
   - ❌ Before: 함수 파라미터로 개별 전달
   - ✅ After: Dataclass 기반 중앙집중식 설정

3. **로깅**
   - ❌ Before: `print()` 문 사용
   - ✅ After: Structured logging with levels

4. **재시도 로직**
   - ❌ Before: 없음 (단일 시도만)
   - ✅ After: Exponential backoff 적용

5. **검증**
   - ❌ Before: 최소한의 검증
   - ✅ After: 입력 데이터 철저한 검증

6. **타입 안정성**
   - ❌ Before: 타입 힌트 없음
   - ✅ After: 전체 코드베이스 타입 힌트

7. **코드 구조**
   - ❌ Before: 절차적 스크립트
   - ✅ After: OOP with separation of concerns

## 라이센스

MIT
