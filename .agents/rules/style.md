# Style Rules

import, method order, docstring, comment, logging 스타일 계약을 정의합니다.

## Imports

- import는 PEP 8 구분을 따라 Python standard library, third-party package, first-party `src.*` 순서로 둡니다.
- 각 그룹 사이에는 빈 줄 하나만 둡니다.
- 그룹 내부는 isort 기본 정렬처럼 알파벳순으로 정렬하고, plain `import ...`를 먼저 둔 뒤 `from ... import ...`를 빈 줄 없이 둡니다.
- `TYPE_CHECKING`은 순환 import를 피해야 할 때만 사용합니다.
- 수정하는 파일의 import는 새 규칙에 맞추고, 관련 없는 파일의 import churn은 만들지 않습니다.

## Naming And Order

- `RssSource` 공개 phase 메서드는 `run_fetch`, `run_enrich`처럼 orchestration 단계를 드러냅니다.
- helper 이름은 반환값, 처리 대상, 외부 호출 목적을 드러냅니다.
- 모델/문서 payload 생성 helper는 `_create_state_doc`처럼 산출물 이름을 포함합니다.
- Provider는 public metadata property, `__init__`, public external-call method, private helper 순서로 둡니다.
- Plugin은 필요한 property, `__init__`, public phase method, private orchestration/helper, mapping/model creation helper 순서로 둡니다.
- Service는 public `run_*()`, private pipeline step, response/payload helper, module-level dependency factory 순서로 둡니다.
- 같은 개념의 메서드는 같은 동사와 명사 구조를 유지합니다.
- 함수 인자는 가능한 한 구체적인 Entity 또는 Schema 타입으로 명시합니다.

## Documentation And Comments

- 코드 주석, docstring, Pydantic `Field(description=...)`은 영어로 작성합니다.
- 설명은 짧고 구체적으로 쓰고, 코드가 보장하지 않는 동작을 설명하지 않습니다.
- 함수와 메서드 docstring은 `Return ...`, `Fetch ...`, `Upload ...`처럼 imperative mood를 사용합니다.
- 클래스 docstring은 객체의 책임을 설명합니다.
- inline comment는 event loop semaphore, retry, 중복 즉시 기록, 매니페스트 기록 순서처럼 필요한 이유나 외부 제약을 설명할 때만 둡니다.
- TODO comment는 이유와 방향을 함께 포함합니다.

## Logging

- 애플리케이션 로그 메시지는 영어로 작성합니다.
- 런타임 코드는 `logger`를 사용하고 `print()`를 사용하지 않습니다.
- 기본 형식은 `<Component> <operation> [scope] <outcome> | key: value, key: value`입니다.
- source, collection, bucket은 `[]` prefix가 아니라 key-value 필드로 기록합니다.
- Component는 `IngestRouter`, `IngestService`, `RssSource`, `FirestoreProvider`, `CloudStorageProvider`처럼 책임 단위를 드러냅니다.
- item/chunk 단위 실패에는 scope를 쓰고, method 전체 실패에는 scope를 쓰지 않습니다.
- `logger.exception`은 stack trace가 필요한 phase/method 실패에만 사용합니다.
- 자주 쓰는 필드는 `endpoint`, `executed_at`, `source`, `collection`, `lookup_key`, `news_id`, `run_id`, `bucket`, `path`, `count`, `*_count`, `reason`, `error`, `status`, `status_code`, `failed_phase`, `elapsed`입니다.

예시는 다음 로그 형식을 따릅니다.

```text
IngestRouter ingest completed | endpoint: ingest/run, status: success
IngestService filter_retryable completed | lookup_key: entry_key, count: 20, retryable_count: 3
RssSource enrich completed | source: yahoo_finance, count: 3, success_count: 3, failed_count: 0
```
