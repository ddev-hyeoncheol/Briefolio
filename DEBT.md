# Technical Debt

이 파일은 프로젝트 인프라, 설정 및 코드베이스의 장기적인 기술 부채를 추적하고 관리하기 위한 대장입니다. 각 항목은 다음 형식으로 작성합니다.

```markdown
### [Category] Title

- **설명**: 부채의 현재 상태와 원인.
- **영향**: 방치했을 때의 위험.
- **해결 방안**: 해소 방법과 적용 시점.
```

## Infrastructure & Deployment

### [Deployment] Terraform Apply Trigger Separation

- **설명**: 기존 `cloudbuild.terraform.yml`은 `terraform apply`까지 자동 실행하도록 구성되어 있어, push 시점에 원격 state 차이나 의도치 않은 인프라 변경이 즉시 반영될 위험이 있었습니다. 레거시 단일 프로젝트 파일 정리 시 해당 파일을 제거하여 자동 apply 실행 경로를 차단했습니다.
- **영향**: 향후 Terraform CI/CD 워크플로 구축 시 자동 apply가 실행되면 BigQuery schema, 리소스, 비용 변경이 예기치 않게 적용될 수 있습니다.
- **해결 방안**: 레거시 `cloudbuild.terraform.yml`은 제거 완료되었습니다. 향후 경계별(`terraform/{ingest,intelligence,serving}`) CI 트리거는 `terraform init`, `terraform validate`, `terraform plan`까지만 실행합니다. `terraform apply`와 `terraform destroy`는 Cloud Build trigger에 포함하지 않고 사용자가 plan을 검토한 뒤 직접 실행합니다.

## Data Contract & Ingestion

### [Concurrency] Ingest news_id Dedup Race Across Sources

- **설명**: `IngestService.run()`은 `asyncio.gather`로 각 source의 `_run_source()`를 동시 실행합니다. 서로 다른 source가 같은 canonical_url(같은 news_id)로 귀결되는 기사를 동시에 처리하면, 둘 다 news_lookup 시점에 `news_state`를 "없음"으로 읽어 중복으로 enrich+load를 수행할 수 있습니다.
- **영향**: 현재 `ENABLED_SOURCE_CLASSES`에 source가 하나뿐이라 발현되지 않지만, 두 번째 source를 등록하는 즉시 같은 기사가 중복 처리/저장될 수 있습니다.
- **해결 방안**: news_lookup 통과 직후 `create()`로 news_id 문서를 원자적으로 선점하고, load 완료 시 최종 상태로 갱신하는 2단계 쓰기로 전환합니다. 다만 이는 정상 케이스의 write 횟수를 1회에서 2회로 늘리므로, 두 번째 source를 실제로 활성화하는 시점에 맞춰 적용합니다.

### [Data Safety] Ingest Deletion Guards Disabled

- **설명**: 개발 중 리소스 재생성을 쉽게 하려고 `terraform/ingest`의 삭제 방지를 의도적으로 비활성화했습니다. Firestore는 `delete_protection_state = "DELETE_PROTECTION_DISABLED"`와 `deletion_policy = "DELETE"`, GCS 버킷은 `force_destroy = true`로 구성되어 있습니다.
- **영향**: `terraform destroy`나 리소스 블록 삭제처럼 삭제를 유발하는 모든 경로가 데이터까지 포함해 막힘없이 실행됩니다. 지금은 두 저장소 모두 비어 있어 무해하지만, 실제 `news_state` 문서와 raw JSONL이 쌓이기 시작하면 실수로 인한 전체 데이터 손실 위험이 생깁니다.
- **해결 방안**: 파이프라인이 실제로 운영되어 의미 있는 데이터가 쌓이기 시작하면 Firestore에는 `delete_protection_state`를 `DELETE_PROTECTION_ENABLED`로 변경하고(`deletion_policy`는 그대로 둬도 protection이 실제 삭제를 막습니다), 버킷에서는 `force_destroy`를 제거해 기본값(false)으로 되돌립니다.

## Testing & Verification

### [Gaps] Missing Core Logic Automated Tests

- **설명**: 현재 FastAPI 라우터, `IngestService`, `RssPlugin` 등 핵심 워크플로 및 뉴스 수집 파이프라인을 검증하는 단위/통합 테스트가 존재하지 않습니다.
- **영향**: 코드베이스를 변경하거나 리팩토링할 때, 예외 처리 흐름이나 뉴스 수집 파이프라인의 오작동 및 회귀 버그를 감지하기 어렵습니다.
- **해결 방안**: `pytest` 및 `httpx.AsyncClient`를 도입하여, 라우터 엔드포인트의 입력 검증, 모의(Mocking) `FirestoreProvider`/`CloudStorageProvider` 동작, 그리고 dedup·append-only 적재 흐름을 검증하는 테스트 코드를 구축해야 합니다.
