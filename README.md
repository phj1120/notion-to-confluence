# Notion to Confluence Migration Tool

Notion 페이지를 Confluence 페이지로 마이그레이션하는 도구입니다.  
`mapping.csv`에 Notion → Confluence 페이지 매핑을 정의하고 실행하면, Notion 내용을 Confluence에 반영합니다.

## 시작하기

### 1. 패키지 설치

```bash
# 가상환경 생성 및 활성화
python -m venv .venv

# Mac / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 아래 값을 입력하세요:

```
NOTION_API_TOKEN={Notion API 토큰}
CONFLUENCE_URL=https://{your-domain}.atlassian.net
CONFLUENCE_USERNAME={your-email@example.com}
CONFLUENCE_API_TOKEN={Confluence API 토큰}
```

> **주의:** `CONFLUENCE_URL`은 도메인만 입력하세요.
> - ✅ `https://{your-domain}.atlassian.net`
> - ❌ `https://{your-domain}.atlassian.net/wiki/spaces/SPACE`

### 3. 매핑 파일 설정

```bash
cp mapping.csv.example mapping.csv
```

`mapping.csv`에 마이그레이션할 페이지를 입력하세요:

```csv
id,notion_url,confluence_url,should_update,last_updated
1,https://www.notion.so/{Notion-페이지-URL},https://{your-domain}.atlassian.net/wiki/spaces/{SPACE}/pages/{페이지ID},true,
```

- `notion_url`: 가져올 Notion 페이지 URL
- `confluence_url`: 덮어쓸 Confluence 페이지 URL (페이지를 먼저 Confluence에 생성한 후 입력)
- `should_update`: `true`인 페이지만 실행 시 마이그레이션됨

### 4. 실행

가상환경이 활성화된 상태에서 실행하세요:

```bash
python migrate.py
```

`should_update=true`인 페이지만 Notion에서 가져와 Confluence에 반영합니다.  
성공 시 `last_updated`가 자동 갱신되고, 실행 이력은 `history.csv`에 기록됩니다.

### 5. 배치 실행 (선택)

주기적으로 자동 실행하고 싶을 때 설정합니다.

**Mac / Linux — cron**

```bash
crontab -e
```

아래 내용을 추가하세요 (매일 오전 9시 ~ 오후 6시, 1시간마다 실행):

```
0 9-18 * * * cd {/path/to/notion-to-confluence} && .venv/bin/python migrate.py >> migration.log 2>&1
```

**Windows — schtasks**

`schtasks`는 Windows 기본 내장 명령어로, crontab과 유사하게 쓸 수 있습니다.  
명령 프롬프트(cmd)를 관리자 권한으로 열고 실행하세요 (매일 오전 9시 ~ 오후 6시, 1시간마다 실행):

```cmd
schtasks /create /tn "NotionToConfluence" /tr "\"{C:\path\to\notion-to-confluence}\.venv\Scripts\python.exe\" \"{C:\path\to\notion-to-confluence}\migrate.py\"" /sc hourly /mo 1 /st 09:00 /et 18:00 /k /f
```

등록된 작업은 아래 명령으로 확인하거나 삭제할 수 있습니다:

```cmd
schtasks /query /tn "NotionToConfluence"
schtasks /delete /tn "NotionToConfluence" /f
```

---

## API 토큰 발급

### Notion API Token

1. [Notion Integrations](https://www.notion.so/my-integrations) 에서 Integration 생성
2. 생성된 토큰 복사
3. 마이그레이션할 Notion 페이지에서 `...` 메뉴 → Connections → 생성한 Integration 연결

### Confluence API Token

1. [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens) 에서 토큰 생성
2. 생성된 토큰 복사

---

## 트러블슈팅

| 증상 | 확인 사항 |
|------|-----------|
| `401 Unauthorized` | API 토큰이 올바른지, Notion Integration이 페이지에 연결됐는지 확인 |
| `Page not found` | `confluence_url`의 페이지가 Confluence에 실제로 존재하는지, `CONFLUENCE_URL`에 `/wiki/spaces/...`가 포함되지 않았는지 확인 |
| 포맷 변환 문제 | 미지원 블록은 경고 로그로 표시됨. `src/utils/format_converter.py`에 변환 로직 추가 가능 |

---

## 프로젝트 구조 (참고)

```
.
├── migrate.py                  # 실행 진입점
├── mapping.csv                 # 페이지 매핑 설정
├── history.csv                 # 실행 이력 (자동 생성)
├── .env                        # 환경 변수
└── src/
    ├── core/
    │   ├── config.py           # 설정 관리
    │   ├── exceptions.py       # Custom exceptions
    │   └── logger.py           # 로깅 설정
    ├── clients/
    │   ├── notion_client.py    # Notion API 클라이언트
    │   └── confluence_client.py # Confluence API 클라이언트
    └── utils/
        ├── format_converter.py # Notion → Confluence 포맷 변환
        ├── csv_manager.py      # mapping/history CSV 관리
        └── retry_utils.py      # Exponential backoff retry
```

지원하는 Notion 블록: 제목(H1~H3), 단락, 불릿/번호 리스트, 코드 블록, 표, 인용구, 구분선, 콜아웃, 토글, 할 일 목록, 링크

## 라이센스

MIT
