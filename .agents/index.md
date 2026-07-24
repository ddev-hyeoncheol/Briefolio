# Agent Harness Index

현재 작업에 필요한 하네스 문서만 골라 읽기 위한 인덱스입니다.

## Always

항상 다음 파일을 읽습니다.

- `.agents/rules/core.md`

## Workflows

리뷰 요청이면 다음 파일을 읽습니다.

- `.agents/workflows/review.md`

동작 변경 없는 코드 구조 개선이나 청소이면 다음 파일을 읽습니다.

- `.agents/workflows/refactor.md`

리팩토링이 파일 수정을 포함하면 다음 파일도 함께 읽습니다.

- `.agents/workflows/implement.md`

기능 추가, 버그 수정, 문서 변경처럼 동작이나 산출물이 바뀌는 작업이면 다음 파일을 읽습니다.

- `.agents/workflows/implement.md`

## Guides

새 뉴스 source 추가이면 다음 파일을 읽습니다.

- `.agents/guides/news-source.md`

## Context

현재 포커스, 임시 결정 등 동적 상태가 작업 결과에 직접 영향을 주는 경우 다음 파일을 읽습니다.

- `MEMORY.md`

기술 부채 파악 및 아키텍처 리팩토링 검토 시 다음 파일을 읽습니다.

- `DEBT.md`
- `TRANSITION.md`

## Domain Rules

아키텍처, 레이어 책임, API, Provider 변경이면 다음 파일을 읽습니다.

- `.agents/rules/architecture.md`

Ingest pipeline, dedup, count, 실패 전파 변경이면 다음 파일을 읽습니다.

- `.agents/rules/pipeline.md`

Entity, Schema, Firestore 문서, Terraform, field description 변경이면 다음 파일을 읽습니다.

- `.agents/rules/data-contract.md`

## Cross-Cutting Rules

import, method order, docstring, comment, logging 변경이면 다음 파일을 읽습니다.

- `.agents/rules/style.md`

## Special Rules

하네스 문서 추가/수정/리뷰/검토이면 다음 파일을 읽습니다.

- `.agents/rules/harness-doc.md`

commit 요청이면 다음 파일을 읽습니다.

- `.agents/rules/commit.md`
