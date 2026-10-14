from typing import TYPE_CHECKING

from sqlalchemy import (
    and_,
    func,
    literal,
    or_,
    SQLColumnExpression,
    true,
    union,
    union_all,
)
from sqlalchemy.orm import aliased
from sqlalchemy.sql import (
    ColumnElement,
    select,
    Select,
)
from sqlalchemy.sql.expression import (
    CTE,
    Subquery,
)

from galaxy import model

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session

COPY_ASSOCIATIONS = {
    model.HistoryDatasetAssociation: (
        "copied_from_history_dataset_association_id",
        model.JobToOutputDatasetAssociation.dataset_id,
    ),
    model.HistoryDatasetCollectionAssociation: (
        "copied_from_history_dataset_collection_association_id",
        model.JobToOutputDatasetCollectionAssociation.dataset_collection_id,
    ),
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

    def get_related_hids(self, history_id: int, hid: int) -> list[int]:
        """Return this history's hids for the item's immediate job inputs and outputs.

        Ordinary copies inherit their source's connections. Job outputs, including cached
        and pass-through outputs, keep their own connections even when they have a copy link.
        """
        hda = model.HistoryDatasetAssociation
        hdca = model.HistoryDatasetCollectionAssociation
        item_classes = (hda, hdca)
        metadata_tables: list[Subquery] = []
        metadata_selects: list[ColumnElement[int] | ColumnElement[bool]] = []
        for item_class in item_classes:
            copied_from, _ = COPY_ASSOCIATIONS[item_class]
            # Find the clicked item and copy presence in the same pass over this history's rows.
            metadata = (
                select(
                    func.min(item_class.id).filter(item_class.hid == hid).label("item_id"),
                    (func.count(getattr(item_class, copied_from)) > 0).label("has_copies"),
                )
                .where(item_class.history_id == history_id)
                .subquery()
            )
            metadata_tables.append(metadata)
            metadata_selects.extend((metadata.c.item_id, metadata.c.has_copies))
        hda_id, hda_copies, hdca_id, hdca_copies = self.sa_session.execute(
            select(*metadata_selects).select_from(metadata_tables[0].join(metadata_tables[1], true()))
        ).one()
        if hda_id is None and hdca_id is None:
            return [hid]
        copies_by_class = {hda: hda_copies, hdca: hdca_copies}
        # Avoid planning copy work in ordinary histories, and anchor the clicked item by primary key.
        collection_outputs = self._collection_output_hda_ids(history_id) if hda_copies else None
        related_selects = []
        for item_class, item_id in ((hda, hda_id), (hdca, hdca_id)):
            if item_id is None:
                continue
            if copies_by_class[item_class]:
                chain = self._copied_from_chain(
                    item_class,
                    item_class.id == item_id,
                    name=f"clicked_{item_class.__name__.lower()}",
                    collection_outputs=collection_outputs,
                )
                related_id = chain.c.ancestor_id
            else:
                related_id = item_id
            if item_class is hda:
                related_selects.extend(self.outputs_derived_from_input_hda(related_id))
                related_selects.extend(self.inputs_for_hda(related_id))
            else:
                related_selects.extend(self.outputs_derived_from_input_hdca(related_id))
                related_selects.extend(self.inputs_for_hdca(related_id))
        related = union_all(*related_selects).cte("related_items")
        hid_selects: list[Select[tuple[int | None]]] = [select(literal(hid).label("hid"))]
        for item_class in item_classes:
            related_ids = select(related.c.id).where(related.c.src == item_class.__name__)
            # Direct matches need no ancestry walk, including in histories that were never copied.
            hid_selects.append(
                select(item_class.hid).where(item_class.history_id == history_id, item_class.id.in_(related_ids))
            )
            if not copies_by_class[item_class]:
                continue
            copied_from, _ = COPY_ASSOCIATIONS[item_class]
            has_creating_job = self._has_creating_job(item_class, item_class.id, collection_outputs)
            copies = self._copied_from_chain(
                item_class,
                and_(
                    item_class.history_id == history_id,
                    getattr(item_class, copied_from).is_not(None),
                    ~has_creating_job,
                    related_ids.exists(),
                ),
                name=f"copies_{item_class.__name__.lower()}",
                stop_at=related_ids,
                collection_outputs=collection_outputs,
            )
            hid_selects.append(select(copies.c.hid).where(copies.c.ancestor_id.in_(related_ids)))
        return list(self.sa_session.scalars(union(*hid_selects)))

    def _copied_from_chain(
        self,
        item_class: type[model.HistoryDatasetAssociation] | type[model.HistoryDatasetCollectionAssociation],
        where: ColumnElement[bool],
        name: str,
        stop_at: Select[tuple[int]] | None = None,
        collection_outputs: CTE | None = None,
    ) -> CTE:
        """Pair each selected item's hid with its ordinary-copy ancestors, including the
        first job-created ancestor, without following that ancestor's own copy link."""
        copied_from, _ = COPY_ASSOCIATIONS[item_class]

        chain = (
            select(
                item_class.hid.label("hid"),
                item_class.id.label("ancestor_id"),
                getattr(item_class, copied_from).label("copied_from_id"),
            )
            .where(where)
            .cte(name=name, recursive=True)
        )
        parent = aliased(item_class)
        ancestors = (
            select(chain.c.hid, parent.id, getattr(parent, copied_from))
            .join(parent, parent.id == chain.c.copied_from_id)
            .where(~self._has_creating_job(item_class, chain.c.ancestor_id, collection_outputs))
        )
        if stop_at is not None:
            ancestors = ancestors.where(chain.c.ancestor_id.not_in(stop_at))
        # UNION also terminates malformed cyclic copy links; ordinary job joins use UNION ALL.
        return chain.union(ancestors)

    def _has_creating_job(
        self,
        item_class: type[model.HistoryDatasetAssociation] | type[model.HistoryDatasetCollectionAssociation],
        item_id: SQLColumnExpression[int],
        collection_outputs: CTE | None = None,
    ) -> ColumnElement[bool]:
        _, output_id = COPY_ASSOCIATIONS[item_class]
        has_job = select(output_id).where(output_id == item_id).exists()
        if item_class is model.HistoryDatasetAssociation and collection_outputs is not None:
            return or_(has_job, item_id.in_(select(collection_outputs.c.hda_id)))
        return has_job

    def _collection_output_hda_ids(self, history_id: int) -> CTE:
        """Find collection-owned outputs among this history's possible copy ancestors.

        Collection tools can register a collection without individual element outputs.
        Batch membership checks so every copy hop does not walk collections separately.
        """
        hda = model.HistoryDatasetAssociation
        candidates = self._copied_from_chain(
            hda,
            and_(hda.history_id == history_id, hda.copied_from_history_dataset_association_id.is_not(None)),
            name="possible_dataset_copy_ancestors",
        )
        candidate_ids = select(candidates.c.ancestor_id.label("hda_id")).distinct().cte("possible_dataset_copy_ids")
        element = model.DatasetCollectionElement
        memberships = (
            select(element.hda_id, element.dataset_collection_id.label("collection_id"))
            .where(element.hda_id.in_(select(candidate_ids.c.hda_id)))
            .cte("copy_element_collections", recursive=True)
        )
        parent = aliased(element)
        memberships = memberships.union(
            select(memberships.c.hda_id, parent.dataset_collection_id)
            .join(parent, parent.child_collection_id == memberships.c.collection_id)
            .where(parent.child_collection_id.is_not(None))
        )
        # An explicit distinct work set keeps downstream membership-join estimates bounded.
        memberships = (
            select(memberships.c.hda_id, memberships.c.collection_id)
            .distinct()
            .cte("distinct_copy_element_collections")
        )
        output = model.JobToOutputDatasetCollectionAssociation
        hdca = model.HistoryDatasetCollectionAssociation
        # Reusing an existing input in an output collection does not create a new dataset output.
        input_dataset = model.JobToInputDatasetAssociation
        is_input = (
            select(input_dataset.id)
            .where(input_dataset.job_id == output.job_id, input_dataset.dataset_id == memberships.c.hda_id)
            .correlate(output, memberships)
            .exists()
        )
        input_collection = model.JobToInputDatasetCollectionAssociation
        input_hdca = aliased(hdca)
        input_memberships = memberships.alias("input_element_collections")
        is_collection_input = (
            select(input_collection.id)
            .join(input_hdca, input_hdca.id == input_collection.dataset_collection_id)
            .join(input_memberships, input_memberships.c.collection_id == input_hdca.collection_id)
            .where(input_collection.job_id == output.job_id, input_memberships.c.hda_id == memberships.c.hda_id)
            .correlate(output, memberships)
            .exists()
        )
        is_output = (
            select(output.id)
            .select_from(memberships)
            .join(hdca, hdca.collection_id == memberships.c.collection_id)
            .join(output, output.dataset_collection_id == hdca.id)
            .where(memberships.c.hda_id == candidate_ids.c.hda_id, ~is_input, ~is_collection_input)
            .exists()
        )
        return select(candidate_ids.c.hda_id).where(is_output).cte("collection_output_hdas")

    def _get_union_results(self, *selects):
        result = []
        for row in self.sa_session.execute(union(*selects)).all():
            result.append({"src": row.src, "id": row.id})
        return result

    def outputs_derived_from_input_hda(self, input_hda_id: int | ColumnElement[int]):
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

    def outputs_derived_from_input_hdca(self, input_hdca_id: int | ColumnElement[int]):
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

    def inputs_for_hda(self, input_hda_id: int | ColumnElement[int]):
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

    def inputs_for_hdca(self, input_hdca_id: int | ColumnElement[int]):
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
