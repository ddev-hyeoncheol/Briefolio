# Pipeline Rules

Ingest pipeline의 단계, dedup 계약, count 의미, 실패 전파를 정의합니다.

## Pipeline Execution

- 진입점은 `POST /ingest/run` 하나이며, 요청 body는 선택 필드 `executed_at`만 받습니다.
- `executed_at`은 UTC 10분 단위로 내림 정규화한 스케줄 슬롯 라벨입니다.
- 호출마다 `run_id`(UUID)를 생성해 캡처 경로를 유일하게 만듭니다. 모든 캡처는 append-only이며 기존 파일을 덮어쓰지 않습니다.
- 파이프라인은 최소 1회(at-least-once) 적재를 보장합니다. 중복 호출로 생긴 중복 record는 Firestore lookup이 비용을 줄이고, Silver의 news_id dedup이 최종 제거합니다.
- 등록된 모든 source는 `asyncio.gather`로 동시 실행하고, 한 source의 실패가 다른 source를 중단시키지 않습니다.
- 전체 status는 모든 source가 `success`면 `success`, 모두 `failed`면 `failed`, 섞이면 `partial`입니다.
- Router는 status가 `partial`이면 HTTP 207, `failed`이면 HTTP 500으로 응답합니다.

## Source Pipeline

- 흐름은 `Fetch -> Entry Lookup -> Enrich -> News Lookup -> Load -> State Write`입니다.
- `Fetch`는 RSS entry를 `NewsModel`로 매핑하고, 스키마 검증 실패나 published_at 누락 entry는 건너뜁니다.
- 식별 키는 정규화된 URL의 UUID v5(`make_url_id()`)로 유도합니다. `entry_key`는 entry_url 기반, `news_id`는 canonical_url(없으면 entry_url) 기반이며, 직렬화 여부는 data-contract.md를 따릅니다.
- `Entry Lookup`은 Firestore `news_state`를 entry_key로 조회해 최신 status가 `success`인 item을 제외합니다. 문서 없음과 `failed`는 재시도 대상으로 통과합니다.
- `Enrich`는 통과 item만 스크래핑하며, item 실패는 phase 실패가 아니라 `status`, `status_code`, `error_message`를 가진 record로 보존합니다.
- Enrich는 같은 news_id로 수렴한 item을 success 우선으로 1개만 남깁니다. 캡처 내 중복 제거는 이 축약이, 캡처 간 중복 제거는 Firestore lookup이 담당합니다.
- `News Lookup`은 enrich로 news_id가 entry_key와 달라진 item만 재조회합니다.
- News Lookup에서 떨어진 중복 item은 load를 기다리지 않고 entry_key를 `success`로 즉시 기록합니다.
- `Load`는 남은 item(성공/실패 record 모두)을 JSONL 한 파일로 캡처 경로에 적재하고 짝이 되는 매니페스트를 마지막에 기록합니다.
- item이 0건인 캡처도 매니페스트(count 0)는 기록해 실행 흔적을 남깁니다.
- `State Write`는 load가 예외 없이 끝난 경우에만 각 item의 news_id와 entry_key(다를 때만)에 문서를 덮어씁니다.
- `expires_at`(기록 시각 + 7일)은 Firestore TTL 정책용 필드이며, TTL 활성화는 DEBT로 추적합니다.
- Source status는 load 대상 item 중 `failed`가 하나라도 있으면 `partial`, 전부 성공이면 `success`입니다.
- Source count는 성공/실패 record를 포함한 load 대상 item 수입니다.
- phase 예외는 해당 source를 `failed_phase`와 함께 `failed`로 중단합니다. state가 기록되지 않은 item은 다음 호출에서 자동 재시도됩니다.
