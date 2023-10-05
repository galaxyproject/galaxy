from galaxy.schema.schema import Model


class JobInputSummary(Model):
    has_empty_inputs: bool
    has_duplicate_inputs: bool
