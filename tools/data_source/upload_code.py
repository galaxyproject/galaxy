from galaxy.datatypes import registry

def get_formats():
    datatypes_registry = registry.Registry()
    options = []
    formats = datatypes_registry.datatypes_by_extension.keys()
    formats.sort()

    options.append(('Auto-detect','auto',True))
    for format in formats:
        label = format.capitalize()
        options.append((label,format,False))
    return options