# Working Memory

이 파일은 에이전트가 다음 작업에서도 기억하면 좋은 현재 상태와 임시 합의를 담습니다.

- 현재 작업 초점은 Ingest 계층 분리입니다.
- `src/worker/`는 `src/ingest/`로 이동했고 Dockerfile과 Cloud Build 실행 경로도 전환했습니다.
- 기존 `src/api/` placeholder는 삭제했으며 Serving package는 Serving 구현 시점에 만듭니다.
- Cloud Run Ingest는 인증을 필수화했고, Cloud Scheduler OIDC와 `roles/run.invoker` 구성은 Terraform 작업에 남아 있습니다.
- `style.md`의 Logging 섹션은 비워둠 — 로깅 규칙을 다른 형식으로 재작성 예정.
