# Briefolio

Briefolio는 외부 금융 뉴스를 수집해 원본 데이터를 안전하게 보존하고, 이후 정제·AI 보강·검색 API로 확장하는 GCP 기반 서버리스 데이터 플랫폼입니다.

현재 저장소에서 실행 가능한 범위는 **Briefolio Ingest**입니다. BigQuery/Dataform 기반 Intelligence와 사용자 조회용 Serving은 아직 구현 전이며, 전체 전환 계획은 [`TRANSITION.md`](TRANSITION.md)를 기준으로 관리합니다.

## Current Status

| 경계         | 책임                                                  | 상태                      |
| :----------- | :---------------------------------------------------- | :------------------------ |
| Seed         | Terraform remote state 부트스트랩                     | 구성 완료                 |
| Ingest       | RSS 수집, 본문 추출, Firestore dedup, GCS raw 적재    | 구현 및 배포 구성 진행 중 |
| Intelligence | BigQuery staging, Dataform 정제, Vertex AI 보강, mart | 구현 전                   |
| Serving      | 사용자 API, 검색, 캐시, serving 저장소                | 구현 전                   |

현재 Ingest에는 Yahoo Finance source만 활성화되어 있습니다. CNBC source 구현은 존재하지만 배포 대상에는 아직 등록되지 않았습니다.

## Architecture

현재 Ingest 흐름은 다음과 같습니다.

```text
Cloud Scheduler (구성 예정)
  → 인증된 POST /ingest/run
  → Cloud Run Ingest
      → RSS fetch
      → Firestore entry URL dedup
      → newspaper4k HTML enrich
      → Firestore canonical URL dedup
      → GCS raw JSONL + manifest
      → Firestore latest state 기록
```

최종 목표 구조는 다음과 같습니다.

```text
Briefolio Ingest
  → GCS Raw Data Lake

Briefolio Intelligence
  → BigQuery native staging
  → Dataform silver.news
  → Vertex AI augmentation
  → mart.*

Briefolio Serving
  → Firestore / Search / Vector DB
  → Cloud Run API
```

Ingest는 BigQuery나 AI 처리에 직접 의존하지 않습니다. GCS raw 이후의 정제·AI 보강은 Intelligence 경계에서 별도로 구현합니다.

## Ingest Pipeline

`POST /ingest/run`은 다음 phase를 순서대로 실행합니다.

1. **Fetch**: 등록된 RSS source를 읽고 source DTO를 `NewsModel`로 변환합니다.
2. **Entry Lookup**: Firestore에서 RSS entry URL의 최신 상태를 조회하고 이미 성공한 기사를 제외합니다.
3. **Enrich**: 신규 기사 HTML에서 본문, 저자, canonical URL, 대표 이미지와 언어를 추출합니다.
4. **News Lookup**: canonical URL로 식별자가 바뀐 기사만 Firestore에서 다시 확인합니다.
5. **Load**: source별 JSONL과 manifest를 GCS에 append-only capture로 기록합니다.
6. **State Write**: 적재가 끝난 기사에 한해 Firestore 상태를 갱신합니다.

호출의 `executed_at`은 UTC 10분 슬롯으로 내림 정규화되며, 호출마다 새로운 UUID `run_id`가 생성됩니다. 같은 슬롯을 다시 실행해도 기존 캡처를 덮어쓰지 않습니다.

### Capture Paths

```text
gs://{bucket}/news/data/executed_at={YYYYMMDDThhmmssZ}/run_id={run_id}/source={source}.jsonl
gs://{bucket}/news/manifests/executed_at={YYYYMMDDThhmmssZ}/run_id={run_id}/source={source}.json
```

기사가 0건이면 data object는 만들지 않지만, 빈 실행과 미실행을 구분할 수 있도록 manifest는 항상 기록합니다.

### Firestore State

```text
news_state/{make_url_id(url)}
  status: success | failed
  url: 원본 URL
  source: source 식별자
  executed_at: 정규화된 실행 슬롯
  expires_at: 기록 시각 + 7일
  error_message: 실패한 경우에만 기록
```

`make_url_id()`의 namespace seed와 URL 정규화 규칙은 Firestore 기록을 시작한 뒤에는 변경하지 않습니다.

## Project Structure

```text
src/
├── config/
│   └── config.py
├── core/
│   ├── logger.py
│   └── transient.py
└── ingest/
    ├── main.py
    ├── dependencies.py
    ├── router.py
    ├── service.py
    ├── models/
    ├── plugins/
    │   └── sources/
    └── providers/

terraform/
├── bootstrap.sh
├── ingest/
├── intelligence/
└── serving/

cloudbuild.yaml
Dockerfile
```

- `router.py`: HTTP 요청·응답과 pipeline status의 상태 코드를 매핑합니다.
- `service.py`: source 실행, dedup, 적재와 결과 집계를 오케스트레이션합니다.
- `plugins/`: RSS parsing과 외부 뉴스 HTML 처리를 담당합니다.
- `providers/`: Firestore와 Cloud Storage I/O를 캡슐화합니다.
- `models/`: raw record와 API DTO 계약을 정의합니다.

## Technology

- Python 3.12
- FastAPI, Pydantic v2
- feedparser, httpx, newspaper4k
- Google Cloud Storage, Firestore
- Cloud Run, Cloud Build, Cloud Scheduler
- Terraform

BigQuery, Dataform, Vertex AI는 다음 Intelligence 단계에서 도입할 예정이며 현재 Python Ingest 런타임의 의존성이 아닙니다.

## API

### `POST /ingest/run`

요청 body는 선택 필드 `executed_at`만 받습니다. 생략하면 현재 UTC 시각을 사용합니다.

```bash
curl -X POST "http://localhost:8080/ingest/run" \
  -H "Content-Type: application/json" \
  -d '{}'
```

특정 실행 슬롯을 요청할 수도 있습니다.

```json
{
    "executed_at": "2026-08-03T12:34:56+00:00"
}
```

응답 예시는 다음과 같습니다.

```json
{
    "executed_at": "2026-08-03T12:30:00Z",
    "run_id": "80c26f55-9c61-4c86-b0eb-1d1f9fc84dda",
    "status": "success",
    "count": 12,
    "started_at": "2026-08-03T12:34:56.100Z",
    "completed_at": "2026-08-03T12:35:04.400Z",
    "elapsed_seconds": 8.3,
    "details": [
        {
            "source": "yahoo_finance",
            "executed_at": "2026-08-03T12:30:00Z",
            "status": "success",
            "count": 12,
            "started_at": "2026-08-03T12:34:56.101Z",
            "completed_at": "2026-08-03T12:35:04.399Z",
            "elapsed_seconds": 8.298
        }
    ]
}
```

- `success`: HTTP 200
- `partial`: HTTP 207
- `failed`: HTTP 500

헬스 체크는 `GET /health`, Swagger UI는 `/docs`에서 확인할 수 있습니다.

## Development

로컬 실행은 애플리케이션 개발과 진단 용도로만 사용합니다. 컨테이너 빌드와 GCP 배포는 로컬 `docker build` 또는 `gcloud builds submit`을 공식 경로로 사용하지 않습니다.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.ingest.main
```

로컬에서 애플리케이션을 시작하거나 실제 Ingest를 실행하려면 Application Default Credentials와 `briefolio-ingest`의 Firestore·GCS 접근 권한이 필요합니다.

주요 환경 변수는 다음과 같습니다.

| 변수              | 설명                                     | 기본값                 |
| :---------------- | :--------------------------------------- | :--------------------- |
| `PORT`            | FastAPI 서버 포트                        | `8080`                 |
| `LOG_LEVEL`       | 로그 레벨                                | `INFO`                 |
| `K_SERVICE`       | Cloud Run이 자동 주입하는 서비스명       | 없음                   |
| `RAW_BUCKET_NAME` | raw JSONL과 manifest를 저장할 GCS bucket | `briefolio-ingest-raw` |
| `USER_AGENT`      | RSS·기사 HTML 요청 User-Agent            | Chrome 기반 기본값     |

## Deployment

공식 애플리케이션 배포 경로는 저장소 기반 Cloud Build trigger입니다.

```text
main branch push
  → Cloud Build trigger
  → 저장소의 cloudbuild.yaml 실행
  → Docker image build
  → Artifact Registry push
  → 인증 필수 Cloud Run Ingest 배포
```

Cloud Build는 revision 배포까지만 담당하며, 실제 `POST /ingest/run` 호출은 Cloud Scheduler가 담당합니다.

로컬 build·deploy는 운영 경로에서 제외합니다. Cloud Build trigger, Cloud Run runtime identity, Cloud Scheduler OIDC와 `roles/run.invoker`는 `terraform/ingest/`에서 관리하는 방향으로 구성 중입니다.

서비스 계정의 책임은 다음과 같이 분리합니다.

- **Cloud Build account**: trigger build 생성, 이미지 build·push와 Cloud Run revision 배포
- **Cloud Run runtime account**: 실행 중 Firestore와 raw GCS bucket 접근
- **Cloud Scheduler account**: OIDC token으로 비공개 Cloud Run endpoint 호출

### Manual Cloud Build Bootstrap

GitHub App 인가와 Cloud Build 2세대 저장소 연결은 Terraform 소유 대상이 아닙니다. 최초 구성 시 사용자가 다음 작업을 GCP Console에서 직접 수행합니다.

1. `briefolio-ingest` 프로젝트에서 Secret Manager API를 활성화합니다. Cloud Build가 GitHub 연결의 인증 정보를 저장하므로 secret을 별도로 만들 필요는 없습니다.
2. **Cloud Build > 저장소 > 2세대 > 호스트 연결 만들기**에서 `us-west1` 리전의 `github-ddev-hyeoncheol` 연결을 만듭니다.
3. GitHub 계정 `ddev-hyeoncheol`로 인가하고 Cloud Build GitHub App이 `ddev-hyeoncheol/Briefolio` 저장소에 접근하도록 허용합니다.
4. 해당 연결에 `ddev-hyeoncheol/Briefolio` 저장소를 연결하고 상태가 **사용 설정됨**인지 확인합니다.

현재 Terraform 입력에 사용하는 저장소의 전체 resource name은 다음과 같습니다.

```hcl
cloud_build_repository = "projects/briefolio-ingest/locations/us-west1/connections/github-ddev-hyeoncheol/repositories/Briefolio"
```

Cloud Build trigger와 그 권한은 `terraform/ingest/`가 소유하므로 Console에서 별도로 만들거나 수정하지 않습니다. 이후 Terraform `plan` 결과를 검토하고 인프라 또는 state를 변경하는 명령은 사용자가 직접 실행합니다. 연결을 폐기할 때는 Terraform에서 trigger를 먼저 제거한 뒤, 사용자가 연결된 저장소와 host connection을 Console에서 삭제하고 GitHub App 접근 권한을 회수합니다.

## Terraform

- `terraform/bootstrap.sh`: Seed project와 remote state bucket을 만드는 일회성 부트스트랩 스크립트입니다.
- `terraform/ingest/`: Ingest 프로젝트의 GCS, Firestore, Artifact Registry, IAM과 배포 리소스를 관리합니다.
- `terraform/intelligence/`: Intelligence 경계의 독립 state root이며 현재 placeholder입니다.
- `terraform/serving/`: Serving 경계의 독립 state root이며 현재 placeholder입니다.
- `terraform/` 바로 아래 `.tf` 파일: 이전 단일 프로젝트 구성으로, 전환 완료 후 제거할 레거시 root입니다.

자동 push trigger에서는 애플리케이션 이미지만 배포합니다. Terraform 변경은 `validate`와 `plan`으로 검증하고, 인프라 또는 state를 변경하는 명령은 사용자가 결과를 검토한 뒤 직접 실행합니다.

## Adding a News Source

1. `src/ingest/models/sources/`에 source RSS entry DTO를 추가합니다.
2. `src/ingest/plugins/sources/`에 `RssPlugin` 구현체를 추가합니다.
3. RSS 필드를 storage, metadata, ignored 집합으로 분류합니다.
4. `run_fetch()`에서 DTO 검증 후 `NewsModel`로 변환합니다.
5. 배포할 source를 `src/ingest/dependencies.py`의 `ENABLED_SOURCE_CLASSES`에 등록합니다.

세부 규칙은 [`.agents/guides/news-source.md`](.agents/guides/news-source.md)를 따릅니다.
