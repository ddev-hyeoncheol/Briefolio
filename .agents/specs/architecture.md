# Architecture Spec

## Runtime Boundaries

| 영역 | 현재 경로 | 책임 |
| :--- | :-------- | :--- |
| Ingest Entry | `src/ingest/main.py` | FastAPI 초기화, lifespan, shared client 생성, router 등록 |
| Serving Entry | - | Serving 구현 전이며 Python package가 없음 |
| Dependencies | `src/ingest/dependencies.py` | app state 조회, concrete Plugin·Provider·Service 조립 |
| Router | `src/ingest/router.py` | HTTP 요청/응답과 pipeline status의 상태 코드 매핑 |
| Service | `src/ingest/service.py` | source pipeline 흐름 제어, dedup, 결과 집계 |
| Plugin | `src/ingest/plugins/` | RSS parsing, HTML enrich, source별 외부 도메인 처리 |
| Provider | `src/ingest/providers/` | 주입받은 Firestore와 Cloud Storage client 호출 |
| Model | `src/ingest/models/` | raw entity, API DTO, source DTO 계약 |
| Core / Config | `src/core/`, `src/config/` | 공통 logging, transient 판정, runtime 설정 |
| Infrastructure | `terraform/{ingest,intelligence,serving}/`, `cloudbuild/` | 프로젝트별 state root와 GCP 배포 설정 |

## Transition Boundary

- 현재 Ingest runtime과 전용 Model은 모두 `src/ingest/`에 있습니다.
- 삭제된 `src/api/` placeholder는 복원하지 않고, Serving 구현을 시작할 때 `src/serving/`을 만듭니다.
- Ingest 실행 경로에는 BigQuery, Dataform, Gemini, Vertex AI, serving 조회 책임을 추가하지 않습니다.
- Intelligence의 Python package는 Cloud Run fallback이 확정되기 전에는 만들지 않습니다.

## Dependencies

- Entry는 shared resource를 lifespan에서 생성·종료하고, Dependencies가 app state로부터 concrete Plugin·Provider·Service를 조립합니다.
- Router는 비즈니스 로직을 만들지 않고 요청 DTO와 Service dependency factory만 사용합니다.
- Service는 FastAPI와 app state를 모르며 주입받은 Plugin·Provider로 실행 흐름과 dedup을 수행합니다.
- Plugin은 외부 뉴스 데이터를 `NewsModel`로 변환하고, Provider는 외부 저장소 I/O만 캡슐화합니다.
- Provider는 Entity/Schema 변환이나 pipeline 상태 판정을 담당하지 않습니다.
- Entity와 Schema는 Router, Service, Plugin, Provider를 import하지 않습니다.
- event loop에 종속되는 semaphore와 외부 client는 lifespan에서 생성해 `app.state`로 공유하고 종료 시 client를 닫습니다.

## API And Resources

- Ingest API는 `POST /ingest/run` 하나이며 source별 endpoint를 만들지 않습니다.
- 요청 body는 선택 필드 `executed_at`만 받고 bucket, collection 같은 물리 식별자를 받지 않습니다.
- 활성 source는 Dependencies의 `ENABLED_SOURCE_CLASSES`, raw bucket은 `Settings.raw_bucket_name`, Firestore collection은 Service 상수로 관리합니다.
- `FirestoreProvider`는 상태 일괄 조회, 전체 덮어쓰기, `expires_at` 주입을 담당합니다.
- `CloudStorageProvider`는 동기 Storage 호출을 `asyncio.to_thread`로 실행합니다.
- Cloud Run Ingest 배포는 unauthenticated 호출을 허용하지 않으며 호출 주체에 `roles/run.invoker`가 필요합니다.
- 재시도는 transient HTTP 상태와 네트워크 오류에만 적용하며 구현 지점은 `RssPlugin._fetch_html()`입니다.
