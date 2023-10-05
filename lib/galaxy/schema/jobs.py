from galaxy.schema.schema import EncodedDatasetSourceId, Model


class JobInputSummary(Model):
    has_empty_inputs: bool
    has_duplicate_inputs: bool


class JobAssociation(Model):
    name: str
    dataset: EncodedDatasetSourceId
