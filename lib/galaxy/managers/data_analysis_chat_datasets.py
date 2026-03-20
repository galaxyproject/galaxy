"""Manager for data analysis chat dataset download preparation."""

import os
from dataclasses import dataclass

from galaxy.exceptions import (
    ItemAccessibilityException,
    ObjectNotFound,
    RequestParameterMissingException,
)
from galaxy.managers.agents import AgentService
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model import User


@dataclass
class PreparedDatasetDownload:
    file_path: str
    mime_type: str
    display_name: str
    content_length: int


class DataAnalysisChatDatasetsManager:
    """Prepare dataset downloads authorized for browser-side data analysis execution."""

    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service

    def prepare_download(
        self,
        trans: ProvidesHistoryContext,
        user: User,
        dataset_id: str,
        token: str,
    ) -> PreparedDatasetDownload:
        if not token:
            raise RequestParameterMissingException("Missing download token")

        try:
            self.agent_service.verify_dataset_download_token(trans, dataset_id, token)
        except ValueError as exc:
            raise ItemAccessibilityException(str(exc)) from exc

        try:
            decoded_id = trans.security.decode_id(dataset_id)
        except Exception as exc:
            raise ObjectNotFound("Dataset not found") from exc

        hda_manager = trans.app.hda_manager
        try:
            hda = hda_manager.get_accessible(decoded_id, user, current_history=trans.history, trans=trans)
        except Exception as exc:
            raise ItemAccessibilityException("Dataset is not accessible") from exc

        try:
            hda_manager.ensure_dataset_on_disk(trans, hda)
        except Exception as exc:
            raise ObjectNotFound(str(exc)) from exc

        file_path = hda.dataset.get_file_name()
        if not file_path or not os.path.exists(file_path):
            raise ObjectNotFound("Dataset file not found")

        try:
            display_name = hda.display_name()
        except Exception:
            display_name = hda.name or dataset_id

        return PreparedDatasetDownload(
            file_path=file_path,
            mime_type=hda.get_mime() or "application/octet-stream",
            display_name=display_name or dataset_id,
            content_length=os.path.getsize(file_path),
        )
