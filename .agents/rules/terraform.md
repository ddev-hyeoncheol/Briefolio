# Terraform Rules

## Root And Provider

- 새 리소스는 `terraform/{ingest,intelligence,serving}/`의 독립 root에만 추가하고, `terraform/` 아래 레거시는 확장하지 않습니다.
- 각 root의 `main.tf`에 Terraform·Provider·backend·locals·variables를 함께 두고, output 소비자가 없으면 `outputs.tf`를 만들지 않습니다.
- `required_version = ">= 1.7, < 2.0"`, Google Provider `~> 5.0`, 현재 lock `5.45.2`를 root 간 동일하게 유지합니다. `init -reconfigure`는 backend 재설정에만 쓰고 버전 업그레이드로 간주하지 않으며, lock 파일은 직접 수정하지 않습니다.
- 세 root는 `briefolio-tfstate`를 공유하고 backend prefix를 `service_name`과 동일하게 분리합니다.
- `project_id`와 `region`은 소유 범위를 설명하는 description, 유효한 default, `nullable = false`를 갖습니다.
- Seed project와 state bucket은 Terraform 외부의 일회성 bootstrap 대상으로 유지하고 Terraform resource로 중복 선언하지 않습니다.

## Naming And Layout

- `service_name`은 root 경계 이름이며 HCL 이름에서 제외하고 purpose 기반 snake_case를 사용합니다.
- API resource HCL 이름은 service 첫 라벨, 프로젝트 범위 이름은 `{service_name}-{purpose}`, 전역 이름은 `{project_id}-{purpose}`를 사용합니다.
- Service Account는 purpose HCL 이름, `{service_name}-{purpose}` account ID, `Briefolio {Service} {Purpose}` display name을 사용하고 계약 없는 description은 생략합니다.
- 리소스 파일은 GCP 서비스명을 kebab-case로 쓰고, root 설정은 `main.tf`, API는 `apis.tf`, identity와 grant는 `iam.tf`에 둡니다.
- 일반 resource 인자는 식별자 → scope(`project`·`region`·`location`) → 핵심 동작 → nested block → `lifecycle` → `depends_on` 순서로 배열합니다.
- `_iam_member`는 scope(`project`·`location`) → 대상 식별자 → `role` → `member` 순서를 사용합니다.

## Values And Dependencies

- **[CRITICAL]** Cloud Run container에 `resources` 블록을 두면 request-based billing 유지를 위해 `cpu_idle = true`를 명시합니다.
- 일반 리소스의 `project`는 Provider에서 상속하고, project IAM처럼 정책 대상을 지정하는 리소스에만 명시합니다.
- 지역 리소스는 Provider마다 요구하는 `region`, `location`, `location_id`에 `var.region`을 명시합니다.
- 미명시와 명시 기본값의 결과가 같으면 생략하고, 미명시가 비용·보안·삭제·bootstrap·외부 소유 계약을 바꾸거나 상위 block 유무로 기본값이 달라지는 값은 명시합니다.
- Artifact Registry 최신 3개 보존, GCS 7일 soft delete, Firestore TTL, Cloud Run `min_instance_count = 0`는 기본값과 같아도 비용·보존 의도로 유지합니다.
- resource attribute 참조로 의존성을 만들고, 참조가 없는 API 활성화 순서에만 `depends_on`을 사용합니다.
- root가 직접 사용하는 API만 `apis.tf`에서 관리합니다.

## Ownership And Contracts

- 코드와 state에 연결된 managed resource만 Terraform이 소유하며, 코드 제거는 plan의 destroy와 실제 GCP 삭제로 이어집니다.
- `ignore_changes` 속성은 Terraform 소유가 아니므로 외부 갱신 주체를 코드와 전환 명세에 기록합니다.
- Cloud Run은 bootstrap image로 생성하고 이후 image와 gcloud 배포 client metadata는 Cloud Build가 소유하며, Scheduler는 paused로 생성하고 이후 pause·resume은 운영자가 소유합니다.
- GitHub connection과 repository는 사용자가 연결하고 Terraform은 전체 resource name을 입력받아 trigger만 소유합니다.
- Trigger custom substitutions는 `cloudbuild.yaml` 사용처와 일대일로 맞추며, build arg·runtime env로 명시하지 않은 substitution은 애플리케이션에 전달된다고 간주하지 않습니다.
- runtime 환경 변수와 Firestore collection 같은 실제 GCP 식별자는 resource attribute 또는 애플리케이션 상수와 대조하며 HCL label을 실제 이름으로 간주하지 않습니다.

## IAM

- **[CRITICAL]** `_iam_policy`는 정책 전체와 Google service agent를 포함한 모든 binding·audit config를 Terraform이 소유하기로 선택한 경우에만 사용합니다.
- **[CRITICAL]** IAM 변경 plan에서 policy, role, principal, 대상 범위와 Google service agent 영향을 확인해 보고합니다.
- 개별 grant는 `_iam_member`로 선언하고 repository·service·Service Account·bucket 등 가능한 가장 좁은 범위에 부여합니다. `_iam_binding`은 해당 role의 전체 principal 목록을 소유할 때만 사용합니다.
- Service Account는 build·runtime·scheduler처럼 실행 목적별로 분리하고 소비 리소스가 email·id·name을 직접 참조합니다.
- 같은 policy에서 `_iam_policy`와 member·binding·audit config를 혼용하지 않고, 같은 role에 `_iam_binding`과 `_iam_member`를 혼용하지 않습니다.

## State And Deletion

- **[CRITICAL]** 데이터 삭제·교체 plan은 정확한 리소스와 보존 데이터 영향을 확인해 보고합니다.
- `state list`·`state show`로 주소와 GCP ID를 확인합니다. 편입은 `import`, 주소 변경은 `moved`, 소유권 포기는 `removed`의 `lifecycle.destroy = false` 또는 Provider의 ABANDON 정책으로 선언합니다.
- 삭제 보호 리소스는 보호 해제 plan과 사용자 apply 완료를 먼저 확인한 뒤 제거 plan을 검증합니다. 코드 제거가 destroy로 나타나지 않으면 apply 명령을 안내하지 않습니다.
- `force_destroy`, deletion policy, deletion protection, API `disable_on_destroy`를 명시하며 `prevent_destroy`를 GCP 데이터 보호 수단으로 간주하지 않습니다.

## Execution And Review

- **[CRITICAL]** 에이전트는 apply·destroy·refresh·CLI import·state 변경·force-unlock의 승인도 요청하지 않고 실행하지 않습니다.
- 에이전트는 fmt·validate·refresh 포함 plan·read-only state 조회까지 수행하고 결과와 사용자가 직접 실행할 명령만 안내합니다.
- 여러 파일은 서비스 계약·소유권 → 데이터 삭제·보안·비용 → IAM·API·의존성 → 이름·scope → 인자 배열·주석·기본값 → plan·state 순서로 가로 검토합니다.
