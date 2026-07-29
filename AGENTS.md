# Agent Harness Entry Point

## Load Order

1. `.agents/core.md`
2. `.agents/index.md`
3. `.agents/index.md`가 선택한 파일

## Guardrail

- **[CRITICAL]** 최초 분석·도구 실행·파일 수정 전에 `.agents/core.md`와 `.agents/index.md`를 `[Harness]`로 가장 먼저 출력합니다.
- `.agents/index.md` 확인 후 추가로 읽을 파일이 있으면 읽기 전에 `[Harness]`로 추가 출력합니다.
- 출력은 `[Harness]` 제목과 실제 읽을 파일의 저장소 기준 상대 경로의 `- ` 목록으로 작성합니다.
- 매 요청(새 메시지·대화 턴)마다 이전에 읽었더라도 하네스를 다시 로드합니다.
