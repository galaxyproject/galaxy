from galaxy import model


def build_collection( type, dataset_instances ):
    """
    Build DatasetCollection with populated DatasetcollectionElement objects
    corresponding to the supplied dataset instances or throw exception if
    this is not a valid collection of the specified type.
    """
    dataset_collection = model.DatasetCollection( )
    set_collection_elements( dataset_collection, type, dataset_instances )
    return dataset_collection


def set_collection_elements( dataset_collection, type, dataset_instances ):
    element_index = 0
    elements = []
    for element in type.generate_elements( dataset_instances ):
        element.element_index = element_index
        element.collection = dataset_collection
        elements.append( element )

        element_index += 1

    dataset_collection.elements = elements
    return dataset_collection
