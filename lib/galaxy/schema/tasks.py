from enum import Enum

from pydantic import BaseModel


class PdfDocumentType(str, Enum):
    invocation_report = "invocation_report"
    page = "page"


class PrepareDatasetCollectionDownload(BaseModel):
    short_term_storage_request_id: str
    history_dataset_collection_association_id: int


class GeneratePdfDownload(BaseModel):
    short_term_storage_request_id: str
    # basic markdown - Galaxy directives need to be processed before handing off to this task
    basic_markdown: str
    document_type: PdfDocumentType
