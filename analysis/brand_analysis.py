import copy
import pandas as pd
import matplotlib.pyplot as plt
import psycopg


with psycopg.connect(
    dbname="goldapple_pet",
    user="postgres",
    host="127.0.0.1",
    port=5432
) as conn:

    df_product = pd.read_sql_query(
        "SELECT * FROM product",
        conn
    )

    df_sk = pd.read_sql_query(
        "SELECT * FROM skincare",
        conn
    )


df_skincare = df_product.merge(
    df_sk,
    on="item_id",
    how="inner",
    validate="one_to_one"
)

# Business case №1
"""
«Найдите бренды, которые выглядят наиболее перспективными по текущему ассортименту и пользовательскому интересу. 
Нам нужны не просто самые крупные бренды, а бренды, у которых есть признаки устойчивого интереса пользователей».
"""

df_test = copy.deepcopy(df_skincare)
df_test["recomm_count"] = (df_test["review_count"] * df_test["recommended"] / 100).round()
print(df_test.describe())
print(df_test.columns)
print(df_test.shape)
print(df_test.head(3))

print(df_test["rating"].isna().sum())
print(df_test["review_count"].isna().sum())
print(df_test["brand"].isna().sum())
print(df_test["recommended"].isna().sum())
# """
# None отствует 
# """
skincare_brand = df_test.groupby("brand").agg(
    total_product = ("item_id", "count"),
    total_review = ("review_count", "sum"),
    median_review = ("review_count", "median"),
    avg_review = ("review_count", "mean"),
    median_price = ("price_actual", "median"),
    total_recommended = ("recomm_count", "sum")
    ).reset_index()

skincare_brand["dolya_recomm"] = (skincare_brand["total_recommended"] / skincare_brand["total_review"] * 100).round(2)

target_review = df_test["review_count"].median().round(2)

print(target_review)
pre_table_skincare = skincare_brand[
    (skincare_brand["median_review"] >= target_review) & 
    (skincare_brand["total_product"] >= 3) &
    (skincare_brand["dolya_recomm"] >= 85)
    ]

print(pre_table_skincare["brand"].nunique()) 

target_33 = pre_table_skincare["total_review"].quantile(0.33)
target_66 = pre_table_skincare["total_review"].quantile(0.66)

pre_table_skincare.loc[
    pre_table_skincare["total_review"] <= target_33, "segment_review"
] = "low"
pre_table_skincare.loc[
    (pre_table_skincare["total_review"] > target_33) & (pre_table_skincare["total_review"] <= target_66), "segment_review"
] = "middle"
pre_table_skincare.loc[
    pre_table_skincare["total_review"] > target_66, "segment_review"
] = "high"

pre_table_skincare["coeff_avg_to_median"] = (100 - (pre_table_skincare["median_review"] / pre_table_skincare["avg_review"] * 100)).round(2)
table_skincare = pre_table_skincare[
    (pre_table_skincare["coeff_avg_to_median"] <= 20) & (pre_table_skincare["coeff_avg_to_median"] >= -20)
]

print(table_skincare.sort_values("median_review"))
# Кол-во продуктов 
x = table_skincare["brand"]
y = table_skincare["total_product"]

plt.bar(x, y)

plt.title("Brand и кол-во продуктов")
plt.xlabel("Brand")
plt.ylabel("Кол-во продуктов")
plt.xticks(rotation=50)

plt.show()

# # Распределение median (Берём её за основу, а не среднее, т.к делаем упор на стабильность вовлечения пользователя в Brand)
y = table_skincare["median_review"]

plt.bar(x, y)

plt.title("Brand и медианна кол-ва отзывов")
plt.xlabel("Brand")
plt.ylabel("Медианна кол-ва отзывов")
plt.xticks(rotation=50)

plt.show()

"""
Для первичного продвижения отбираются бренды:
1/ минимум с тремя 3 продуктами
2/ y которых медианное количество отзывов на товары не ниже медианы категории skincare 
3/ доля рекомендаций не ниже 85%
4/ отклонение среднего и медианного количества отзывов отличаются не более чем на 20%. 

Это позволяет отсечь бренды с маленькой выборкой, слабым пользовательским интересом и бренды, 
результат которых потенциально определяется отдельными хитами.
Среди прошедших брендов приоритет определяется сочетанием устойчивого интереса (median_review), 
общего масштаба интереса (total_review) 
и доли положительной обратной связи (dolya_recomm).
Bioderma — наиболее выраженный кандидат: очень высокий типичный объём отзывов, высокий общий объём отзывов и около 95% рекомендаций. 
d'Alba также сочетает высокий типичный интерес с крупным общим объёмом отзывов. 

Третий кандидат зависит от бизнес-приоритета: 
FOR ME by gold apple особенно интересен для масштабирования благодаря большому ассортименту и большому общему объёму отзывов, 
хотя его типичный кол-во продуктов уступает нескольким более компактным брендам.
""" 

