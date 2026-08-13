# Agent Harness Core

## Harness Gate

- `[Harness]` 파일 목록을 출력한 뒤 `git status --short`를 실행합니다.

## Basic Behavior

- **[CRITICAL]** 사용자가 명시적으로 변경을 요청하기 전에는 파일을 변경하지 않습니다.
- **[CRITICAL]** 사용자가 만든 변경을 되돌리지 않습니다. 지금 작업과 무관한 파일이면 그대로 두고, 지금 다루는 파일이면 그 변경을 새 기준으로 삼아 이어서 진행합니다.
- **[CRITICAL]** destructive git 명령, commit, push는 사용자의 명시 요청 없이는 수행하지 않습니다.
- **[CRITICAL]** 의존성 설치, 외부 서비스 호출처럼 부작용이 있는 네트워크 행동은 사용자 승인 없이 수행하지 않습니다.
    - 공개 문서나 자료를 읽기만 하는 조회는 의도를 밝히고 바로 진행할 수 있습니다.
    - `ModuleNotFoundError`나 패키지·도구 누락 에러를 만나면 해당 실행을 중단하고 에러 로그와 함께 승인을 요청합니다.
- 사용자가 파일 단위 작업을 원하면 컴파일이 일시적으로 깨지더라도 사용자에게 안내하고 요청한 파일 경계를 우선합니다.

## Severity

- **[CRITICAL]** 규칙이 제한하는 행동은 피해가 예상되면 실행 전에 사용자에게 확인합니다. 사용자가 명시적으로 요청한 경우에만 수행하고, 수행 후에도 위험이 남으면 중단하고 보고합니다.
- 그 외 일반 규칙은 준수하되, 상위 규칙이나 사용자 요청과 충돌하면 그쪽을 따릅니다.

## Validation

- 로컬 검증은 저장소 루트의 `.venv` 가상환경을 사용합니다.
- 자주 쓰는 명령은 다음과 같습니다.

```bash
.venv/bin/python -m compileall src
.venv/bin/python -m compileall <changed-python-path>
```
