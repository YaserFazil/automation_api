def create_entries_products_for_images(image_links):
    entries_products = []
    id_sequence = [28, 30, 32, 34, 36, 38, 40, 42, 44, 46]  # The id sequence as given
    for index, link in enumerate(image_links):
        entry = {
            "id": id_sequence[index],
            "name": f"Online Image {index + 1}",
            "type": "image",
            "value": [link],
        }
        entries_products.append(entry)
    return entries_products


def create_entries_products_for_msrps(msrps):
    entries_products = []
    id_sequence = [60, 61, 62, 63, 64, 71, 72, 77, 78, 79]  # The id sequence as given
    for index, msrp in enumerate(msrps):
        entry = {
            "id": id_sequence[index],
            "name": f"MSRP {index + 1}",
            "type": "text",
            "value": msrp,
        }
        entries_products.append(entry)
    return entries_products


images = [
    "asldkjf",
    "kfdsj",
    "lskdjf",
    "lskjdf",
    "lskdjf",
    "sldjf",
    "slkfdj",
    "lskfdj",
    "sfkj",
    "skdjflk",
]

images_links = create_entries_products_for_images(images)
msrps = create_entries_products_for_msrps(images)
print(images_links + msrps)
