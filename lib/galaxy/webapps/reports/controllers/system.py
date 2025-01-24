import logging
import shutil
from datetime import (
    datetime,
    timedelta,
)
from decimal import Decimal

from sqlalchemy import (
    and_,
    desc,
    false,
    null,
    select,
    true,
)
from sqlalchemy.orm import joinedload

from galaxy import (
    model,
    util,
)
from galaxy.webapps.base.controller import (
    BaseUIController,
    web,
)

log = logging.getLogger(__name__)


class System(BaseUIController):
    @web.expose
    def index(self, trans, **kwd):
        params = util.Params(kwd)
        message = ""
        if params.userless_histories_days:
            userless_histories_days = params.userless_histories_days
        else:
            userless_histories_days = "60"
        if params.deleted_histories_days:
            deleted_histories_days = params.deleted_histories_days
        else:
            deleted_histories_days = "60"
        if params.deleted_datasets_days:
            deleted_datasets_days = params.deleted_datasets_days
        else:
            deleted_datasets_days = "60"
        file_path, disk_usage, datasets, file_size_str = self.disk_usage(trans, **kwd)
        if "action" in kwd:
            if kwd["action"] == "userless_histories":
                userless_histories_days, message = self.userless_histories(trans, **kwd)
            elif kwd["action"] == "deleted_histories":
                deleted_histories_days, message = self.deleted_histories(trans, **kwd)
            elif kwd["action"] == "deleted_datasets":
                deleted_datasets_days, message = self.deleted_datasets(trans, **kwd)
        return trans.fill_template(
            "/webapps/reports/system.mako",
            file_path=file_path,
            disk_usage=disk_usage,
            datasets=datasets,
            file_size_str=file_size_str,
            userless_histories_days=userless_histories_days,
            deleted_histories_days=deleted_histories_days,
            deleted_datasets_days=deleted_datasets_days,
            message=message,
            nice_size=nice_size,
        )

    def userless_histories(self, trans, **kwd):
        """The number of userless histories and associated datasets that have not been updated for the specified number of days."""
        params = util.Params(kwd)
        message = ""
        if params.userless_histories_days:
            userless_histories_days = int(params.userless_histories_days)
            cutoff_time = datetime.utcnow() - timedelta(days=userless_histories_days)
            history_count = 0
            dataset_count = 0
            stmt = select(model.History).filter(
                and_(
                    model.History.user_id == null(),
                    model.History.deleted == true(),
                    model.History.update_time < cutoff_time,
                )
            )
            for history in trans.sa_session.scalars(stmt).all():
                for dataset in history.datasets:
                    if not dataset.deleted:
                        dataset_count += 1
                history_count += 1
            message = f"{history_count} userless histories ( including a total of {dataset_count} datasets ) have not been updated for at least {userless_histories_days} days."
        else:
            message = "Enter the number of days."
        return str(userless_histories_days), message

    def deleted_histories(self, trans, **kwd):
        """
        The number of histories that were deleted more than the specified number of days ago, but have not yet been purged.
        Also included is the number of datasets associated with the histories.
        """
        params = util.Params(kwd)
        message = ""
        if params.deleted_histories_days:
            deleted_histories_days = int(params.deleted_histories_days)
            cutoff_time = datetime.utcnow() - timedelta(days=deleted_histories_days)
            history_count = 0
            dataset_count = 0
            disk_space = 0

            stmt = (
                select(model.History)
                .filter(
                    and_(
                        model.History.deleted == true(),
                        model.History.purged == false(),
                        model.History.update_time < cutoff_time,
                    )
                )
                .options(joinedload(model.History.datasets))
                .unique()
            )

            histories = trans.sa_session.scalars(stmt).all()
            for history in histories:
                for hda in history.datasets:
                    if not hda.dataset.purged:
                        dataset_count += 1
                        try:
                            disk_space += hda.dataset.file_size
                        except Exception:
                            pass
                history_count += 1
            message = (
                f"{history_count} histories ( including a total of {dataset_count} datasets ) were deleted more than {deleted_histories_days} days ago, but have not yet been purged, "
                f"disk space: {nice_size(disk_space, True)}."
            )
        else:
            message = "Enter the number of days."
        return str(deleted_histories_days), message

    def deleted_datasets(self, trans, **kwd):
        """The number of datasets that were deleted more than the specified number of days ago, but have not yet been purged."""
        params = util.Params(kwd)
        message = ""
        if params.deleted_datasets_days:
            deleted_datasets_days = int(params.deleted_datasets_days)
            cutoff_time = datetime.utcnow() - timedelta(days=deleted_datasets_days)
            dataset_count = 0
            disk_space = 0
            stmt = select(model.Dataset).filter(
                and_(
                    model.Dataset.deleted == true(),
                    model.Dataset.purged == false(),
                    model.Dataset.update_time < cutoff_time,
                )
            )
            for dataset in trans.sa_session.scalars(stmt).all():
                dataset_count += 1
                try:
                    disk_space += dataset.file_size
                except Exception:
                    pass
            message = (
                f"{dataset_count} datasets were deleted more than {deleted_datasets_days} days ago, but have not yet been purged,"
                f" disk space: {nice_size(disk_space, True)}."
            )
        else:
            message = "Enter the number of days."
        return str(deleted_datasets_days), message

    @web.expose
    def dataset_info(self, trans, **kwd):
        message = ""
        dataset = trans.sa_session.get(model.Dataset, trans.security.decode_id(kwd.get("id", "")))
        # Get all associated hdas and lddas that use the same disk file.
        stmt = select(trans.model.HistoryDatasetAssociation).filter(
            and_(
                trans.model.HistoryDatasetAssociation.deleted == false(),
                trans.model.HistoryDatasetAssociation.dataset_id == dataset.id,
            )
        )
        associated_hdas = trans.sa_session.scalars(stmt).all()
        stmt = select(trans.model.LibraryDatasetDatasetAssociation).filter(
            and_(
                trans.model.LibraryDatasetDatasetAssociation.deleted == false(),
                trans.model.LibraryDatasetDatasetAssociation.dataset_id == dataset.id,
            )
        )
        associated_lddas = trans.sa_session.scalars(stmt).all()
        return trans.fill_template(
            "/webapps/reports/dataset_info.mako",
            dataset=dataset,
            associated_hdas=associated_hdas,
            associated_lddas=associated_lddas,
            message=message,
        )

    def get_disk_usage(self, file_path):
        disk_usage = shutil.disk_usage(file_path)
        pct_used = round(disk_usage.used / disk_usage.total * 100, 2)
        return (nice_size(disk_usage.total), nice_size(disk_usage.used), nice_size(disk_usage.free), pct_used)

    @web.expose
    def disk_usage(self, trans, **kwd):
        file_path = trans.app.config.file_path
        disk_usage = self.get_disk_usage(file_path)
        min_file_size = 2**32  # 4 Gb
        file_size_str = nice_size(min_file_size)
        stmt = (
            select(model.Dataset)
            .filter(and_(model.Dataset.purged == false(), model.Dataset.file_size > min_file_size))
            .order_by(desc(model.Dataset.file_size))
        )
        datasets = trans.sa_session.scalars(stmt).all()
        return file_path, disk_usage, datasets, file_size_str


def nice_size(size, include_bytes=False):
    """Returns a readably formatted string with the size"""
    niced = False
    nice_string = f"{size} bytes"
    try:
        nsize = Decimal(size)
        for x in ["bytes", "KB", "MB", "GB"]:
            if nsize.compare(Decimal("1024.0")) == Decimal("-1"):
                nice_string = f"{nsize:3.1f} {x}"
                niced = True
                break
            nsize /= Decimal("1024.0")
        if not niced:
            nice_string = f"{nsize:3.1f} TB"
            niced = True
        if include_bytes and x != "bytes":
            nice_string = f"{nice_string} ({size} bytes)"
    except Exception:
        pass
    return nice_string
