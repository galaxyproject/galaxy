from typing import TYPE_CHECKING

from sqlalchemy import (
    and_,
    literal,
    union,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql import (
    ColumnElement,
    select,
)
from sqlalchemy.sql.expression import CTE

from galaxy import model

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session

COPIED_FROM_ATTRIBUTES = {
    model.HistoryDatasetAssociation: "copied_from_history_dataset_association_id",
    model.HistoryDatasetCollectionAssociation: "copied_from_history_dataset_collection_association_id",
}


class JobConnectionsManager:
    """Get connections graph of inputs and outputs for given item"""

    def __init__(self, sa_session: "scoped_session"):
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
        """Get hids of inputs and outputs for the item with the given hid in the given history.

        Items copied into the history (e.g. by importing a history) are connected to jobs only
        through the items they were copied from, so connections are found for every item in the
        copy chain and then mapped back to the history's own copies.
        """
        related_ids: dict[str, set[int]] = {
            "HistoryDatasetAssociation": set(),
            "HistoryDatasetCollectionAssociation": set(),
        }
        for src, item_class in (
            ("HistoryDatasetAssociation", model.HistoryDatasetAssociation),
            ("HistoryDatasetCollectionAssociation", model.HistoryDatasetCollectionAssociation),
        ):
            chain = self._copied_from_chain(
                item_class, and_(item_class.history_id == history_id, item_class.hid == hid)
            )
            for item_id in self.sa_session.scalars(select(chain.c.ancestor_id)):
                graph = self.get_connections_graph(id=item_id, src=src)
                for val in graph["outputs"] + graph["inputs"]:
                    related_ids[val["src"]].add(val["id"])
        result = {hid}
        hda_ids = related_ids["HistoryDatasetAssociation"]
        if hda_ids:
            # copies of a dataset share its underlying dataset
            hda = model.HistoryDatasetAssociation
            related_dataset_ids = select(hda.dataset_id).where(hda.id.in_(hda_ids))
            result.update(
                self.sa_session.scalars(
                    select(hda.hid).where(hda.history_id == history_id, hda.dataset_id.in_(related_dataset_ids))
                )
            )
        hdca_ids = related_ids["HistoryDatasetCollectionAssociation"]
        if hdca_ids:
            hdca = model.HistoryDatasetCollectionAssociation
            chain = self._copied_from_chain(hdca, hdca.history_id == history_id)
            result.update(self.sa_session.scalars(select(chain.c.hid).where(chain.c.ancestor_id.in_(hdca_ids))))
        return list(result)

    def _copied_from_chain(
        self,
        item_class: type[model.HistoryDatasetAssociation] | type[model.HistoryDatasetCollectionAssociation],
        where: ColumnElement[bool],
    ) -> CTE:
        """Recursive CTE pairing the hid of each item matching ``where`` with the item's id and
        the ids of all items it was (transitively) copied from."""
        copied_from = COPIED_FROM_ATTRIBUTES[item_class]
        chain = (
            select(
                item_class.hid.label("hid"),
                item_class.id.label("ancestor_id"),
                getattr(item_class, copied_from).label("copied_from_id"),
            )
            .where(where)
            .cte(name="copied_from_chain", recursive=True)
        )
        parent = aliased(item_class)
        return chain.union(
            select(chain.c.hid, parent.id, getattr(parent, copied_from)).join(
                parent, parent.id == chain.c.copied_from_id
            )
        )

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
