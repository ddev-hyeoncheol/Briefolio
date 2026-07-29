# Harness Documentation Rules

## File Roles

- `AGENTS.md`: 하네스의 논리적 진입점. 매 턴 읽을 파일·순서와 `[Harness]` 출력 규칙을 안내합니다.
- `CLAUDE.md`: Claude Code가 세션 시작 시 자동 로드하는 물리적 진입점. `AGENTS.md`만 import하며 규칙을 직접 정의하지 않습니다.
- `.agents/core.md`: 모든 작업에 항상 적용되는 최상위 행동 규칙. `.agents/index.md`와 함께 매 턴 무조건 읽습니다.
- `.agents/index.md`: 트리거 조건 기반의 작업별 라우터. 라우팅만 담습니다.
- `.agents/rules/`: 영구적 제약 조건(Constraints) 보관.
- `.agents/specs/`: 현재 프로젝트의 아키텍처와 동작을 서술하는 명세(Spec) 보관. 서술 대상이 바뀌면 함께 갱신합니다.
- `.agents/workflows/`: 순서가 중요한 작업 절차(Process) 보관.
- `.agents/guides/`: 도메인 고유의 컴포넌트 확장 지침(Guide) 보관.
- `MEMORY.md`: 현재 포커스, 임시 결정 등 동적 상태(State) 보관.
- `DEBT.md`: 장기 기술 부채 대장 보관.
- `TRANSITION.md`: 진행 중인 아키텍처 전환 계획과 단계별 로드맵 보관. 전환이 끝나면 제거하는 한시적 문서.
- `CONTRIBUTING.md`: 사람과 AI 공통 기여 규칙의 Canonical 원본.

## Writing Style

- Markdown 제목 헤더(`#`, `##` 등)는 영어로 쓰고, 본문 설명은 한국어로 작성합니다.
- `##` 섹션의 내용은 bullet으로 작성하고, 부연은 하위 bullet에 둡니다. 구조 비교는 표, 순서가 있는 절차는 번호 목록, 명령이나 예시는 코드 블록을 사용할 수 있습니다.
- 누적 문서가 기본 bullet과 다른 항목 형식을 쓰면, 빈 상태에도 해당 형식의 예시 블록을 둡니다.
- 규칙의 판단 기준은 `관련`, `적절히`처럼 해석이 갈리는 표현 대신, 기계적으로 확인 가능한 구체적 대상이나 조건으로 작성합니다.
- 규칙은 명령문(~하십시오)이 아닌 단호한 규정문(~합니다, ~지킵니다)으로 작성합니다.
- 데이터 유실, 보안 취약점, 비용 급증, 사용자 변경 훼손 위험이 있는 규칙에만 **[CRITICAL]** 태그를 붙입니다.
- 같은 섹션 안에서는 **[CRITICAL]** bullet을 가장 먼저 둡니다.
- 중복 작성하지 않습니다. 타 파일 규칙은 링크나 포인터로만 참조합니다.

## Maintenance

- 파일명·규칙명 변경 시 전역 검색을 수행하여 고아 참조(Stale Reference)를 제거합니다.
- 하네스 문서를 추가·삭제·이동하면 `.agents/index.md` 라우팅을 갱신합니다. 진입점이나 분류 체계가 바뀌면 File Roles도 갱신합니다.
- 개별 core/rule/spec/workflow/guide 파일은 60줄 이하로 유지합니다. 초과 시 역할 기준으로 분리합니다. (`index.md`는 라우터 카테고리라 이 상한 적용 대상이 아닙니다.)
- 파일의 분류(rule/spec/workflow/guide)가 바뀌면 제목도 그 분류에 맞게 갱신합니다.
