# Ingest Pipeline Spec

## Execution

- 진입점은 `POST /ingest/run`이며, 요청의 `executed_at`은 UTC 10분 단위로 내림 정규화한 스케줄 슬롯입니다.
- 호출마다 UUID `run_id`를 새로 생성합니다. 같은 슬롯의 재호출도 별도 immutable capture로 저장하며 기존 object를 덮어쓰지 않습니다.
- 적재 의미는 at-least-once를 전제로 합니다. Firestore lookup은 불필요한 enrich를 줄이고, 최종 중복 제거는 Intelligence의 `news_id` dedup이 담당합니다.
- 등록된 source는 `asyncio.gather`로 동시에 실행하며 `_run_source()`가 phase 예외를 결과로 변환해 다른 source 실행을 보존합니다.
- source가 없거나 모두 `success`이면 전체 status는 `success`, 모두 `failed`이면 `failed`, 나머지는 `partial`입니다.
- Router는 `success`를 HTTP 200, `partial`을 HTTP 207, `failed`를 HTTP 500으로 변환합니다.

## Source Flow

- 단계는 `Fetch -> Entry Lookup -> Enrich -> News Lookup -> Load -> State Write` 순서입니다.
- `Fetch`는 RSS entry를 `NewsModel`로 매핑하고, DTO 검증 실패나 `published_at` 변환 실패 item은 건너뜁니다.
- `Entry Lookup`은 `entry_key`의 Firestore status가 `success`인 item을 제외하고 문서가 없거나 `failed`인 item만 통과시킵니다.
- `Enrich`는 통과 item의 HTML을 병렬 처리해 입력별 결과를 반환합니다. HTTP, parsing, boilerplate, 빈 본문 실패는 phase를 중단하지 않고 `failed` record로 보존합니다.
- Service는 Enrich 결과를 `news_id`로 그룹화해 하나만 남기고 성공 record를 실패 record보다 우선하며, 그룹의 모든 `entry_key`를 상태 기록까지 보존합니다.
- `News Lookup`은 canonical URL로 `news_id`가 바뀐 item만 조회하고, 기존 canonical 성공과 중복이면 load에서 제외합니다.
- canonical 중복으로 제외한 그룹의 모든 `entry_key`는 이미 처리된 URL로 보고 Load 전에 `success` 상태로 기록합니다.
- `Load`는 남은 성공/실패 record를 source별 JSONL에 쓰고 manifest를 마지막에 씁니다. item이 0건이면 data object 없이 `count: 0` manifest만 씁니다.
- `State Write`는 Load가 모두 끝난 뒤 생존 record의 `news_id`와 그룹의 모든 서로 다른 `entry_key`를 생존 status로 덮어씁니다.

## Results And Failure

- source `count`는 phase 예외 없이 실행을 마친 경우 성공/실패를 포함한 JSONL record 수이고, phase 예외로 `failed`가 되면 0입니다. 전체 `count`는 source `count`의 합입니다.
- source 실행이 끝났을 때 load 대상에 `failed` item이 있으면 status는 `partial`, 없으면 `success`입니다.
- phase 예외는 source status를 `failed`로 만들고 현재 phase와 오류를 응답에 남깁니다.
- Load 또는 State Write 실패 시 최종 state가 없는 item은 다음 호출에서 다시 처리될 수 있으며, 이미 올라간 raw object의 중복은 허용합니다.
- `expires_at`은 기록 시각부터 7일 뒤이며 Firestore TTL 활성화 전 상태는 `DEBT.md`에서 추적합니다.
