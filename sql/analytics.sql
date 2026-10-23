-- TASK 1

WITH cte AS (
            SELECT
                category 
                , ROUND(AVG(price_actual), 2) AS avg_price
                , PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_actual) AS median_price
            FROM product
            GROUP BY 1
            ), cte2 AS (
                SELECT 
                    item_id 
                    , name
                    , brand
                    , t1.category
                    , price_actual
                    , ft.avg_price
                    , ft.median_price
                    , ROUND((price_actual - avg_price) / avg_price * 100, 2) AS deviation_price
                    , PERCENT_RANK() OVER (PARTITION BY t1.category ORDER BY price_actual DESC) AS p_rank
                FROM product AS t1
                LEFT JOIN cte AS ft 
                    ON t1.category = ft.category
                ) 
                    SELECT
                        *
                        , CASE 
                            WHEN p_rank <= '0.20' THEN 'premium'
                            WHEN p_rank <= '0.50' THEN 'middle'
                            ELSE 'budget'
                        END AS segment
                    FROM cte2;

-- 2 TASK

WITH cte AS (
            SELECT
                category
                , brand
                , SUM(review_count) AS review_brand   -- Кол-во отзывов
                , ROUND(SUM(COALESCE(review_count * recommended / 100.0, 0))) AS recommend_brand -- Кол-во рекомендаций
                , COUNT(item_id) AS total_product -- Кол-во продуктов
                , ROUND(AVG(price_actual), 2) AS avg_price_brand -- Средняя цена бреда
            FROM product
            GROUP BY 1, 2
        ), cte2 AS (       
                SELECT 
                    *
                    , ROW_NUMBER() OVER (PARTITION BY category ORDER BY avg_price_brand DESC) AS rank_price
                FROM cte
                WHERE TRUE
                    and review_brand >= (
                                    SELECT 
                                        AVG(review_count)
                                    FROM product
                                    )
                )
                    SELECT 
                        *
                    FROM cte2 
                    WHERE TRUE
                        and rank_price <= 3

-- TASK 3 
WITH cte AS (
        SELECT 
            category,
            COUNT(item_id) FILTER (WHERE review_count = 0 or review_count is NULL) as not_reviewed_sku,
            COUNT(DISTINCT item_id) as sku_count, 
            COUNT(item_id) FILTER (WHERE review_count > 0) as reviewed_sku,
            SUM(COALESCE(review_count, 0)) as total_reviews,
            AVG(price_actual) as avg_price
        FROM product 
        WHERE TRUE 
        GROUP BY 1  
        )
        SELECT 
            category,
            sku_count,
            not_reviewed_sku,
            reviewed_sku,
            total_reviews,
            avg_price,
            ROUND((reviewed_sku * 1.0 / sku_count) * 100, 2) as reviewed_share_pct
        FROM cte 
        LIMIT 3

-- TASK 4 

WITH cte AS (
        SELECT 
            category,
            brand,
            COUNT(DISTINCT item_id) AS sku_count,
            SUM(review_count) AS total_review, 
            ROUND(AVG(price_actual), 2) AS avg_price
        FROM product
        GROUP BY 1, 2
        ), 
        cte2 AS (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY category ORDER BY total_review DESC) as brand_rank
        FROM cte 
        WHERE TRUE
        AND sku_count >= 3
        AND total_review >= 100
        )
        SELECT 
            *
        FROM cte2
        WHERE brand_rank <= 3
        ORDER BY category DESC, brand_rank ASC

-- TASK 5

WITH cte AS (
        SELECT
            pd.item_id,
            pd.name,
            pd.category, 
            CASE WHEN pf.item_id is not null THEN 1 ELSE 0 END AS in_perfume,
            CASE WHEN sk.item_id is not null THEN 1 ELSE 0 END AS in_skincare,
            CASE WHEN sp.item_id is not null THEN 1 ELSE 0 END AS in_supplement
        FROM product AS pd
            LEFT JOIN perfume AS pf 
                on pd.item_id = pf.item_id
            LEFT JOIN skincare AS sk 
                on pd.item_id = sk.item_id
            LEFT JOIN supplement AS sp 
                on pd.item_id = sp.item_id 
        )
        SELECT
            item_id,
            name,
            category,
            in_perfume,
            in_skincare,
            in_supplement,
            in_perfume + in_skincare + in_supplement AS subtype_count
        FROM cte 
        WHERE in_perfume + in_skincare + in_supplement >= 2
        """
