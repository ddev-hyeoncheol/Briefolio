# Legacy: BigQuery 기반 Bronze/Silver 로직

TRANSITION.md Phase 1/2에서 Bronze는 GCS+Firestore로, Silver 생성은 Dataform SQL로 이전되면서 삭제된 Python 코드의 원본 로직입니다. Dataform SQL 작성 시 참고용이며, 실행되지 않습니다.

## Bronze 조회 쿼리 (`BronzeStore`, 삭제됨)

`extract_bronze_news`:

```sql
SELECT * FROM `bronze.news` WHERE executed_at = @executed_at
```

`lookup_bronze_news` — `entry_id` 또는 `news_id`를 lookup_key로 받아 최근 7일 윈도우에서 키별 최신 status를 조회:

```sql
SELECT
    {lookup_key}, status AS latest_status
FROM (
    SELECT
        {lookup_key}, status,
        ROW_NUMBER() OVER (PARTITION BY {lookup_key} ORDER BY executed_at DESC) AS rn
    FROM `bronze.news`
    WHERE executed_at >= TIMESTAMP_SUB(@executed_at, INTERVAL 7 DAY)
        AND {lookup_key} IN UNNEST(@lookup_values)
)
WHERE rn = 1
```

필터 조건: 조회 결과에 lookup_value가 없거나 최신 status가 `failed`이면 재수집 대상으로 통과. Firestore 마이그레이션(TRANSITION.md 3.1)이 그대로 승계해야 하는 정책입니다.

## Silver 적재 패턴 (`SilverStore.load_silver_news`, 삭제됨)

같은 `executed_at` 배치를 먼저 삭제한 뒤 재적재하는 방식으로 멱등성을 확보했습니다.

```sql
DELETE FROM `silver.news` WHERE executed_at = @executed_at
```

삭제 후 남은 `items`를 JSON load job으로 적재. `items`가 비어도 삭제는 수행.

## Bronze → Silver 변환 규칙 (`SilverNewsModel.from_bronze_news`, 삭제됨)

- `bronze_news.status == "success"`이고 `bronze_news.content is not None`인 row만 통과.
- 대표 URL은 `bronze_news.canonical_url or bronze_news.entry_url`.
- 필드 매핑: `raw_authors = bronze_news.authors`, `raw_content = bronze_news.content`, 나머지는 동일 이름으로 매핑.

Dataform SQL(TRANSITION.md 4.4)의 `WHERE status = 'success' AND content IS NOT NULL` 필터가 이 규칙을 승계합니다.
