# Gemini News Brief

Gemini News Brief는 GCP(Google Cloud Platform) 기반으로 뉴스 수집, 정제, 그리고 Gemini AI를 활용한 데이터 보강(요약, 감성 분석, 카테고리화, 번역, 시장 개체 추출) 작업을 자동화하고, 이를 API로 제공하는 클라우드 네이티브(Cloud-Native) 서버리스 데이터 파이프라인 프로젝트입니다.

## 🎯 목표 및 철학

- **GCP 운영 우선주의**: 로컬 환경에서는 비즈니스 로직(수집/API) 개발에만 집중하고, 복잡한 인프라 설정과 실행/스케줄링은 클라우드 관리형 서비스에 전적으로 위임합니다.
- **고성능 데이터 파이프라인**: 병목 현상 없는 비동기 병렬 처리(End-to-End Parallelism)를 통해 뉴스 크롤링과 BigQuery 적재를 고속으로 수행합니다.
- **회복 탄력성 (Resilience)**: 특정 뉴스 소스나 외부 API 장애가 발생해도 전체 파이프라인이 중단되지 않고 부분 성공(Partial Success)을 처리할 수 있는 견고한 에러 핸들링을 지향합니다.

## ⚙️ 기술 스택

- **Backend**: Python 3.12, FastAPI, Pydantic v2
- **Data/Scraping**: feedparser, newspaper4k
- **AI/LLM**: Google GenAI SDK, Gemini
- **GCP Services**: BigQuery, Cloud Run, Cloud Build, Cloud Scheduler
- **IaC**: Terraform

## 🗂️ 프로젝트 구조

```
src/
├── api/
│   └── main.py                  # 공개 API 서비스 진입점 (헬스체크 등)
├── config/
│   └── config.py                # Pydantic Settings 기반 환경 변수 관리
├── core/
│   ├── dependencies.py          # FastAPI Lifespan 자원 의존성 주입 (Semaphore, Providers)
│   ├── logger.py                # 로컬/GCP 환경 자동 전환 로거
│   └── transient.py             # 일시적 오류(429, 5xx) 판별 및 재시도 헬퍼
├── providers/
│   ├── bigquery.py              # BigQuery 공급자 (비동기 스레드 풀 구동 및 세마포어 제어)
│   └── gemini.py                # Gemini AI 공급자 (비동기 생성 및 Exponential Backoff 재시도)
├── models/
│   ├── entities/
│   │   ├── bronze_news.py       # BronzeNewsModel (원천 수집 데이터 엔티티)
│   │   ├── silver_news.py       # SilverNewsModel (정제된 뉴스 엔티티)
│   │   └── silver_news_augmented.py # SilverNewsAugmentedModel (AI 보강 뉴스 엔티티)
│   └── schemas/
│       ├── batch.py             # 배치 요청/응답 스키마 (Layer, Target 정의)
│       ├── llm.py               # Gemini 구조화된 출력(Structured Outputs) DTO 스키마
│       └── sources/
│           ├── common.py        # 뉴스 수집 공통 스키마
│           ├── cnbc.py          # CNBC 전용 RSS entry DTO
│           └── yahoo_finance.py # Yahoo Finance 전용 RSS entry DTO
└── worker/
    ├── main.py                  # Worker API 서비스 진입점 (Lifespan 자원 바인딩)
    ├── routers/
    │   └── batch.py             # /batch 엔드포인트 라우터 (전체/개별 배치 구동)
    ├── services/
    │   └── batch.py             # 레이어별/타겟별 오케스트레이션 서비스 (BatchService)
    └── plugins/
        ├── source.py            # 뉴스 수집/추출 추상화 및 공통 로직 (SourcePlugin)
        ├── db.py                # DB 관련 페이즈 제어 플러그인 (DbPlugin)
        ├── ai.py                # Gemini LLM 기반 뉴스 변환/보강 플러그인 (AiPlugin)
        ├── sources/
        │   ├── cnbc.py          # CNBC 뉴스 수집 플러그인
        │   └── yahoo_finance.py # Yahoo Finance 뉴스 수집 플러그인
        ├── stores/
        │   ├── bronze.py        # BigQuery Bronze 테이블 물리 연산 (BronzeStore)
        │   └── silver.py        # BigQuery Silver 테이블 물리 연산 (SilverStore)
        └── prompts/
            └── news_augmented.py # AI 보강에 사용되는 System Instruction 및 프롬프트
```

## 🏗️ 아키텍처 및 파이프라인 흐름

이 프로젝트는 로컬 실행보다 GCP 운영을 우선하며, 실행/스케줄링/배포는 Cloud Build + Cloud Run + BigQuery로 처리하는 클라우드 네이티브 파이프라인입니다.

배치는 스케줄러에 의해 API 호출로 트리거되며, 내부적으로 여러 소스의 작업을 비동기 이벤트 루프 기반으로 처리합니다.

### 1단계: Bronze Layer (Fetch + Lookup + Enrich + News Lookup + Load)

1. **Fetch (RSS 수집)**: 등록된 RSS source에서 raw 기사 리스트를 가져옵니다.
2. **Entry Lookup (1차 필터링)**: 최근 7일 동안 수집된 이력을 확인하여 수집된 적이 없거나, 직전 수집 시도가 실패(failed)한 기사만 수집 대상으로 선별합니다.
3. **Enrich (본문 추출)**: 선별된 기사들에 한해 `newspaper4k`를 활용하여 병렬로 HTML 본문 텍스트, 저자명, 캐노니컬 URL 등을 추출합니다.
4. **News Lookup (2차 필터링)**: 추출 결과의 캐노니컬 URL을 통해 deterministic UUID v5 형태의 `news_id`를 생성하고 최종 중복 확인을 거칩니다.
5. **Load (DB 적재)**: 최종 수집 대상 기사들을 BigQuery `bronze.news` 테이블에 적재합니다.

### 2단계: Silver Layer (Extract + Transform + Load)

1. **Extract**: 특정 배치 타임스탬프(`executed_at`)에 수집 완료된 Bronze 기사들을 추출합니다.
2. **Transform**: 본문이 정상 추출된 성공(`success`) 기사만 필터링하고, 필드를 도메인 용어에 맞게 정규화합니다.
3. **Load**: 멱등성 보장을 위해 해당 배치 데이터 선삭제 후 BigQuery `silver.news` 테이블에 적재합니다.

### 3단계: Silver Augmented Layer (Extract + Transform + Load)

1. **Extract**: Silver 정제 기사들을 추출합니다.
2. **Transform**: 기사들을 3개씩 묶어(Chunk) Gemini API에 전달하며, 감성 분석, 카테고리 분석, 번역 및 요약(한글 타이틀/요약), 주요 자산 개체(최대 5개 회사/티커 등) 정보를 도출합니다.
3. **Load**: 멱등성 보장을 위해 해당 배치 데이터 선삭제 후 BigQuery `silver.news_augmented` 테이블에 적재합니다.

## 💡 개발 주안점 (Design Considerations)

- **지연 평가(Lazy Evaluation)를 통한 리소스 최적화**: 무거운 본문 스크래핑(`Enrich`)이나 AI 분석(`Augmented`)을 무작정 수행하지 않고, DB와 대조(`Lookup`)하여 반드시 필요한 타겟 기사에 대해서만 실행되도록 설계하여 네트워크 및 컴퓨팅 리소스를 절약했습니다.
- **도메인(Domain) 기반 구조 개선**: 데이터 스토어 레이어를 `BronzeStore`와 `SilverStore`로 명확히 나열하고, `DbPlugin`, `SourcePlugin`, `AiPlugin`이 도메인 관점으로 파이프라인 페이즈 연산을 오케스트레이션하게 구성하여 높은 결합도와 낮은 유지보수 비용을 추구합니다.
- **비동기 이벤트 루프 안전성 확보**: 세마포어나 프로바이더 클라이언트 객체들을 모듈 레벨에서 즉시 인스턴스화하지 않고, FastAPI 앱의 이벤트 루프가 구동된 이후 lifespan 구문에서 생성되도록 지연 초기화(Lazy Initialization) 패턴을 도입해 런타임 루프 불일치 크래시를 방지했습니다.
- **오류 격리(Resilience)**: `asyncio.gather(..., return_exceptions=True)` 및 청크/아이템 단위 예외 처리를 활용하여 일부 기사 수집 또는 특정 LLM 청크 실패가 전체 파이프라인 실행을 중단시키지 않도록 구성했습니다.

## 🚀 배포 및 자동화 구성

이 프로젝트는 배포 과정의 모든 것을 자동화하여 개발 생산성을 극대화합니다.

- **통합 워크로드**: FastAPI 기반 API 서빙 및 Worker 서비스 단일 컨테이너 운영
- **스키마 동기화**: Terraform 기반 BigQuery 데이터셋/테이블 생성 및 스키마 관리
- **CI/CD**: Cloud Build app 배포 파이프라인은 이미지 빌드와 Cloud Run 배포를 담당하고, Terraform 파이프라인은 인프라 변경을 별도로 관리

## 🛠️ 환경 변수 (Environment Variables)

| 변수명      | 설명                                                                        | 기본값      |
| ----------- | --------------------------------------------------------------------------- | ----------- |
| `PORT`      | FastAPI 서버 포트 (Cloud Run 자동 주입)                                     | `8080`      |
| `LOG_LEVEL` | 로깅 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                             | `INFO`      |
| `K_SERVICE` | Cloud Run이 자동 주입하는 서비스명. 값이 있으면 GCP JSON 로그 포맷으로 전환 | (자동 주입) |

## 💻 로컬 실행 가이드 (Quick Start)

1. 프로젝트를 클론하고 의존성 패키지를 설치합니다.
    ```bash
    git clone https://github.com/ddev-hyeoncheol/gemini-news-brief.git
    cd gemini-news-brief
    pip install -r requirements.txt
    ```
2. (선택) 로컬에서 실제 BigQuery에 적재하려면 GCP 인증 정보를 설정합니다.
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
    ```
3. Uvicorn 서버를 실행합니다.

    ```bash
    uvicorn src.worker.main:app --host 0.0.0.0 --port 8080 --reload
    ```

    > 서버가 실행되면 `http://localhost:8080/docs`에서 Swagger UI를 확인할 수 있습니다.

    > **참고**: GCP 자격증명이 설정되지 않은 경우 앱 시작은 가능하지만, BigQuery 실행 단계는 credentials 오류로 실패합니다.

## 📝 API 사용 예시 (Usage Example)

**POST `/batch/run`**

전체 파이프라인을 트리거하여 등록된 모든 소스의 뉴스를 수집, 검사, 추출, 적재, AI 보강까지 한 번에 처리합니다.

**Request (cURL)**

```bash
curl -X POST "http://localhost:8080/batch/run" \
     -H "Content-Type: application/json" \
     -d '{}'
```

**Response (JSON)**

```json
{
    "executed_at": "2026-06-12T15:00:00Z",
    "status": "success",
    "started_at": "2026-06-12T15:00:00.123Z",
    "completed_at": "2026-06-12T15:00:15.456Z",
    "elapsed_seconds": 15.333,
    "tasks": [
        {
            "layer": "bronze",
            "target": "news",
            "executed_at": "2026-06-12T15:00:00Z",
            "status": "success",
            "count": 3,
            "started_at": "2026-06-12T15:00:00.124Z",
            "completed_at": "2026-06-12T15:00:05.123Z",
            "elapsed_seconds": 4.999,
            "details": [
                {
                    "source": "yahoo_finance",
                    "executed_at": "2026-06-12T15:00:00Z",
                    "status": "success",
                    "count": 3,
                    "started_at": "2026-06-12T15:00:00.125Z",
                    "completed_at": "2026-06-12T15:00:04.456Z",
                    "elapsed_seconds": 4.331
                }
            ]
        },
        {
            "layer": "silver",
            "target": "news",
            "executed_at": "2026-06-12T15:00:00Z",
            "status": "success",
            "count": 3,
            "started_at": "2026-06-12T15:00:05.124Z",
            "completed_at": "2026-06-12T15:00:06.123Z",
            "elapsed_seconds": 0.999
        },
        {
            "layer": "silver",
            "target": "news-augmented",
            "executed_at": "2026-06-12T15:00:00Z",
            "status": "success",
            "count": 3,
            "started_at": "2026-06-12T15:00:06.124Z",
            "completed_at": "2026-06-12T15:00:15.455Z",
            "elapsed_seconds": 9.331
        }
    ]
}
```

## 🔌 새 뉴스 소스 추가하기

1. `src/ingest/models/sources/` 아래에 source별 RSS entry DTO를 추가합니다.
2. `src/ingest/plugins/sources/` 아래에 `RssPlugin` 구현체를 추가합니다.
3. `source`, `rss_url`, `rss_entry_storage_fields`, `rss_entry_metadata_fields`, `rss_entry_ignored_fields` 프로퍼티를 정의합니다.
4. `run_fetch(executed_at: datetime)`에서 DTO 검증 후 RSS 항목을 `NewsModel` 리스트로 매핑합니다.
5. 배포 대상 source만 `src/ingest/dependencies.py`의 `ENABLED_SOURCE_CLASSES`에 등록합니다.

아래 코드는 핵심 흐름만 보여주는 최소 예시이며, 실제 source에서는 날짜 파싱 helper를 기존 구현과 맞춰 보강합니다.

```python
from datetime import datetime, timezone

from src.ingest.models.news import NewsModel
from src.ingest.models.sources.my_new_source import MyNewSourceEntrySchema
from src.ingest.plugins.rss import RssPlugin


class MyNewSource(RssPlugin):
    @property
    def source(self) -> str:
        return "my_new_source"

    @property
    def rss_url(self) -> str:
        return "https://example.com/rss"

    @property
    def rss_entry_storage_fields(self) -> set[str]:
        return {"link", "title", "published_parsed"}

    @property
    def rss_entry_metadata_fields(self) -> set[str]:
        return {"id", "summary"}

    @property
    def rss_entry_ignored_fields(self) -> set[str]:
        return {"links", "title_detail", "summary_detail", "published"}

    async def run_fetch(self, executed_at: datetime) -> list[NewsModel]:
        raw_feed = await self._fetch_feed()
        entries_data = raw_feed.get("entries") or []
        results: list[NewsModel] = []

        for entry_data in entries_data:
            try:
                entry = MyNewSourceEntrySchema.model_validate(entry_data)
            except Exception:
                continue

            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            metadata = entry.model_dump(exclude=self.rss_entry_storage_fields, mode="json")

            results.append(
                NewsModel(
                    executed_at=executed_at,
                    source=self.source,
                    title=entry.title,
                    entry_url=entry.link,
                    published_at=published_at,
                    metadata=metadata,
                )
            )

        return results
```

등록 예시는 다음과 같습니다.

```python
ENABLED_SOURCE_CLASSES = (YahooFinanceSource, MyNewSource)
```
