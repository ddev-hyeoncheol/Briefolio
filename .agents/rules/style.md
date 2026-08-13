# Python Style Rules

## Imports

- import는 isort 기본 정렬을 따르며 standard library, third-party, first-party `src.*` 그룹을 빈 줄 하나로 구분합니다.
- 수정한 파일의 import만 이 규칙에 맞추고, 범위 밖 파일의 import 정리만을 위한 변경은 만들지 않습니다.

## Naming And Order

- 공개 orchestration 메서드는 단일 진입점이면 `run()`, 여러 단계이면 `run_<phase>()`로 이름을 짓습니다.
- helper는 `<verb>_<target>` 구조로 책임과 대상을 드러내고, 같은 역할에는 같은 동사를 사용합니다.
- payload 생성 helper는 `_create_<artifact>()`로 이름을 짓습니다.
- Provider·Plugin·Service 멤버는 public property, `__init__`, public method, private method 순서로 둡니다.
- module-level dependency factory는 대상 클래스 뒤에 둡니다.

## Logging
