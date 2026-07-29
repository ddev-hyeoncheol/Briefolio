# Commit Rules

## Scope

- 이 파일은 stage 안전과 에이전트 전용 메시지 규칙을 정의합니다.
- 커밋 메시지 형식은 `CONTRIBUTING.md`의 `Commit Message Convention`을 따릅니다.
- 커밋 실행 권한과 git 안전 규칙은 `.agents/core.md`를 따릅니다.

## Checks

- **[CRITICAL]** 사용자 요청 범위 밖의 변경은 커밋 대상에 포함하지 않으며, 이미 stage되어 있으면 커밋을 중단하고 사용자에게 확인합니다.
- 커밋 전 `git status --short`를 확인합니다.
- 요청 범위 파일만 stage하고, 전체 worktree를 일괄 stage하지 않습니다.
- stage된 파일이 사용자 요청의 목적 단위와 일치하는지 staged diff로 확인합니다.
- 커밋 메시지에 `Co-Authored-By`를 포함하지 않습니다.
- `git commit -m`을 여러 번 사용할 때 각 `-m`은 별도 단락(Paragraph)이 되므로, 본문의 불릿 리스트(Bullet List)는 반드시 하나의 `-m` 블록 안에 묶어서 작성합니다.
