# Comments Rules

## General

- 영어로 작성하고, 코드로 드러나는 내용은 반복하지 않습니다.
- 보장하지 않는 동작은 설명하지 않습니다.
- TODO comment는 이유와 방향을 함께 포함합니다.

## Python Files

- 함수와 메서드에는 `Return ...`, `Fetch ...`, `Upload ...`처럼 imperative mood의 docstring을 작성합니다.
- 클래스 docstring은 객체의 책임을 설명합니다.
- 분기·변환·예외 처리가 없는 생성자·property override·private helper에는 docstring을 생략합니다.
- Pydantic `Field(description=...)`는 단일 문장으로 작성하고, 같은 스키마·파일 안에서 표현을 일관되게 유지합니다.
- description은 필드를 채우는 코드와 대조해 출처·정규화·fallback·집계·phase 실패 의미를 현재 동작대로 반영합니다.
- inline comment는 event loop semaphore, retry, 중복 즉시 기록, 매니페스트 기록 순서처럼 필요한 이유나 외부 제약을 설명할 때만 둡니다.

## Non-Python Config Files

- Terraform/Docker/YAML 같은 설정 파일의 주석은 설정만으로 드러나지 않는 목적이나 외부 제약을 설명합니다.
