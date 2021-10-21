def collection_consists_of_objects(collection, *objects):
    """
    Returns True iff list(collection) == list(objects), where object equality is determined
    by primary key equality: object1.id == object2.id.
    """
    if len(collection) != len(objects):  # False if lengths are different
        return False
    if not collection:   # True if both are empty
        return True

    # Sort, then compare each member by its 'id' attribute, which must be its primary key.
    collection.sort(key=lambda item: item.id)
    objects = list(objects)
    objects.sort(key=lambda item: item.id)

    for item1, item2 in zip(collection, objects):
        if item1.id is None or item2.id is None or item1.id != item2.id:
            return False
    return True
