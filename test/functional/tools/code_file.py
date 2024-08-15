def validate_input(trans, error_map, param_values, page_param_map):
    """
    Validates the user input, before execution.
    """
    first = param_values["name1"]
    second = param_values["name2"]
    if first == second:
        error_map["name1"] = "The value names should be different."
