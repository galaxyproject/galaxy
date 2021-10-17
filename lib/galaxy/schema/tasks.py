from enum import Enum

from pydantic import BaseModel


class PdfDocumentType(str, Enum):
    invocation_report = "invocation_report"
    page = "page"


class PrepareDatasetCollectionDownload(BaseModel):
    short_term_storage_request_id: str
    history_dataset_collection_association_id: int
