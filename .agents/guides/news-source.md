# News Source Guide

새 RSS 기반 뉴스 source를 추가할 때 참고하는 가이드입니다.

## Procedure

1. `.agents/specs/architecture.md`, `.agents/specs/pipeline.md`, `.agents/specs/data-contract.md`를 함께 적용합니다.
2. 수집 샘플을 `docs/feed_samples/{source}.json`에 남기고 각 `feedparser_entry`의 top-level 필드를 확인합니다.
3. Firestore와 raw JSONL에 남을 `source`를 안정적인 lower_snake_case 식별자로 정합니다.
4. `src/ingest/models/sources/`에 RSS entry DTO를 추가하고 저장할 필드와 metadata 필드만 선언합니다.
5. `src/ingest/plugins/sources/`에 `RssPlugin` 구현체를 추가해 `source`, `rss_url`, `run_fetch()`를 정의합니다.
6. 관측된 필드를 `rss_entry_storage_fields`, `rss_entry_metadata_fields`, `rss_entry_ignored_fields` 중 정확히 하나로 분류합니다.
7. `run_fetch(executed_at)`는 `_fetch_feed()` 결과를 DTO로 검증하고 `NewsModel`로 매핑하며, 검증 또는 날짜 변환 실패 entry는 건너뜁니다.
8. source 부가 값은 DTO의 storage 필드를 제외한 JSON dump로 `metadata`에 저장합니다.
9. `entry_key`와 `news_id`는 `NewsModel`이 URL에서 유도하므로 source에서 생성하지 않습니다.
10. 반복되는 비본문은 `boilerplate_contents`에 diagnostic key와 exact content로 등록합니다.
11. 구현 검증 후 `src/ingest/dependencies.py`의 `ENABLED_SOURCE_CLASSES`에 배포할 source만 등록합니다.

## Boundaries

- 새 source 추가만으로 API 형태를 늘리지 않습니다. `POST /ingest/run`은 등록된 모든 source를 실행합니다.
- `RssPlugin.run_fetch()`에는 요청 DTO 대신 `executed_at: datetime`만 넘깁니다.
- `_fetch_feed()`, 공통 enrich, retry, semaphore 로직은 base `RssPlugin`을 재사용하고 source에는 parsing 차이만 둡니다.
- `RssPlugin.run_enrich()`는 입력별 결과를 반환하고, `news_id` 중복 축약과 alias `entry_key` 보존은 Service가 담당합니다.
- `NewsModel`이나 Firestore 계약 변경은 기존 공통 필드와 `metadata`로 표현할 수 없을 때만 검토합니다.
- 기존 source의 `source` 식별자는 Firestore와 raw JSONL 계약에 남으므로 rename하지 않습니다.
- 두 번째 source를 활성화하기 전에는 `DEBT.md`의 교차 source `news_id` dedup race 해소 여부를 확인합니다.

## Validation

- sample의 `feedparser_entry` 필드가 세 필드 집합 중 하나에 모두 포함되고 집합 간 중복이 없는지 확인합니다.
- source DTO 검증, `NewsModel` 매핑, 날짜 변환과 이미지 매핑을 sample 기준으로 확인합니다.
- source 구현체와 DTO를 compile/import하고 `ENABLED_SOURCE_CLASSES` 등록 여부를 확인합니다.
