import psycopg
def insert_product_to_db(all_product):
    
    conn = psycopg.connect(     
    dbname="goldapple_pet",
    user="postgres",
    host="127.0.0.1",
    port=5432,
    autocommit=True
    )
    try:
        with conn.cursor() as cursor:
        # product, perfume, skincare, supplement
            for product in all_product:

                cursor.execute(
                    """
                    INSERT INTO product (
                        item_id,
                        main_variant_item_id,
                        url,
                        category,
                        name,
                        brand,
                        product_type,
                        product_attribute_type,
                        gender,
                        price_actual,
                        rating,
                        recommended,
                        review_count,
                        star_5_pct,
                        star_4_pct,
                        star_3_pct,
                        star_2_pct,
                        star_1_pct
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (item_id) DO NOTHING
                    """,
                    (
                        product.get("item_id"),
                        product.get("main_variant_item_id"),
                        product.get("url"),
                        product.get("category"),
                        product.get("name"),
                        product.get("brand"),
                        product.get("product_type"),
                        product.get("product_attribute_type"),
                        product.get("gender"),
                        product.get("price_actual"),
                        product.get("rating"),
                        product.get("recommended"),
                        product.get("review_count"),
                        product.get("star_5_pct"),
                        product.get("star_4_pct"),
                        product.get("star_3_pct"),
                        product.get("star_2_pct"),
                        product.get("star_1_pct")
                    )
                )

                if product["category"] == 'perfume':

                    cursor.execute(
                        """
                        INSERT INTO perfume (
                            item_id,
                            fragrance_group,
                            top_notes,
                            middle_notes,
                            base_notes,
                            volume
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (item_id) DO NOTHING
                        """,
                    (
                        product.get("item_id"),
                        product.get("fragrance_group"),
                        product.get("top_notes"),
                        product.get("middle_notes"),
                        product.get("base_notes"),
                        product.get("volume")
                    )
                )

                elif product["category"] == 'supplements':

                    cursor.execute(
                        """
                        INSERT INTO supplement (
                            item_id,
                            intended_use,
                            main_component,
                            release_form,
                            supplement_type,
                            hypoallergenic,
                            volume
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (item_id) DO NOTHING
                        """,
                    (
                            product.get("item_id"),
                            product.get("intended_use"),
                            product.get("main_component"),
                            product.get("release_form"),
                            product.get("supplement_type"),
                            product.get("hypoallergenic"),
                            product.get("volume")
                    )
                )

                elif product["category"] == 'skincare':

                    cursor.execute(
                        """
                        INSERT INTO skincare (
                            item_id,
                            intended_use,
                            skin_type,
                            time_use,
                            area_use,
                            main_component,
                            volume,
                            travel_format,
                            age_use,
                            flg_spf
                        )
                        VALUES ( %s, %s, %s, %s, %s,
                                 %s, %s, %s, %s, %s)
                        ON CONFLICT (item_id) DO NOTHING
                        """,
                    (
                            product.get("item_id"),
                            product.get("intended_use"),
                            product.get("skin_type"),
                            product.get("time_use"),
                            product.get("area_use"),
                            product.get("main_component"),
                            product.get("volume"),
                            product.get("travel_format"),
                            product.get("age_use"),
                            product.get("flg_spf")
                    )
                )

                conn.commit()
    
    except Exception:
        conn.rollback()
        raise

    finally:
        print("Данные загружены")
        conn.close()

# insert_product_to_db(all_product)
