# Technical Debt

이 파일은 프로젝트 인프라, 설정 및 코드베이스의 장기적인 기술 부채를 추적하고 관리하기 위한 대장입니다.

## Infrastructure & Deployment

### [Security] Cloud Run Allows Unauthenticated Calls

- **설명**: 현재 `cloudbuild/cloudbuild.yml`에서 API와 Worker Cloud Run 서비스 모두 `--allow-unauthenticated` 인자로 배포됩니다.
- **영향**: Worker가 공개되면 악의적인 무단 호출로 파이프라인 비용이 청구되거나 데이터 수집이 오작동할 위험이 있습니다. API 공개는 현재 제품 요구에 맞춘 의도된 선택입니다.
- **해결 방안**: Worker 수동 테스트 흐름과 Cloud Scheduler OIDC 호출 구성이 정리되면 Worker 서비스는 `--no-allow-unauthenticated`로 전환하고, 호출 주체에 `roles/run.invoker` 권한을 부여합니다.

### [Deployment] Terraform Apply Trigger Separation

- **설명**: 로컬에서 `terraform plan`을 확인한 뒤 push하더라도, push trigger에서 `terraform apply`까지 자동 실행하면 Cloud Build 실행 시점의 원격 state, 권한, provider 환경 차이를 다시 확인하지 못합니다.
- **영향**: 실수로 push된 Terraform 변경이나 원격 state 차이가 즉시 GCP 인프라에 반영되어 BigQuery schema, 리소스, 비용 변경이 의도보다 빠르게 적용될 수 있습니다.
- **해결 방안**: 자동 push trigger는 `terraform init`, `terraform validate`, `terraform plan`까지 실행하고, `terraform apply`는 Cloud Build 수동 trigger 또는 plan 출력 확인 후 승인 단계로 분리합니다.

## Data Contract & Ingestion

### [Concurrency] Ingest news_id Dedup Race Across Sources

- **설명**: `IngestService._run_source()`는 `asyncio.gather`로 여러 source를 동시 실행합니다. 서로 다른 source가 같은 canonical_url(같은 news_id)로 귀결되는 기사를 동시에 처리하면, 둘 다 news_lookup 시점에 `news_state`를 "없음"으로 읽어 중복으로 enrich+load를 수행할 수 있습니다.
- **영향**: 현재 `ENABLED_SOURCE_CLASSES`에 source가 하나뿐이라 발현되지 않지만, 두 번째 source를 등록하는 즉시 같은 기사가 중복 처리/저장될 수 있습니다.
- **해결 방안**: news_lookup 통과 직후 `create()`로 news_id 문서를 원자적으로 선점하고, load 완료 시 최종 상태로 갱신하는 2단계 쓰기로 전환합니다. 다만 이는 정상 케이스의 write 횟수를 1회에서 2회로 늘리므로, 두 번째 source를 실제로 활성화하는 시점에 맞춰 적용합니다.

### [Data Safety] Ingest Deletion Guards Disabled

- **설명**: 개발 단계에서 리네이밍 등 리팩토링 시 `moved` 블록 없이도 삭제 후 재생성이 매끄럽게 되도록, `terraform/ingest`의 데이터 저장소 두 곳 모두 삭제 방지 장치를 의도적으로 꺼둔 구성입니다. `google_firestore_database.state`는 `delete_protection_state`를 명시하지 않고(기본값 비활성화) `deletion_policy = "DELETE"`로 destroy가 실제 데이터베이스 삭제까지 수행하며, `google_storage_bucket.raw`는 `force_destroy = true`로 객체가 들어 있어도 destroy가 통과합니다.
- **영향**: `terraform destroy`나 리소스 블록 삭제처럼 삭제를 유발하는 모든 경로가 데이터까지 포함해 막힘없이 실행됩니다. 지금은 두 저장소 모두 비어 있어 무해하지만, 실제 `news_state` 문서와 raw JSONL이 쌓이기 시작하면 실수로 인한 전체 데이터 손실 위험이 생깁니다.
- **해결 방안**: 파이프라인이 실제로 운영되어 의미 있는 데이터가 쌓이기 시작하면 Firestore에는 `delete_protection_state = "DELETE_PROTECTION_ENABLED"`를 다시 추가하고(`deletion_policy`는 그대로 둬도 protection이 실제 삭제를 막습니다), 버킷에서는 `force_destroy`를 제거해 기본값(false)으로 되돌립니다.

### [Data Lifecycle] Firestore TTL Policy Not Configured

- **설명**: `FirestoreProvider.set_states()`는 `expires_at`(작성 시각 + 7일)을 기록하지만, Terraform에 `news_state`의 `expires_at`에 대한 `google_firestore_field` + `ttl_config` 선언이 없어 TTL 삭제가 활성화되지 않은 상태입니다. TTL 구성은 나중에 작업하기로 의도적으로 미뤘습니다.
- **영향**: 만료된 문서가 자동 삭제되지 않습니다. dedup 정확성은 유지되지만(성공한 문서는 재처리할 이유가 없음), success 문서가 무한히 쌓여 저장 비용이 계속 증가하고 7일 보존 창 설계가 동작하지 않습니다.
- **해결 방안**: 운영 시작 시점에 `terraform/ingest/firestore.tf`에 `news_state` collection의 `expires_at` 필드에 대한 `google_firestore_field` + `ttl_config {}` 리소스를 추가합니다. 애플리케이션은 이미 `expires_at`을 기록하고 있어 추가 코드 변경은 필요 없습니다.

## Testing & Verification

### [Gaps] Missing Core Logic Automated Tests

- **설명**: 현재 FastAPI 라우터, `IngestService`, `RssSource` 플러그인 등 핵심 워크플로 및 뉴스 수집 파이프라인을 검증하는 단위/통합 테스트가 존재하지 않습니다.
- **영향**: 코드베이스를 변경하거나 리팩토링할 때, 예외 처리 흐름이나 뉴스 수집 파이프라인의 오작동 및 회귀 버그를 감지하기 어렵습니다.
- **해결 방안**: `pytest` 및 `httpx.AsyncClient`를 도입하여, 라우터 엔드포인트의 입력 검증, 모의(Mocking) `FirestoreProvider`/`CloudStorageProvider` 동작, 그리고 dedup·append-only 적재 흐름을 검증하는 테스트 코드를 구축해야 합니다.
