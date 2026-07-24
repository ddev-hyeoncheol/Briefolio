# Refactor Workflow

구조 개선, 책임 분리, 이름 정리처럼 기존 동작을 보존하는 리팩토링에 사용합니다.

## Default Order

넓은 범위의 리팩토링은 낮은 계층에서 높은 계층으로 진행합니다.

1. Entity
2. Schema
3. Core / Config
4. Provider
5. Source
6. Service
7. Router / Entry
8. Infra / Docs

## Procedure

1. 요청이 파일 단위, 레이어 단위, 계약 변경 포함 작업인지 구분합니다.
2. 파일 단위 요청이면 파일 경계를 우선하고 현재 diff와 필요한 계약 파일만 확인합니다.
3. `.agents/index.md`에서 필요한 workflow, rule, guide를 추가로 선택합니다.
4. 하위 레이어 계약을 바꾸면 영향을 받는 상위 레이어만 순서대로 갱신합니다.
5. 기존 동작을 보존하되, 계약 변경이 필요하면 사용자 요청과 선택한 rules를 우선합니다.
6. 넓은 검증 전에 변경한 레이어에 맞는 집중 검증을 실행합니다.

## Boundaries

- 현재 리팩토링 목표는 workflow에 고정하지 않고 선택한 rules나 `MEMORY.md`에서 관리합니다.
- Batch pipeline, target, 데이터 계약, logging, import 순서 같은 세부 제약은 각 rules 파일을 따릅니다.
- 리팩토링 중 발견한 별도 개선은 요청 범위 밖이면 기록만 남기고 같은 변경에 섞지 않습니다.
