from pydantic import BaseModel


class SetupHistoryExportJob(BaseModel):
    history_id: int
    job_id: int
    store_directory: str
    include_files: bool
    include_hidden: bool
    include_deleted: bool
