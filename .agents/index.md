# Agent Harness Index

## Workflows

- 리뷰 요청이면 `.agents/workflows/review.md`를 읽습니다.
- 기능 추가·버그 수정·리팩토링·문서 변경처럼 파일을 수정하는 작업이면 `.agents/workflows/implement.md`를 읽습니다.

## Context

- 현재 포커스·임시 결정 등 동적 상태가 작업에 직접 영향을 주면 `MEMORY.md`를 읽습니다.
- 기술 부채가 작업 대상이면 `DEBT.md`를 읽습니다.
- 진행 중인 아키텍처 전환이나 로드맵이 작업 대상이면 `TRANSITION.md`를 읽습니다.

## Domain Spec

- 아키텍처·레이어 책임·API·Provider 중 하나가 작업 대상이면 `.agents/specs/architecture.md`를 읽습니다.
- Ingest pipeline·dedup·count·실패 전파 중 하나가 작업 대상이면 `.agents/specs/pipeline.md`를 읽습니다.
- Entity·Schema·raw JSONL·Firestore 문서·field description 중 하나가 작업 대상이면 `.agents/specs/data-contract.md`를 읽습니다.

## Cross-Cutting Rules

- Python import·naming·멤버 순서 중 하나가 작업 대상이면 `.agents/rules/style.md`를 읽습니다.
- docstring·comment·Field description 중 하나가 작업 대상이면 `.agents/rules/comments.md`를 읽습니다.

## Guides

- 새 뉴스 source 추가이면 `.agents/guides/news-source.md`를 읽습니다.

## Special Rules

- 하네스 문서가 작업 대상이면 `.agents/rules/harness-doc.md`를 읽습니다.
- commit 요청이면 `.agents/rules/commit.md`를 읽습니다.
- branch·pull request가 작업 대상이면 `CONTRIBUTING.md`를 읽습니다.
