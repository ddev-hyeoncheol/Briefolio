# Data Contract Rules

Entity, Schema DTO, Firestore 문서, field description 계약을 정의합니다.

## Models And Schemas

- Entity(`NewsModel`)는 GCS raw JSONL에 저장되는 record shape를 정의합니다.
- Entity 파생 키는 저장 여부로 구분합니다. `news_id`는 computed field로 직렬화하고, `entry_key`는 plain property로 직렬화에서 제외합니다.
- Entity 필드 추가, 삭제, 이름 변경은 raw JSONL 계약 변경이므로 Intelligence 소비 계획(TRANSITION.md 4장)과 충돌 여부를 확인합니다.
- Schema DTO는 API 요청/응답, pipeline phase 결과, source enrichment 결과 계약을 정의합니다.
- 요청 DTO는 사용자가 제공하는 최소 입력만 가지며 물리 리소스 식별자를 받지 않습니다.
- `status`, `failed_phase`, phase 값은 `Literal` 또는 enum으로 제한합니다.
- count 필드는 pipeline 규칙의 실제 의미와 description을 일치시킵니다.
- Pipeline 응답 전용 필드(count, failed_phase 등)는 저장 계약에 반영하지 않습니다.

## Firestore Documents

- `news_state` 문서 키는 `make_url_id()`가 유도한 URL UUID만 사용합니다.
- 문서는 `{status, url, source, executed_at, expires_at[, error_message]}` 전체 덮어쓰기로 기록하며 merge를 사용하지 않습니다.
- `expires_at`은 Provider가 기록 시각 + 7일로 주입하는 TTL 필드입니다.
- 소비자 없는 필드는 문서에 추가하지 않습니다.
- **[CRITICAL]** `make_url_id()`의 namespace와 정규화 규칙 변경은 기존 dedup 기록 전체를 무효화해 중복 적재를 유발하므로 사용자에게 명시 확인을 받습니다.

## Field Descriptions

- Entity `Field(description=...)`은 raw 데이터의 출처(RSS 제공, HTML 추출)를 드러냅니다.
- DTO description은 API 입력과 pipeline 실행 결과 계약을 설명합니다.
