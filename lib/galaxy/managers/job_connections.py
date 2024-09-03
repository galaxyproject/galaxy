from sqlalchemy import (
    literal,
    union,
)
from sqlalchemy.sql import (
    expression,
    select,
)

from galaxy import model
from galaxy.managers.base import get_class
from galaxy.model.scoped_session import galaxy_scoped_session


class JobConnectionsManager:
    """Get connections graph of inputs and outputs for given item"""

    def __init__(self, sa_session: galaxy_scoped_session):
        self.sa_session = sa_session

    def get_connections_graph(self, id: int, src: str):
        """Get connections graph of inputs and outputs for given item id"""
        if src == "HistoryDatasetAssociation":
            output_selects = self.outputs_derived_from_input_hda(id)
            input_selects = self.inputs_for_hda(id)
        elif src == "HistoryDatasetCollectionAssociation":
            output_selects = self.outputs_derived_from_input_hdca(id)
            input_selects = self.inputs_for_hdca(id)
        else:
            raise Exception(f"Invalid item type {src}")
        # Execute selects and return graph of inputs and outputs
        result = {}
        result["outputs"] = self._get_union_results(*output_selects)
        result["inputs"] = self._get_union_results(*input_selects)
        return result

    def get_related_hids(self, history_id, hid: int):
        """Get connections graph of inputs and outputs for given item hid from the given history_id"""
        # Get id(s) and src(s) for the given hid
        items_by_hid = self.sa_session.execute(
            select(model.HistoryDatasetAssociation.id, expression.literal("HistoryDatasetAssociation"))
            .filter_by(history_id=history_id, hid=hid)
            .union(
                select(
                    model.HistoryDatasetCollectionAssociation.id,
                    expression.literal("HistoryDatasetCollectionAssociation"),
                ).filter_by(history_id=history_id, hid=hid)
            )
        ).all()
        result = [hid]
        for item_data in items_by_hid:
            graph = self.get_connections_graph(id=item_data[0], src=item_data[1])
            # Add found related items' hids to result list
            for val in graph["outputs"] + graph["inputs"]:
                item_class = get_class(val["src"])
                item_hid = self.sa_session.execute(select(item_class.hid).where(item_class.id == val["id"])).scalar()
                result.append(item_hid)  # type:ignore[arg-type]
        return result

    def _get_union_results(self, *selects):
        result = []
        for row in self.sa_session.execute(union(*selects)).all():
            result.append({"src": row.src, "id": row.id})
        return result

    def outputs_derived_from_input_hda(self, input_hda_id: int):
        hda_select = (
            select(
                literal("HistoryDatasetAssociation").label("src"),
                model.JobToOutputDatasetAssociation.dataset_id.label("id"),
            )
            .join(
                model.JobToInputDatasetAssociation,
                model.JobToInputDatasetAssociation.job_id == model.JobToOutputDatasetAssociation.job_id,
            )
            .where(model.JobToOutputDatasetAssociation.dataset_id.is_not(None))
            .where(model.JobToInputDatasetAssociation.dataset_id == input_hda_id)
        )
        hdca_select = (
            select(
                literal("HistoryDatasetCollectionAssociation").label("src"),
                model.JobToOutputDatasetCollectionAssociation.dataset_collection_id.label("id"),
            )
            .join(
                model.JobToInputDatasetAssociation,
                model.JobToInputDatasetAssociation.job_id == model.JobToOutputDatasetCollectionAssociation.job_id,
            )
            .where(model.JobToOutputDatasetCollectionAssociation.dataset_collection_id.is_not(None))
            .where(model.JobToInputDatasetAssociation.dataset_id == input_hda_id)
        )
        return hda_select, hdca_select

    def outputs_derived_from_input_hdca(self, input_hdca_id: int):
        hda_select = (
            select(
                literal("HistoryDatasetAssociation").label("src"),
                model.JobToOutputDatasetAssociation.dataset_id.label("id"),
            )
            .join(
                model.JobToInputDatasetCollectionAssociation,
                model.JobToInputDatasetCollectionAssociation.job_id == model.JobToOutputDatasetAssociation.job_id,
            )
            .where(model.JobToOutputDatasetAssociation.dataset_id.is_not(None))
            .where(model.JobToInputDatasetCollectionAssociation.dataset_collection_id == input_hdca_id)
        )
        hdca_select = (
            select(
                literal("HistoryDatasetCollectionAssociation").label("src"),
                model.JobToOutputDatasetCollectionAssociation.dataset_collection_id.label("id"),
            )
            .join(
                model.JobToInputDatasetCollectionAssociation,
                model.JobToInputDatasetCollectionAssociation.job_id
                == model.JobToOutputDatasetCollectionAssociation.job_id,
            )
            .where(model.JobToOutputDatasetCollectionAssociation.dataset_collection_id.is_not(None))
            .where(model.JobToInputDatasetCollectionAssociation.dataset_collection_id == input_hdca_id)
        )
        return hda_select, hdca_select

    def inputs_for_hda(self, input_hda_id: int):
        input_hdas = (
            select(
                literal("HistoryDatasetAssociation").label("src"),
                model.JobToInputDatasetAssociation.dataset_id.label("id"),
            )
            .join(
                model.JobToOutputDatasetAssociation,
                model.JobToOutputDatasetAssociation.job_id == model.JobToInputDatasetAssociation.job_id,
            )
            .where(model.JobToInputDatasetAssociation.dataset_id.is_not(None))
            .where(model.JobToOutputDatasetAssociation.dataset_id == input_hda_id)
        )
        input_hdcas = (
            select(
                literal("HistoryDatasetCollectionAssociation").label("src"),
                model.JobToInputDatasetCollectionAssociation.dataset_collection_id.label("id"),
            )
            .join(
                model.JobToOutputDatasetAssociation,
                model.JobToOutputDatasetAssociation.job_id == model.JobToInputDatasetCollectionAssociation.job_id,
            )
            .where(model.JobToInputDatasetCollectionAssociation.dataset_collection_id.is_not(None))
            .where(model.JobToOutputDatasetAssociation.dataset_id == input_hda_id)
        )
        return input_hdas, input_hdcas

    def inputs_for_hdca(self, input_hdca_id: int):
        input_hdas = (
            select(
                literal("HistoryDatasetAssociation").label("src"),
                model.JobToInputDatasetAssociation.dataset_id.label("id"),
            )
            .join(
                model.JobToOutputDatasetCollectionAssociation,
                model.JobToOutputDatasetCollectionAssociation.job_id == model.JobToInputDatasetAssociation.job_id,
            )
            .where(model.JobToInputDatasetAssociation.dataset_id.is_not(None))
            .where(model.JobToOutputDatasetCollectionAssociation.dataset_collection_id == input_hdca_id)
        )
        input_hdcas = (
            select(
                literal("HistoryDatasetCollectionAssociation").label("src"),
                model.JobToInputDatasetCollectionAssociation.dataset_collection_id.label("id"),
            )
            .join(
                model.JobToOutputDatasetCollectionAssociation,
                model.JobToOutputDatasetCollectionAssociation.job_id
                == model.JobToInputDatasetCollectionAssociation.job_id,
            )
            .where(model.JobToInputDatasetCollectionAssociation.dataset_collection_id.is_not(None))
            .where(model.JobToOutputDatasetCollectionAssociation.dataset_collection_id == input_hdca_id)
        )
        return input_hdas, input_hdcas
