# Architecture Rules

저장소의 레이어 책임, 의존성 방향, API, Provider 동작을 정의합니다.

## Layer Responsibilities

| 레이어          | 주요 경로                        | 핵심 책임                                                              |
| :-------------- | :------------------------------- | :--------------------------------------------------------------------- |
| Entry           | `src/api/`, `src/worker/main.py` | 앱 초기화, lifespan, router 등록을 수행합니다.                         |
| Router          | `src/worker/routers/`            | HTTP 요청/응답 매핑과 상태 코드 변환을 수행합니다.                     |
| Service         | `src/worker/services/`           | 파이프라인 흐름 제어, 결과 집계, factory 기반 조립을 담당합니다.       |
| Plugin / Source | `src/worker/plugins/`            | RSS 수집과 HTML enrich 같은 외부 도메인 작업을 격리합니다.             |
| Provider        | `src/worker/providers/`          | 주입받은 외부 client의 호출 실행을 담당합니다.                         |
| Entity / Schema | `src/models/`                    | raw 저장 모델과 API/파이프라인 DTO 계약을 정의합니다.                  |
| Core / Config   | `src/core/`, `src/config/`       | 공통 로깅, FastAPI dependency, transient helper, 런타임 설정을 둡니다. |
| Infra           | `terraform/`, `cloudbuild/`      | Firestore, Cloud Storage, Cloud Run, Cloud Build 설정을 관리합니다.    |

## Boundaries & Dependencies

- 의존성은 Entry -> Router -> Service -> Plugin/Provider 방향으로 흐르며, Entity/Schema는 필요한 하위 계약으로만 참조합니다.
- Router는 비즈니스 로직을 만들지 않고 `src.models.schemas`와 Service factory만 참조합니다.
- Service는 흐름 제어와 집계를 담당하며, concrete Source와 Provider 조립은 dependency factory 내부로 한정합니다.
- Service는 Provider의 공개 메서드로 외부 저장소에 접근하고, client 초기화와 호출 세부는 Provider가 캡슐화합니다.
- Plugin은 도메인 외부 작업을 조율하며 Entity/Schema DTO를 결과 계약으로 사용합니다.
- `RssSource.run_fetch()`에는 요청 DTO 대신 `executed_at: datetime`만 전달해 결합도를 최소화합니다.
- Provider는 외부 client 호출만 관리하며 Entity/Schema 변환 책임을 갖지 않습니다.
- Entity는 다른 하위 Entity 외의 상위 레이어를 import하지 않습니다.
- Entity는 자기 필드만으로 결정되는 순수 파생 키를 property 또는 computed field로 가질 수 있습니다.
- Schema는 Entity를 참조할 수 있지만 Router, Service, Plugin, Provider를 import하지 않습니다.
- `asyncio.Semaphore`처럼 event loop에 종속되는 객체는 모듈 레벨에서 만들지 않습니다.

## API Rules

- API 형태는 `POST /ingest/run` 하나로 유지하고, source별 엔드포인트를 만들지 않습니다.
- 요청 body는 선택 필드 `executed_at`만 받으며 물리 리소스 식별자를 받지 않습니다.
- 활성 source는 `ENABLED_SOURCE_CLASSES` registry로만 관리합니다.
- 물리 버킷 이름은 `Settings.raw_bucket_name`으로, Firestore collection 이름은 Service 모듈 상수로 관리합니다.

## Provider Rules

- 외부 client는 lifespan에서 한 번 생성해 `app.state`로 공유하고, Provider는 이를 주입받아 사용합니다.
- `FirestoreProvider`는 dedup state 문서의 일괄 조회와 전체 덮어쓰기, TTL 필드(`expires_at`) 주입을 담당합니다.
- `CloudStorageProvider`는 동기 client 호출을 `asyncio.to_thread`로 감싸 event loop를 막지 않습니다.
- Retry는 transient 오류가 있는 외부 호출에만 둡니다. 현재는 enrich HTTP fetch(tenacity)가 유일합니다.
