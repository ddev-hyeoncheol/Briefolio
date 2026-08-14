# Data Contract Spec

## Raw Record

- `NewsModel`은 GCS JSONL record의 canonical shape이며 `model_dump_json()` 결과를 한 줄에 하나씩 저장합니다.
- `news_id`는 `canonical_url` 우선, 없으면 `entry_url`을 정규화해 만든 UUID v5이며 computed field로 직렬화합니다.
- `entry_key`는 `entry_url`로 만든 Firestore lookup용 property이며 raw JSONL에는 직렬화하지 않습니다.
- raw record에는 RSS 원본 필드, HTML enrich 필드, item 진단, source metadata만 저장하고 pipeline 응답 필드는 넣지 않습니다.
- `NewsModel` 필드 추가, 삭제, 이름 변경은 raw 계약 변경이므로 `TRANSITION.md`의 Intelligence 소비 계획과 함께 검토합니다.
- source별 부가 정보는 JSON 직렬화 가능한 `metadata`에 두며 공통 분석 필드만 `NewsModel`의 일급 필드로 승격합니다.

## Capture Objects

- data 경로는 `news/data/executed_at={YYYYMMDDThhmmssZ}/run_id={run_id}/source={source}.jsonl`입니다.
- manifest 경로는 `news/manifests/executed_at={YYYYMMDDThhmmssZ}/run_id={run_id}/source={source}.json`입니다.
- data object는 item이 있을 때만 만들고, manifest는 빈 캡처에도 항상 마지막으로 기록합니다.
- manifest shape는 `{source, run_id, executed_at, count}`이며 `count`는 해당 source의 JSONL record 수입니다.
- 한 호출의 source들은 같은 `executed_at`과 `run_id`를 공유하고 source별 object로 분리됩니다.

## Firestore Documents

- **[CRITICAL]** Firestore state 기록을 시작한 뒤에는 `make_url_id()`의 namespace seed(`Briefolio`)나 URL 정규화 규칙을 바꾸지 않습니다. 변경하면 기존 dedup 문서 키와 호환되지 않습니다.
- `news_state` 문서 키는 entry 또는 canonical URL에 `make_url_id()`를 적용한 UUID만 사용합니다.
- 문서는 `{status, url, source, executed_at, expires_at[, error_message]}` 전체 덮어쓰기로 기록하며 merge를 사용하지 않습니다.
- `status`는 `success` 또는 `failed`이고, `error_message`는 실패 원인이 있을 때만 기록합니다.
- `expires_at`은 Provider가 기록 시각 + 7일로 주입하는 TTL 필드입니다.
- 소비자 없는 필드는 문서에 추가하지 않습니다.

## Schemas And Descriptions

- API 요청/응답, pipeline phase 결과, enrich 결과, source RSS entry는 Entity와 분리된 Schema DTO로 검증합니다.
- 요청 DTO에는 호출자가 제공하는 최소 입력만 두고 물리 리소스 식별자를 받지 않습니다.
- `status`, `failed_phase`, phase 값은 `Literal` 또는 enum으로 제한하고 count description은 pipeline 의미와 일치시킵니다.
- Entity `Field(description=...)`은 raw 데이터의 출처(RSS 제공, HTML 추출)를 드러냅니다.
- DTO description은 API 입력과 pipeline 실행 결과 계약을 설명합니다.
