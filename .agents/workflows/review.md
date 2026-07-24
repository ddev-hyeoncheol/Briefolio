# Review Workflow

사용자가 리뷰를 요청하면 파일 수정 없이 리뷰 대상의 성격에 맞춰 findings 우선으로 응답합니다.

## Output Order

- 지적 사항을 먼저 제시하고 심각도 순서로 정렬합니다.
- 각 지적 사항은 파일과 줄 번호, 실제 영향에 근거합니다.
- 문제가 없으면 명확히 말하고 남은 테스트 공백이나 잔여 위험을 언급합니다.
- 요약, 질문, 변경 제안은 지적 사항 뒤에만 둡니다.

## Procedure

1. 파일 단위 리뷰는 대상 파일을 중심으로 하고, 인접 파일은 계약 확인에 필요한 범위에서만 읽습니다.
2. 리뷰 대상의 현재 파일과 diff를 확인합니다.
3. `.agents/index.md`에서 대상 변경에 맞는 domain rules와 cross-cutting rules를 추가로 선택합니다.
4. 버그, 동작 회귀, 데이터 손실, 책임 경계 위반, 위험한 모호성을 먼저 찾습니다.
5. 하네스 문서 리뷰는 `.agents/rules/harness-doc.md`의 File Roles, Size & Duplication, Writing Style & Severity를 확인합니다.
6. 코드 리뷰는 선택한 rules 파일 중 영향받은 항목만 확인합니다.
7. compile, import, test 검증 여부가 변경 위험도와 맞는지 확인합니다.

## Boundaries

- **[CRITICAL]** 리뷰 중 파일을 수정하지 않습니다. 사용자가 수정까지 요청하면 implement workflow로 전환합니다.
- 세부 규칙은 이 파일에 반복하지 않고 관련 rules 파일을 근거로 삼습니다.
- 테스트 누락은 구체적 동작 위험이 있으면 지적 사항으로, 단순 미실행이면 잔여 위험으로 적습니다.
- 선택한 rules 파일의 섹션은 경중 없이 동일한 깊이로 확인하고, 특정 섹션만 가볍게 다루지 않습니다.
