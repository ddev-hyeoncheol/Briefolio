# Contributing

프로젝트에 기여할 때는 변경 목적을 작게 나누고, 읽기 쉬운 history와 리뷰 가능한 PR을 남깁니다.

## Commit Message Convention

이 저장소는 [Angular Commit Message Guidelines](https://github.com/angular/angular/blob/main/contributing-docs/commit-message-guidelines.md)에서 타입 체계와 구조를 가져온 **simplified local convention**을 사용합니다.

Angular 원문과의 차이:

| 항목    | Angular convention                                                      | 이 저장소                                                                                             |
| ------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Header  | `<type>(<scope>): <short summary>`                                      | `[Type] Subject`                                                                                      |
| Type    | 소문자 `build`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `test` | 대괄호와 PascalCase: `[Build]`, `[CI]`, `[Docs]`, `[Feat]`, `[Fix]`, `[Perf]`, `[Refactor]`, `[Test]` |
| Scope   | 선택 사항                                                               | 사용하지 않음                                                                                         |
| Subject | 명령형 현재시제, 소문자 시작, 마침표 없음                               | 한글로 간결하게 작성                                                                                  |
| Body    | Angular는 `docs` 외에는 body를 요구                                     | 선택 사항이지만, 있으면 변경 이유와 영향을 설명                                                       |
| Footer  | breaking change, deprecation, issue reference                           | 필요할 때만 issue reference, breaking change, deprecation 설명                                        |

즉, 이 저장소의 규칙은 Angular와 **타입 의미와 작성 의도는 비슷하지만 header 형식은 다릅니다.**

## Format

```text
[Type] Subject

- 변경 사항 1
- 변경 사항 2

Footer
```

Header만으로 충분한 작은 변경은 한 줄 commit도 허용합니다.

```text
[Type] Subject
```

## Types

| Type         | 설명                              |
| ------------ | --------------------------------- |
| `[Build]`    | 빌드 시스템 또는 외부 의존성 변경 |
| `[CI]`       | CI/CD 설정 변경                   |
| `[Docs]`     | 문서 변경                         |
| `[Feat]`     | 새로운 기능 추가                  |
| `[Fix]`      | 버그 수정                         |
| `[Perf]`     | 성능 개선                         |
| `[Refactor]` | 기능 변화 없는 리팩토링           |
| `[Test]`     | 테스트 추가 또는 수정             |

## Rules

- Type은 위 목록 중 하나만 사용합니다.
- Subject는 한글로 간결하게 작성합니다.
- Subject는 변경 결과를 한눈에 이해할 수 있게 작성하고, 끝에 마침표를 붙이지 않습니다.
- Body는 선택 사항이며, 필요하면 `- ` 목록으로 작성합니다.
- Body에는 단순 파일 변경보다 변경 이유, 영향, 주요 동작 변화를 우선 적습니다.
- Footer는 관련 issue, breaking change, deprecation을 남길 때만 작성합니다.
- Breaking change는 `BREAKING CHANGE:`로 시작하고, 영향과 migration 방향을 함께 적습니다.
- Deprecation은 `DEPRECATED:`로 시작하고, 권장 대안을 함께 적습니다.
- 커밋은 changelog나 리뷰에서 하나의 의미로 읽을 수 있는 목적 단위로 나눕니다.
- 서로 독립적으로 되돌릴 수 있는 변경은 별도 커밋으로 나눕니다.

## Examples

```text
[Feat] RSS 소스별 GCS 캡처 적재 추가

- source별 `NewsModel`을 JSONL로 직렬화해 GCS에 append-only로 적재
- 캡처마다 manifest JSON을 기록해 빈 실행과 미실행을 구분
- Firestore dedup을 통과한 기사만 enrich 후 적재

Closes #123
```

```text
[Fix] 본문 추출 실패 기사 적재 누락 수정

- HTML enrich에 실패한 기사도 `NewsModel`로 유지해 적재
- 실패 항목의 `status_code`와 오류 메타데이터 기록
```

```text
[Refactor] 뉴스 정규화 책임 분리
```

```text
[Feat] batch API를 단일 ingest 엔드포인트로 통합

- layer/target별 경로를 `POST /ingest/run` 하나로 통합
- 실행 대상은 `ENABLED_SOURCE_CLASSES` 설정으로 결정

BREAKING CHANGE: 기존 `POST /batch/{layer}/{target}` 경로는 제거됩니다.

호출자는 `POST /ingest/run`으로 전환해야 합니다.
```

## Branches And Pull Requests

- 브랜치는 변경 목적이 드러나도록 작게 나눕니다.
- PR은 하나의 리뷰 가능한 목적 단위로 만듭니다.
- PR 설명에는 변경 이유, 주요 변경 사항, 검증 결과를 포함합니다.
