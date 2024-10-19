def create_entries_products_for_images(image_links, field_ids):
    entries_products = []
    id_sequence = [28, 30, 32, 34, 36, 38, 40, 42, 44, 46]  # The id sequence as given
    id_sequence = [field_ids.get("Online Image 1"), field_ids.get("Online Image 2"), field_ids.get("Online Image 3"), field_ids.get("Online Image 4"), field_ids.get("Online Image 5"), field_ids.get("Online Image 6"), field_ids.get("Online Image 7"), field_ids.get("Online Image 8"), field_ids.get("Online Image 9"), field_ids.get("Online Image 10")]
    print("Here is id sequence: ", id_sequence)
    for index, link in enumerate(image_links[:10]):
        entry = {
            "id": id_sequence[index],
            "name": f"Online Image {index + 1}",
            "type": "image",
            "value": [link],
        }
        entries_products.append(entry)
    return entries_products


def create_entries_products_for_msrps(msrps, field_ids):
    entries_products = []
    id_sequence = [60, 61, 62, 63, 64, 71, 72, 77, 78, 79]  # The id sequence as given
    id_sequence = [field_ids.get("MSRP 1"), field_ids.get("MSRP 2"), field_ids.get("MSRP 3"), field_ids.get("MSRP 4"), field_ids.get("MSRP 5"), field_ids.get("MSRP 6"), field_ids.get("MSRP 7"), field_ids.get("MSRP 8"), field_ids.get("MSRP 9"), field_ids.get("MSRP 10")]

    for index, msrp in enumerate(msrps[:10]):
        entry = {
            "id": id_sequence[index],
            "name": f"MSRP {index + 1}",
            "type": "text",
            "value": f"{msrp}",
        }
        entries_products.append(entry)
    return entries_products
