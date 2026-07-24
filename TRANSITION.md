# Briefolio Transition Plan

## Project Identity

- 제품 표시 이름은 `Briefolio`입니다.
- 저장소 및 리소스에 사용하는 기술 식별자는 `briefolio`입니다.
- 기존 `Gemini News Brief` 명칭은 전환 과정에서 순차적으로 제거합니다.
- 프로젝트 이름은 특정 AI provider나 저장 계층을 포함하지 않습니다.
- `Briefolio Intelligence`는 기존 Warehouse와 Enrichment 책임을 하나의 경계로 통합합니다.

| 경계 | 프로젝트 명칭 | 프로젝트 ID | 핵심 책임 |
| :--- | :------------ | :---------- | :-------- |
| Seed | `Briefolio Seed` | `briefolio-seed` | Terraform state 버킷 등 각 경계 project가 공통으로 의존하는 부트스트랩 인프라 관리 |
| Ingest | `Briefolio Ingest` | `briefolio-ingest` | 외부 금융 뉴스 수집, 중복 상태 관리, 본문 추출, GCS raw 적재 |
| Intelligence | `Briefolio Intelligence` | `briefolio-intelligence` | BigQuery/Dataform 정제, AI 보강, serving용 mart 생성 |
| Serving | `Briefolio Serving` | `briefolio-serving` | 사용자 API, 검색, 캐시, 조회 저장소 관리 |

- 프로젝트 ID는 목표 식별자이며 실제 GCP project 생성 전에 전역 사용 가능 여부를 확인합니다.
- 개발·운영 환경을 별도 GCP project로 분리할 때는 프로젝트 ID 끝에 `-dev`, `-prod` 환경 접미사를 추가합니다.

## 1. 전체 방향성

이 프로젝트의 장기 목표는 단일 배치 애플리케이션 안에서 수집, 정제, AI 처리, 서빙을 모두 수행하는 구조에서 벗어나, 각 계층의 책임을 명확히 분리한 데이터 플랫폼 구조로 전환하는 것이다.

현재 구조는 `BatchService.run_pipeline()` 안에서 `BRONZE NEWS → SILVER NEWS → SILVER NEWS_AUGMENTED`가 순차 실행되는 형태이다. 즉 수집, 정제, AI 증강이 하나의 파이프라인 호출 안에 강하게 결합되어 있다.

또한 현재 Bronze 저장은 `BronzeStore.load_bronze_news()`에서 BigQuery `bronze.news`에 직접 JSON load job을 수행하는 방식이다. 장기적으로 raw 데이터는 BigQuery가 아니라 Cloud Storage 기반 Data Lake로 옮기고, BigQuery는 Silver 이후의 정제·분석·서빙 준비 계층으로 사용하는 방향이 맞다.

최종 목표 구조는 다음과 같다.

```text
Briefolio Ingest (briefolio-ingest)
  → Cloud Storage Raw Data Lake

Briefolio Intelligence (briefolio-intelligence)
  → BigQuery staging (GCS JSONL을 load job으로 적재, External Table 미사용)
  → Dataform
  → silver.news
  → silver.news_augmented
  → mart / serving export

Briefolio Serving (briefolio-serving)
  → Firestore / Search / Vector DB
  → Cloud Run API
  → User-facing service
```

단, `silver.news → silver.news_augmented`는 단기적으로 기존 Gemini API 기반 Cloud Run worker를 유지하되, 장기적으로는 별도 서비스 없이 BigQuery에서 Vertex AI remote model을 직접 호출하는 Dataform SQL 스텝으로 전환한다 (검증 실패 시에만 Cloud Run 기반 Vertex AI 구조로 대체).

---

## 2. 프로젝트 분리 기준

장기적으로 프로젝트는 최소 3개 경계로 나눈다.

```text
1. Briefolio Ingest (briefolio-ingest)
2. Briefolio Intelligence (briefolio-intelligence)
3. Briefolio Serving (briefolio-serving)
```

AI augmentation은 BigQuery에서 Vertex AI remote model을 직접 호출하는 Dataform SQL 스텝으로 처리하면, 별도 실행 서비스 없이 Briefolio Intelligence 안에 계속 남는다.

다음과 같이 SQL 밖의 커스텀 로직이 필요해져도 Cloud Run fallback을 Briefolio Intelligence 안에서 운영하며 별도 프로젝트 경계를 추가하지 않는다.

```text
- BigQuery 구조화된 출력 함수가 silver.news_augmented의 nested/다중 필드 스키마를 지원하지 못하는 경우
- embedding, batch prediction, fine-tuning처럼 SQL 함수로 표현하기 어려운 워크로드가 생기는 경우
- Vertex AI 사용량, 재시도, fallback 구조가 SQL 밖의 커스텀 로직을 필요로 할 정도로 커지는 경우
```

```text
Briefolio Ingest
  → Briefolio Intelligence
  → Briefolio Serving
```

---

## 3. Briefolio Ingest 계획

### 3.1 역할

Ingest의 책임은 외부 뉴스 데이터를 가져와 raw 형태로 안전하게 저장하는 것이다. 수집 로직의 BigQuery 의존성을 완전히 배제하기 위해, 중복 수집 방지(이미 수집된 기사 검사)는 Firestore를 활용하여 수행한다.

Firestore에는 기사 본문을 저장하지 않고, URL별 최신 처리 상태만 저장한다. 문서 키는 정규화된 URL의 UUID v5(`make_url_id()`)이며, entry URL 키와 canonical URL 키가 같은 컬렉션을 공유한다 (canonical이 entry와 같으면 문서 1개로 수렴).

```text
Firestore collection:
  news_state/{make_url_id(url)} → { status, url, source, executed_at, expires_at[, error_message] }
    # status: "success" | "failed"
    # url: 키의 원본 URL (UUID 역참조용)
    # source + executed_at: 해당 상태를 확정한 실행 → GCS 파티션 역참조 가능
    # error_message: 실패 문서에만 포함
```

조회는 두 단계다: Enrich 이전에 entry URL 키로 1차 필터, Enrich 후 canonical URL로 키가 바뀐 item만 2차 필터. 필터 조건은 "키 문서가 없거나 최신 status가 `failed`이면 재시도 대상으로 통과"이며, 현행 BigQuery 7일 윈도우 조회의 재시도 정책을 그대로 유지한다. `expires_at`은 이 7일 정책을 Firestore TTL로 구현한 필드다.

Ingest가 담당할 작업은 다음이다.

```text
- RSS feed fetch
- source별 entry parsing
- Firestore 기반 중복 수집 필터링 (entry URL 키 1차 검사 → Enrich 후 키가 바뀐 item만 2차 검사)
- newspaper4k 기반 HTML enrich (신규 기사에 한함)
- NewsModel 생성
- GCS JSONL 저장
- 캡처별 manifest JSON 저장
- Firestore에 entry/canonical URL 키별 최신 state 문서 기록 (success 또는 failed)
```

Ingest가 담당하지 않을 작업은 다음이다.

```text
- BigQuery silver.news 생성
- BigQuery를 통한 수집 중복 조회 및 적재
- Dataform transformation
- LLM augmentation
- serving API
- 사용자 검색/조회
```

### 3.2 저장 위치

원본 데이터는 Cloud Storage에 JSONL로 저장한다.

추천 경로는 다음과 같다.

```text
gs://{bucket}/news/data/executed_at={YYYYMMDDThhmmssZ}/run_id={run_id}/source={source}.jsonl

gs://{bucket}/news/manifests/executed_at={YYYYMMDDThhmmssZ}/run_id={run_id}/source={source}.json
```

경로 계층은 포함 관계를 그대로 따른다: 슬롯(`executed_at`)이 호출(`run_id`)들을 담고, 한 호출이 source별 캡처 파일들을 담는다. 날짜/시간 조회는 `executed_at=` 값의 prefix로 수행한다 (일: `executed_at=20260714`, 시간대: `executed_at=20260714T09`). 나열이 시간순으로 정렬되며, source는 row 필드로도 존재하므로 경로 조회 단위로 두지 않는다.

`data`와 `manifests`를 분리하는 이유는 BigQuery load job이 `*.jsonl`만 읽도록 하기 위해서다. 매니페스트가 같은 wildcard에 섞이면 schema mismatch가 발생할 수 있다.

`run_id`는 호출마다 생성하는 UUID다. RSS 재호출은 같은 원본의 재처리가 아니라 새로운 관측이므로, 중복·재시도 호출은 기존 캡처를 덮어쓰지 않고 서로 다른 immutable capture로 축적된다(append-only). 캡처 간 중복 기사는 Firestore dedup이 비용을 줄이고 Silver의 news_id dedup이 최종 제거한다.

item이 0건인 캡처도 매니페스트는 기록해 "빈 캡처"와 "미실행"을 구분할 수 있게 한다. 이때 데이터 파일은 생성하지 않는다.

### 3.3 Ingest 완료 기준

Ingest는 다음 조건을 만족하면 완료된 것으로 본다.

```text
- Firestore 조회를 통해 중복 기사는 스크래핑 단계 진입 전에 필터링됨
- 10분 슬롯 executed_at 정규화 및 호출별 run_id 생성
- source별 JSONL 파일 생성
- 캡처별 manifest JSON 생성
- GCS에 저장된 JSONL을 Python에서 재독해 가능
- BigQuery에 직접 bronze.news를 쓰지 않음
- Cloud Run Job 또는 Cloud Run Service에서 독립 실행 가능
```

---

## 4. Briefolio Intelligence 계획

### 4.1 역할

Intelligence는 Cloud Storage raw 데이터를 BigQuery 분석 계층으로 정제하고 AI로 보강하는 영역이다.

Intelligence가 담당할 작업은 다음이다.

```text
- GCS raw JSONL을 BigQuery staging table로 적재하는 load job 구성 (External Table 미사용 — BigQuery를 SoT로 유지해 조회 안정성/멱등성 확보)
- Dataform 기반 silver.news 생성
- Overwrite 방식으로 재처리 시 멱등성을 보장하는 쿼리 적용
- partition / clustering
- data quality assertion
- mart table/view 생성
- serving export source 생성
```

기존 Python of `SilverNewsModel.from_bronze_news()`는 `status == "success"`이고 `content is not None`인 row만 통과시키며, `canonical_url or entry_url`을 대표 URL로 사용한다. 이 로직은 SQL로 옮기기 적합하다.

### 4.2 Dataform 도입 방향

Dataform은 `GCS raw → silver.news` 변환의 중심이 된다.

GCS raw JSONL은 External Table로 선언하지 않고, BigQuery load job으로 native staging table에 복제해 적재한다. External Table은 조회 시점에 GCS 파일 상태에 직접 의존해 스키마 불일치나 일시적 조회 실패에 노출되므로, BigQuery를 Silver 이후 계층의 SoT로 유지하고 쿼리 안정성과 멱등성을 확보하려는 목적에는 맞지 않는다.

```text
GCS JSONL
  → BigQuery load job: bronze_staging.news_raw (native staging table)
  → Dataform incremental table: silver.news (Overwrite 기반 멱등성 쿼리)
```

적재 트리거는 Eventarc로 `news/data/**` 객체 생성 이벤트만 구독한다. `news/manifests/**`는 구독 대상이 아니다 — 캡처 파일이 source당 통짜 1개(멀티파트 아님)라 객체 생성 자체가 이미 완결 신호이고, manifest는 0건 실행을 남기기 위한 운영자용 기록일 뿐 적재 로직이 기다릴 대상이 아니다.

Eventarc는 at-least-once 전달이라 같은 이벤트가 중복 도착할 수 있다. load job의 `jobId`를 객체 경로에서 유도한 결정적 값(`run_id`+`source`, 예: `load_{run_id}_{source}`)으로 지정해 멱등성을 확보한다. `run_id`는 한 호출의 모든 source가 공유하므로 `source`를 반드시 함께 포함해야 한다. 이미 존재하는 jobId 재제출은 BigQuery가 거부하며, 핸들러는 이 거부를 실패가 아닌 정상 완료로 처리한다.

Eventarc는 트리거 생성 이전 객체나 재시도 보존 기간을 넘긴 장애를 커버하지 못하므로, 같은 load 로직을 `executed_at=` prefix 목록 조회로 재실행하는 백필/재조정 절차를 별도로 둔다. jobId가 결정적이라 이미 적재된 구간과 겹쳐 실행해도 안전하며(중복은 스킵), 주기적(예: 매일 최근 24시간 재스캔) 실행을 권장한다.

### 4.3 silver.news 설계

`silver.news`는 정제된 뉴스 원문 테이블이다.

주요 필드는 현재 모델을 유지한다. `news_id`는 Ingest가 URL(canonical 우선) 기반 UUID v5로 유도해 raw JSONL에 포함한다.

```text
executed_at
news_id
source
title
url
published_at
updated_at
raw_authors
raw_content
image_url
thumbnail_url
language
loaded_at (Dataform SQL에서 CURRENT_TIMESTAMP()를 기본값으로 사용)
```

권장 partition과 clustering은 다음이다.

```text
Partition:
  DATE(published_at)

Clustering:
  source
  news_id
```

### 4.4 dedupe 및 멱등성 정책

Bronze raw는 append-only로 두고, 중복 제거는 Silver에서 수행한다.

기본 dedupe 및 멱등성 적재 기준은 다음이다.

```text
news_id 기준 latest successful record 선택
동일 news_id가 여러 batch에 있으면 published_at 또는 loaded_at 기준 최신 row 선택
배치 재처리 시 동일 executed_at 데이터가 중복 적재되지 않도록 Overwrite 쿼리를 사용해 멱등성 보장
```

초기에는 단순하게 `WHERE` 필터와 `ROW_NUMBER()`로 처리한다. `status`/`content` 필터를 dedupe보다 먼저 적용해야, 실패 재시도 row가 이전 성공 row를 밀어내지 않는다.

```sql
SELECT *
FROM bronze_staging.news_raw
WHERE status = 'success' AND content IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY news_id
  ORDER BY executed_at DESC, loaded_at DESC
) = 1
```

### 4.5 Intelligence 완료 기준

Intelligence는 다음 조건을 만족하면 완료된 것으로 본다.

```text
- GCS raw JSONL이 Eventarc 트리거로 BigQuery staging table에 적재됨 (jobId 기반 멱등성 포함)
- 같은 load 로직 기반의 백필/재조정 절차가 구성됨
- Dataform으로 silver.news 생성 가능
- silver.news가 partitioned / clustered table로 생성됨
- news_id 중복 제거 및 Overwrite 기반의 멱등성 적재 가능
- assertion 실패 시 workflow 실패 처리 가능
- Python _run_silver_news 의존도 제거
```

---

## 5. AI Augmentation / Vertex AI 전환 계획

### 5.1 현재 위치

현재 `silver.news → silver.news_augmented`는 Python worker에서 Gemini provider를 호출하는 구조다. 현재 `BatchService`도 `SILVER NEWS_AUGMENTED` 단계를 pipeline task로 포함하고 있다.

단기적으로는 이 구조를 유지하되, `silver.news` 생성은 Dataform으로 넘기고, AI augmentation worker는 `silver.news`를 읽어 `silver.news_augmented`에 적재하는 역할만 맡긴다. 이 Cloud Run worker 구조는 5.3의 SQL 네이티브 검증이 끝나기 전까지의 임시 경로이며, 검증에 실패했을 때의 fallback 경로로도 유지한다.

### 5.2 단기 구조

```text
Dataform
  → silver.news

Cloud Run AI Augment Worker
  → BigQuery silver.news extract
  → Gemini API call
  → BigQuery silver.news_augmented load
```

### 5.3 장기 Vertex AI 구조

장기적으로는 별도 실행 서비스 없이 BigQuery SQL에서 Vertex AI remote model을 직접 호출하는 구조로 전환한다.

```text
BigQuery silver.news
  → Dataform SQL: BigQuery remote model 연결(Vertex AI Gemini)
  → AI.GENERATE_TABLE 등 구조화된 출력 함수 호출
  → silver.news_augmented (Dataform incremental/MERGE)
```

이 구조가 성립하면 AI augmentation은 별도 Cloud Run 서비스 없이 Intelligence Dataform 파이프라인의 한 SQL 스텝으로 흡수된다.

**검증 필요 항목** — 채택 전에 다음을 프로토타입으로 먼저 확인한다.

```text
- ai_market_entities처럼 REPEATED RECORD가 포함된 output schema를 구조화된 출력 함수가 한 번에 생성할 수 있는지
- 한글 번역/요약처럼 여러 개의 장문 텍스트 필드를 하나의 호출로 안정적으로 받을 수 있는지
- row 단위 생성 실패가 전체 쿼리를 중단시키지 않고 해당 row만 실패로 남는지
- 현재 3개 기사 chunk 호출 대비 row 단위 호출의 비용/처리 시간 차이
```

검증에 실패하면 다음 Cloud Run 기반 구조로 대체한다.

```text
silver.news
  → enrichment input table
  → Cloud Run: Vertex AI SDK 호출
  → enrichment result table
  → Dataform merge
  → silver.news_augmented
```

### 5.4 provider abstraction

Vertex AI 전환을 쉽게 하기 위해 먼저 provider interface를 분리한다.

```text
AiProvider
  - GeminiApiProvider
  - VertexAiProvider
```

현재는 Gemini API를 직접 쓰더라도, 상위 service는 provider 구현체를 몰라야 한다.

권장 interface는 다음과 같다.

```python
class AiNewsAugmentationProvider:
    async def augment_news_batch(
        self,
        items: list[SilverNewsModel],
    ) -> list[SilverNewsAugmentedModel]:
        ...
```

이 provider abstraction은 5.2(Gemini API worker)나 5.3의 fallback 경로(Cloud Run + Vertex AI SDK)에서만 필요하다. 5.3의 SQL 네이티브 경로가 검증되어 채택되면 AI 호출이 전부 Dataform SQL 안에 있으므로 이 Python provider abstraction은 필요 없어진다. 따라서 이 작업은 SQL 네이티브 검증 결과가 나올 때까지 낮은 우선순위로 둔다.

### 5.5 silver.news_augmented 유지 전략

`silver.news_augmented`는 장기적으로도 BigQuery에 유지한다.

필수 metadata는 다음이다.

```text
model_provider
model_version
prompt_version
schema_version
executed_at
news_id
loaded_at
```

Vertex AI로 전환하더라도 `model_provider = "vertex_ai"` 또는 `model_provider = "google_vertex_ai"`처럼 명확히 남긴다. SQL 네이티브 경로에서는 이 값들을 Dataform SQL의 리터럴 또는 remote model 연결 metadata로 채운다.

### 5.6 AI Augmentation 완료 기준

```text
- silver.news 생성과 AI augmentation 실행이 분리됨
- AI 처리는 silver.news만 source로 사용
- SQL 네이티브 검증 결과에 따라 Dataform SQL 단일 스텝 또는 provider interface 기반 Cloud Run 중 하나로 확정
- silver.news_augmented에 model_provider/model_version 기록
- failed item retry 가능 (row 단위 또는 item 단위)
- 이미 augmented된 news_id skip 가능
```

---

## 6. Briefolio Serving 계획

### 6.1 역할

Serving은 사용자-facing API와 검색/조회 최적화 계층이다.

Serving이 담당할 작업은 다음이다.

```text
- 최신 뉴스 목록 API
- 뉴스 상세 API
- 카테고리/시장 엔티티 기반 조회
- 검색 API
- embedding/vector search
- Firestore 또는 별도 serving DB 관리
- cache
```

Serving이 직접 BigQuery `silver` 전체를 읽는 구조는 피한다. 대신 Intelligence에서 serving 전용 mart/export를 만든다.

```text
BigQuery mart.latest_news
BigQuery mart.news_search_source
BigQuery mart.market_entity_news
```

Serving은 이 mart를 기반으로 Firestore/Search/Vector DB에 필요한 subset만 복제한다.

### 6.2 Serving 저장소

초기에는 Firestore를 serving DB로 사용할 수 있다.

```text
Firestore collections:
  news
  news_by_category
  news_by_market_entity
  latest_news
```

검색이 중요해지면 별도 검색 계층을 둔다.

```text
초기:
  Firestore

중기:
  Firestore + embedding table

장기:
  Vector DB / Vertex AI Vector Search / AlloyDB pgvector 등 검토
```

### 6.3 Serving 완료 기준

```text
- BigQuery silver/mart와 serving DB가 분리됨
- 사용자 API는 BigQuery raw/silver에 직접 의존하지 않음
- Firestore 또는 search index에 serving subset 적재 가능
- serving API는 독립 Cloud Run service로 실행 가능
```

---

## 7. Terraform 전환 계획

Terraform도 서비스 경계에 맞춰 나눈다. 각 경계는 처음부터 독립된 root와 state를 갖는다.

### 7.1 현재 구조

```text
terraform/
  bootstrap.sh   # briefolio-seed project/상태 버킷 생성용 1회성 수동 스크립트 (Terraform 밖에서 실행)
  ingest/        # briefolio-ingest state root
  intelligence/  # briefolio-intelligence state root
  serving/       # briefolio-serving state root
```

각 root(`ingest/`, `intelligence/`, `serving/`)는 `main.tf`(backend)와 `provider.tf`로 구성되고, `briefolio-tfstate` 버킷을 공유하되 `prefix`로 state 파일을 분리한다 (`{경계}`).

`seed/` root는 아직 없다. `briefolio-seed` project와 상태 버킷(`briefolio-tfstate`)은 `bootstrap.sh`로 생성했고, 현재 Terraform으로 관리할 추가 리소스가 없기 때문이다. 공유 CI/CD 같은 리소스가 필요해지면 그때 `terraform/seed/`를 추가한다.

### 7.2 향후 구조

dev/prod처럼 여러 환경을 실제로 분리해야 하는 시점이 오면, 각 root 안에 `envs/{env}/`를 추가하는 방식으로 확장한다. 환경이 하나뿐인 지금은 미리 만들지 않는다.

---

## 8. GCP Project 분리 계획

목표 GCP project는 Project Identity에 정의한 4개 경계로 구성한다.

```text
Briefolio Seed
project_id: briefolio-seed
  - Terraform state GCS 버킷 (ingest/intelligence/serving state를 prefix로 분리 보관)

Briefolio Ingest
project_id: briefolio-ingest
  - Cloud Run Ingest
  - Cloud Scheduler
  - source secrets
  - Firestore ingestion state
  - GCS raw data

Briefolio Intelligence
project_id: briefolio-intelligence
  - BigQuery
  - Dataform
  - Vertex AI remote model 연결
  - Cloud Run AI augmentation fallback
  - GCS raw data read IAM

Briefolio Serving
project_id: briefolio-serving
  - Cloud Run API
  - Firestore serving data
  - Search / Vector DB
```

Seed(`briefolio-seed`)와 Ingest(`briefolio-ingest`)는 이미 실제 GCP project로 생성되었다. Intelligence/Serving은 해당 경계의 구현이 시작될 때 같은 방식으로 생성한다.

---

## 9. 실행 로드맵

### Phase 0. Contract 정리

목표는 schema와 데이터 계약을 먼저 확정하는 것이다.

작업:

```text
- NewsModel schema 확정
- SilverNewsModel schema 확정
- SilverNewsAugmentedModel schema 확정
- GCS JSONL schema version 정의
- run_id 규칙 정의
- Firestore 수집 중복 여부 인덱스 스키마 정의
```

완료 기준:

```text
- schema_version 명시
- GCS path convention 문서화
- Firestore state 스키마(news_state 단일 컬렉션, URL 키) 문서화
```

---

### Phase 1. Ingest 분리

목표는 raw 수집을 BigQuery에서 Cloud Storage로 옮기는 것이다.

작업:

```text
- src/worker/ → src/ingest/, src/api/ → src/serving/ 디렉토리 리네이밍
- src/core/dependencies.py에서 service별 provider 의존성을 ingest/serving 각자의 dependencies.py로 분리
- CloudStorageProvider 추가
- FirestoreProvider 및 중복 필터 로직 추가
- requirements.txt에 google-cloud-storage, google-cloud-firestore 추가
- GCS bucket 및 Firestore 설정 추가
- load를 BigQuery에서 GCS JSONL로 변경
- /ingest/run 독립 실행 검증
```

완료 기준:

```text
- src/ingest, src/serving, src/core 구조로 재편됨 (13절 참고)
- BigQuery bronze.news에 쓰지 않음
- GCS에 batch별 JSONL 생성
- Firestore에 수집 이력 기록 및 중복 필터 작동
- GCS JSONL 재독해 가능
```

---

### Phase 2. Dataform 기반 Silver 전환

목표는 Python의 `_run_silver_news()`를 Dataform으로 대체하는 것이다.

작업:

```text
- Dataform repository 구성
- bronze_staging.news_raw staging table 생성 및 GCS → BigQuery load job 구성
- silver.news incremental table 생성 (Overwrite 멱등성 쿼리 적용)
- dedupe SQL 작성
- assertions 추가
- 기존 Python Silver transform 비활성화
```

완료 기준:

```text
- Dataform 실행만으로 silver.news 생성 가능
- content 없는 row 제외
- failed row 제외
- news_id dedupe 및 멱등성 덮어쓰기 적용
- partition/clustering 적용
```

---

### Phase 3. AI Augmentation 분리

목표는 AI 처리 단계를 Dataform Silver 이후 독립 실행되도록 만드는 것이다. 이 phase는 SQL 네이티브 경로 검증을 먼저 수행한다.

작업 (3a. SQL 네이티브 검증):

```text
- silver.news 샘플로 BigQuery remote model 연결(Vertex AI) 프로토타입 구성
- ai_market_entities 등 REPEATED RECORD 출력 검증
- 한글 번역/요약 다중 필드 출력 검증
- row 단위 실패 처리 방식 검증
- 기존 3개 chunk 호출 대비 row 단위 호출의 비용/처리 시간 비교
```

완료 기준 (3a):

```text
- 구조화된 출력 함수가 silver.news_augmented 스키마를 그대로 채울 수 있는지 결론
- 결론에 따라 3b(SQL 네이티브) 또는 3c(Cloud Run fallback) 진행 여부 확정
```

작업 (3b. SQL 네이티브 채택 시):

```text
- Dataform SQL에 remote model 호출 추가
- silver.news에서 미처리 news_id만 대상으로 하는 incremental 로직 작성
- row 단위 실패를 별도 컬럼/재시도 대상으로 보존
```

작업 (3c. Cloud Run fallback 채택 시):

```text
- AI worker를 /batch/silver/news_augmented 전용으로 단순화
- silver.news에서 미처리 row만 추출
- silver.news_augmented에 append 또는 merge
- provider interface 추가
- GeminiApiProvider를 interface 구현체로 이동
```

완료 기준 (3b/3c 공통):

```text
- full pipeline 없이 augmentation만 실행 가능
- 이미 처리된 news_id skip 가능
- failed item retry 가능
- model_provider/model_version 기록
```

---

### Phase 4. Vertex AI 전환 준비 (Phase 3에서 3c를 선택했을 때만 진행)

목표는 Gemini API 직접 호출 구조를 Vertex AI로 교체 가능한 구조로 만드는 것이다. Phase 3에서 3b(SQL 네이티브)가 채택되면 이미 Vertex AI를 SQL에서 직접 쓰고 있으므로 이 phase는 건너뛴다.

작업:

```text
- VertexAiProvider 추가
- provider selection config 추가
- prompt_version 관리
- schema validation 유지
- 비용/token/latency logging 표준화
- Gemini API와 Vertex AI 결과 비교
```

완료 기준:

```text
- 동일 Silver input으로 Gemini API / Vertex AI A/B 실행 가능
- silver.news_augmented schema 변경 없이 provider 교체 가능
- model_provider로 결과 출처 구분 가능
```

---

### Phase 5. Serving 분리

목표는 사용자-facing 조회 계층을 BigQuery 분석 계층에서 분리하는 것이다.

작업:

```text
- mart.latest_news 생성
- mart.news_search_source 생성
- Firestore serving collection 설계
- BigQuery mart → Firestore export job 생성
- Cloud Run serving API 추가
```

완료 기준:

```text
- 사용자는 BigQuery silver를 직접 조회하지 않음
- Serving API가 Firestore/search index를 통해 응답
- Intelligence 장애와 Serving 장애가 분리됨
```

---

### Phase 6. Terraform / GCP Project 분리

목표는 운영 경계를 인프라 경계로 확장하는 것이다.

작업:

```text
- Terraform modules 분리
- envs/dev, envs/prod 구성
- core / ingest / intelligence / serving module 정리
- remote state 분리 검토
- GCP project 분리 검토
- cross-project IAM 구성
```

완료 기준:

```text
- ingest 변경이 intelligence 리소스를 직접 건드리지 않음
- serving 배포가 ingest/intelligence와 독립됨
- Vertex AI 권한이 intelligence 영역에 격리됨
```

---

## 10. 우선순위

가장 먼저 해야 할 순서는 다음이다.

```text
1. GCS Raw Data Lake 전환 및 Firestore 중복 체크 연동
2. Dataform으로 silver.news 생성 (Overwrite 멱등성 쿼리)
3. AI augmentation SQL 네이티브(Vertex AI remote model) 검증
4. (검증 실패 시에만) Cloud Run 기반 AI augmentation 독립 실행 및 provider abstraction
5. Serving 저장소 분리
6. Terraform module 분리
7. GCP project/state 분리
```

즉 지금 당장 해야 할 핵심은 **Ingest 분리와 raw 저장소 전환 및 중복 제거 분리**이다.
Serving이나 GCP project 분리는 나중에 해도 된다.

다만 Terraform root/state 분리와 Seed/Ingest project 생성은, 1번(GCS/Firestore 연동)을 실제 GCP 리소스 위에서 구현하기 위한 선행 준비로 먼저 진행했다.

---

## 11. 최종 목표 아키텍처

최종적으로 프로젝트는 다음 구조를 지향한다.

```text
[Briefolio Ingest]
Cloud Scheduler
  → Cloud Run Ingest (Firestore로 중복 체크)
  → GCS Raw JSONL

[Briefolio Intelligence]
Dataform
  → BigQuery bronze staging (native load, SoT 유지)
  → BigQuery silver.news (Overwrite 멱등성 보장)
  → BigQuery remote model 호출 (Vertex AI Gemini)
  → BigQuery silver.news_augmented
  → BigQuery mart.*

[Briefolio Serving]
Export Job
  → Firestore / Search / Vector DB
  → Cloud Run API
```

이 구조의 핵심은 다음이다.

```text
- Ingest의 결과물은 Data Lake이며, BigQuery에는 External Table이 아닌 load job으로 복제해 SoT와 조회 안정성을 유지
- Ingest 중복 관리는 Firestore를 활용해 BigQuery 완전 분리 (Firestore에는 URL 키별 최신 state만 저장)
- Silver는 BigQuery 정제 계층
- Augmented는 기본적으로 Intelligence Dataform SQL 안에서 Vertex AI remote model로 생성하며, SQL 네이티브가 불가능하면 같은 프로젝트의 Cloud Run fallback을 사용 (repeated/RECORD 필드는 이 경로에서만 생성되며 GCS 적재와 무관)
- Mart는 serving 준비 계층
- Serving은 별도 low-latency 조회 계층
```

---

## 12. 판단 기준

앞으로 기능을 추가할 때는 아래 기준으로 위치를 결정한다.

```text
외부에서 데이터를 가져오는가?
  → Ingest

GCS/BigQuery 데이터를 SQL로 정제하는가?
  → Intelligence / Dataform

LLM, embedding, model provider가 SQL(BigQuery remote model)로 표현 가능한가?
  → Intelligence / Dataform

SQL로 표현하기 어려운 LLM/embedding/model 워크로드인가?
  → Intelligence / Cloud Run + Vertex AI (fallback)

사용자 요청을 직접 처리하는가?
  → Serving

공통 schema나 utility인가?
  → core package
```

이 기준을 유지하면 프로젝트가 커져도 책임 경계가 무너지지 않는다.

---

## 13. 코드 디렉토리 구조

Intelligence는 SQL 네이티브 채택 시 Dataform SQL과 Terraform 리소스로만 구성되고 별도 Python 코드가 거의 없다. 따라서 `src/` 아래에는 Ingest, Serving, 그리고 둘의 공통 유틸을 담는 `core`만 존재한다.

```text
src/
  core/                # 기존 그대로 유지 — Ingest/Serving 공통 인프라 유틸
    config.py
    logger.py
    transient.py

  ingest/              # 기존 worker/ 대체
    main.py
    dependencies.py    # source_semaphore, StorageProvider, FirestoreProvider 주입
    routers/
    services/
    plugins/
      source.py
      sources/
      stores/          # gcs.py, firestore.py (BigQuery 기반 BronzeStore 대체)
    providers/
      storage.py
      firestore.py
    models/
      entities/
        news.py
      schemas/

  serving/             # 기존 api/ 대체
    main.py
    dependencies.py    # Serving 전용 조회 provider 주입
    routers/
    services/
    providers/
      firestore.py     # Ingest 중복 검사용 Firestore와 별도 collection/용도
    models/
      entities/
      schemas/
```

명명 원칙은 다음과 같다.

```text
- "shared"라는 새 이름을 만들지 않는다. 기존 src/core/가 이미 공통 유틸 역할이므로 그대로 확장한다.
- core에는 Ingest/Serving이 동일하게 쓰는 것(설정 로딩, 로거, transient 판별)만 남긴다.
- BigQueryProvider/GeminiProvider처럼 service별 provider 의존성은 core/dependencies.py가 아니라 각 서비스의 dependencies.py로 옮긴다.
- Intelligence 전용 src/ 디렉토리는 미리 만들지 않는다. Cloud Run fallback(3c)이 실제로 채택될 때만 src/intelligence/를 새로 만든다.
```

`src/worker/` → `src/ingest/`, `src/api/` → `src/serving/` 리네이밍은 코드 경로뿐 아니라 `Dockerfile`, `cloudbuild.yml`의 이미지/서비스 이름, uvicorn 실행 경로(`src.worker.main:app` 등), Terraform Cloud Run 리소스 이름에도 함께 반영한다.
