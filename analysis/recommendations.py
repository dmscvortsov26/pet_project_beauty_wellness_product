# Business case №2
"""
Рекомендательный score для perfume
"""
df_perfume_recomm = df_perfume[["item_id", "name", "brand", "fragrance_group", "top_notes", "middle_notes", "base_notes"]]

df_perfume_recomm = df_perfume_recomm[df_perfume_recomm["fragrance_group"].notna()]

df_perfume_recomm["all_notes"] = df_perfume_recomm[["top_notes", "middle_notes", "base_notes"]].fillna("").astype(str).agg(", ".join, axis=1)

def score_product():


    print("1 этап, определение товара!")
    while True:

        loc_start = int(input("Введите номер что бы посмотреть характеристики продукта из каталога: (Этот продукт будет уйдет в рекомендации) "))
        result = df_perfume_recomm.iloc[loc_start]
        print(result)

        end = int(input("Введите цифру 1, если вы определились с товаром, 0 если продолжите просмотр: "))
        
        if end == 1:
            break


    print('2 этап, сбор данных')
    target_result = {
        "item_id": result["item_id"], 
        "name": result["name"],
        "brand": result["brand"],
        "fragrance_group": result["fragrance_group"],
        "top_notes": result["top_notes"],
        "middle_notes": result["middle_notes"],
        "base_notes": result["base_notes"],
        "all_notes": result["all_notes"]
    }
    print(target_result)

    recomm_perfume = {}

    for product in df_perfume_recomm.itertuples():

        score = 0
        pre_item = [item_id.strip() for item_id in product.item_id.split(',')]

        if pre_item != [target_result["item_id"]]:
            try:
                top_notes = [note.strip() for note in product.top_notes.split(',')] if product.top_notes else []
                middle_notes = [note.strip() for note in product.middle_notes.split(',')] if product.middle_notes else []
                base_notes = [note.strip() for note in product.base_notes.split(',')] if product.base_notes else []
                all_notes = [note.strip() for note in product.all_notes.split(',')] if product.all_notes else []
                frag_lists = [group.strip() for group in product.fragrance_group.split(',')] if product.fragrance_group else []

                for top_note in top_notes:
                    if top_note in target_result["top_notes"]:
                        score += 20

                for middle_note in middle_notes:
                    if middle_note in target_result["middle_notes"]:
                        score += 10

                for base_note in base_notes:
                    if base_note in target_result["base_notes"]:
                        score += 15
                
                for frag_group in frag_lists:
                    if frag_group in target_result["fragrance_group"]:
                        score += 3

                for all_note in all_notes:
                    if all_note in target_result["all_notes"]:
                        score += 1
        
                recomm_perfume[product.item_id] = score

            except TypeError:
                continue

            except AttributeError:
                continue

    print("3 этап, подготовка рекомендаций")
    sort_dict = dict(sorted(recomm_perfume.items(), key=lambda item: item[1], reverse=True))

    top3_recomm = set()
    for ind, el in enumerate(sort_dict):
        if ind < 5:
            top3_recomm.add(el)


    print("4 этап, рекомендации")
    result = df_perfume.loc[
        df_perfume["item_id"].isin(top3_recomm)
    ]
    print(result)
