SUFFIX_TO_BYTES = {
    'KI': 1024,
    'MI': 1024**2,
    'GI': 1024**3,
    'TI': 1024**4,
    'PI': 1024**5,
    'EI': 1024**6,
    'K': 1000,
    'M': 1000**2,
    'G': 1000**3,
    'T': 1000**4,
    'P': 1000**5,
    'E': 1000**6,
}


class ByteSize(object):
    """Convert multiples of bytes to various units."""

    def __init__(self, value):
        """
        Represents a quantity of bytes.

        `value` may be an integer, in which case it is assumed to be bytes.
        If value is a string, it is parsed as bytes if no suffix (Mi, M, Gi, G ...)
        is found.

        >>> values = [128974848, '129e6', '129M', '123Mi' ]
        >>> [ByteSize(v).to_unit('M') for v in values]
        ['128M', '129M', '129M', '128M']
        """
        self.value = parse_bytesize(value)

    def to_unit(self, unit=None, as_string=True):
        """unit must be `None` or one of Ki,Mi,Gi,Ti,Pi,Ei,K,M,G,T,P."""
        if unit is None:
            if as_string:
                return str(self.value)
            return self.value
        unit = unit.upper()
        new_value = int(self.value / SUFFIX_TO_BYTES[unit])
        if not as_string:
            return new_value
        return "{value}{suffix}".format(value=new_value, suffix=unit)


def parse_bytesize(value):
    if isinstance(value, int):
        # Assume bytes
        return value
    value = value.upper()
    found_suffix = None
    for suffix in SUFFIX_TO_BYTES:
        if value.endswith(suffix):
            found_suffix = suffix
            break
    if found_suffix:
        value = value[:-len(found_suffix)]
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            raise ValueError("{value} is not a valid integer or float value".format(value=value))
    if found_suffix:
        value = value * SUFFIX_TO_BYTES[found_suffix]
    return value
