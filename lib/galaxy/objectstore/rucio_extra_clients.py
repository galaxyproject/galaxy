import copy
import logging
import time

try:
    from rucio.client.uploadclient import UploadClient
    from rucio.common.exception import (
        InputValidationError,
        NoFilesUploaded,
        NotAllFilesUploaded,
        RSEWriteBlocked,
    )
    from rucio.common.utils import generate_uuid
    from rucio.rse import rsemanager as rsemgr
except ImportError:
    UploadClient = object


class DeleteClient(UploadClient):
    def delete(self, items, forced_schemes=None, ignore_availability=False):
        for item in items:
            self._delete_item(item, forced_schemes, ignore_availability)

    def _delete_item(self, item, forced_schemes, ignore_availability):
        logger = self.logger
        dids = [item["did"]]
        files = list(next(self.client.list_replicas(dids))["pfns"].items())
        for file in files:
            pfn = file[0]
            rse = file[1]["rse"]
            force_scheme = None
            for rse_scheme in forced_schemes or []:
                if rse == rse_scheme["rse"]:
                    force_scheme = rse_scheme["scheme"]
            if not self.rses.get(rse):
                rse_settings = self.rses.setdefault(rse, rsemgr.get_rse_info(rse, vo=self.client.vo))
                if not ignore_availability and rse_settings["availability_delete"] != 1:
                    logger(logging.DEBUG, "%s is not available for deletion. No actions have been taken", rse)
                    continue

            # protocol handling and deletion
            rse_settings = self.rses[rse]
            protocols = rsemgr.get_protocols_ordered(rse_settings=rse_settings, operation="delete", scheme=force_scheme)
            protocols.reverse()
            success = False
            while not success and len(protocols):
                protocol = protocols.pop()
                cur_scheme = protocol["scheme"]
                try:
                    protocol_delete = self._create_protocol(rse_settings, "delete", force_scheme=cur_scheme)
                    protocol_delete.delete(pfn)
                    success = True
                except Exception as error:
                    logger(logging.WARNING, "Delete attempt failed")
                    logger(logging.INFO, "Exception: %s", error, exc_info=True)
            logger(logging.DEBUG, "Successfully deleted dataset %s", pfn)


class InPlaceIngestClient(UploadClient):
    def ingest(self, items, summary_file_path=None, traces_copy_out=None, ignore_availability=False, activity=None):
        """
        :param items: List of dictionaries. Each dictionary describing a file to upload. Keys:
            path                  - path of the file that will be uploaded
            path                  - path of the file that will be uploaded
            rse                   - rse expression/name (e.g. 'CERN-PROD_DATADISK') where to upload the file
            did_scope             - Optional: custom did scope (Default: user.<account>)
            did_name              - Optional: custom did name (Default: name of the file)
            dataset_scope         - Optional: custom dataset scope
            dataset_name          - Optional: custom dataset name
            dataset_meta          - Optional: custom metadata for dataset
            impl                  - Optional: name of the protocol implementation to be used to upload this item.
            force_scheme          - Optional: force a specific scheme (if PFN upload this will be overwritten) (Default: None)
            pfn                   - Optional: use a given PFN (this sets no_register to True, and no_register becomes mandatory)
            no_register           - Optional: if True, the file will not be registered in the rucio catalogue
            register_after_upload - Optional: if True, the file will be registered after successful upload
            lifetime              - Optional: the lifetime of the file after it was uploaded
            transfer_timeout      - Optional: time after the upload will be aborted
            guid                  - Optional: guid of the file
            recursive             - Optional: if set, parses the folder structure recursively into collections
        :param summary_file_path: Optional: a path where a summary in form of a json file will be stored
        :param traces_copy_out: reference to an external list, where the traces should be uploaded
        :param ignore_availability: ignore the availability of a RSE
        :param activity: the activity set to the rule if no dataset is specified

        :returns: 0 on success

        :raises InputValidationError: if any input arguments are in a wrong format
        :raises RSEWriteBlocked: if a given RSE is not available for writing
        :raises NoFilesUploaded: if no files were successfully uploaded
        :raises NotAllFilesUploaded: if not all files were successfully uploaded
        """
        # helper to get rse from rse_expression:

        logger = self.logger
        self.trace["uuid"] = generate_uuid()

        # check given sources, resolve dirs into files, and collect meta infos
        files = self._collect_and_validate_file_info(items)
        logger(logging.DEBUG, f"Num. of files that upload client is processing: {len(files)}")

        # check if RSE of every file is available for writing
        # and cache rse settings
        registered_dataset_dids = set()
        registered_file_dids = set()
        for file in files:
            rse = file["rse"]
            if not self.rses.get(rse):
                rse_settings = self.rses.setdefault(rse, rsemgr.get_rse_info(rse, vo=self.client.vo))
                if not ignore_availability and rse_settings["availability_write"] != 1:
                    raise RSEWriteBlocked(f"{rse} is not available for writing. No actions have been taken")

            dataset_scope = file.get("dataset_scope")
            dataset_name = file.get("dataset_name")
            file["rse"] = rse
            if dataset_scope and dataset_name:
                dataset_did_str = f"{dataset_scope}:{dataset_name}"
                file["dataset_did_str"] = dataset_did_str
                registered_dataset_dids.add(dataset_did_str)

            registered_file_dids.add(f"{file['did_scope']}:{file['did_name']}")
        wrong_dids = registered_file_dids.intersection(registered_dataset_dids)
        if len(wrong_dids):
            raise InputValidationError(f"DIDs used to address both files and datasets: {wrong_dids}")
        logger(logging.DEBUG, "Input validation done.")

        # clear this set again to ensure that we only try to register datasets once
        registered_dataset_dids = set()
        num_succeeded = 0
        summary = []
        for file in files:
            basename = file["basename"]
            logger(logging.INFO, "Preparing upload for file %s", basename)

            pfn = file.get("pfn")

            trace = copy.deepcopy(self.trace)
            # appending trace to list reference, if the reference exists
            if traces_copy_out is not None:
                traces_copy_out.append(trace)

            rse = file["rse"]
            trace["scope"] = file["did_scope"]
            trace["datasetScope"] = file.get("dataset_scope", "")
            trace["dataset"] = file.get("dataset_name", "")
            trace["remoteSite"] = rse
            trace["filesize"] = file["bytes"]

            file_did = {"scope": file["did_scope"], "name": file["did_name"]}
            dataset_did_str = file.get("dataset_did_str")
            rse_settings = self.rses[rse]
            is_deterministic = rse_settings.get("deterministic", True)
            if not is_deterministic and not pfn:
                logger(logging.ERROR, "PFN has to be defined for NON-DETERMINISTIC RSE.")
                continue
            if pfn and is_deterministic:
                logger(
                    logging.WARNING,
                    "Upload with given pfn implies that no_register is True, except non-deterministic RSEs",
                )
                no_register = True

            self._register_file(
                file, registered_dataset_dids, ignore_availability=ignore_availability, activity=activity
            )

            file["upload_result"] = {0: True, 1: None, "success": True, "pfn": pfn}  # needs to be removed
            num_succeeded += 1
            trace["transferStart"] = time.time()
            trace["transferEnd"] = time.time()
            trace["clientState"] = "DONE"
            file["state"] = "A"
            logger(logging.INFO, "Successfully uploaded file %s", basename)
            self._send_trace(trace)

            if summary_file_path:
                summary.append(copy.deepcopy(file))

            replica_for_api = self._convert_file_for_api(file)
            try:
                self.client.update_replicas_states(rse, files=[replica_for_api])
            except Exception as error:
                logger(logging.ERROR, f"Failed to update replica state for file {basename}")
                logger(logging.DEBUG, f"Details: {str(error)}")

            # add file to dataset if needed
            if dataset_did_str and not no_register:
                try:
                    self.client.attach_dids(file["dataset_scope"], file["dataset_name"], [file_did])
                except Exception as error:
                    logger(logging.WARNING, "Failed to attach file to the dataset")
                    logger(logging.DEBUG, f"Attaching to dataset {str(error)}")

        if num_succeeded == 0:
            raise NoFilesUploaded()
        elif num_succeeded != len(files):
            raise NotAllFilesUploaded()
        return 0
