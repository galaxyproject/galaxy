def restrict_test(context, section):
    """
    Disable the Test Section section

    This tool filter will disable the Test Section section.
    """
    if section.name == "Test Section":
        return False
    return True
