import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime

import irods.keywords as kw
from irods.exception import (
    CollectionDoesNotExist,
    DataObjectDoesNotExist,
    NetworkException,
)
from irods.session import iRODSSession
from sqlalchemy import (
    bindparam,
    create_engine,
    text,
)

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib")))

import galaxy.config
from galaxy.util import directory_hash_id
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)

last_accessed_sql_statement = """SELECT iq.dataset_id, MAX(iq.create_time) AS max_create_time
                                 FROM (SELECT ds.id as dataset_id, j.create_time
                                 FROM dataset ds
                                 INNER JOIN history_dataset_association hda
                                 ON ds.id = hda.dataset_id
                                 INNER JOIN job_to_input_dataset jtid
                                 ON hda.id = jtid.dataset_id
                                 INNER JOIN job j
                                 ON jtid.job_id = j.id
                                 WHERE ds.state = :state
                                 AND ds.deleted = False
                                 AND ds.purged = False
                                 AND ds.id >= :min_id
                                 AND ds.id <= :max_id
                                 AND ds.object_store_id IN :store_ids
                                 UNION
                                 SELECT ds.id as dataset_id, j.create_time
                                 FROM dataset ds
                                 INNER JOIN history_dataset_association hda
                                 ON ds.id = hda.dataset_id
                                 INNER JOIN job_to_output_dataset jtod
                                 ON hda.id = jtod.dataset_id
                                 INNER JOIN job j
                                 ON jtod.job_id = j.id
                                 WHERE ds.state = :state
                                 AND ds.deleted = False
                                 AND ds.purged = False
                                 AND ds.id >= :min_id
                                 AND ds.id <= :max_id
                                 AND ds.object_store_id IN :store_ids) AS iq
                                 GROUP BY iq.dataset_id
                                 """


def copy_files_to_irods(
    start_dataset_id, end_dataset_id, object_store_info_file, irods_info_file, database_connection, copy_or_checksum
):
    if start_dataset_id > end_dataset_id:
        print(f"Error: start_dataset_id {start_dataset_id} cannot be larger than end_dataset_id {end_dataset_id}")
        return

    # read object_store_info file
    with open(object_store_info_file) as osi:
        object_store_info = json.load(osi)
    osi_keys = tuple(object_store_info.keys())

    # read irods_info_file
    with open(irods_info_file) as ii:
        irods_info = json.load(ii)

    try:
        engine = create_engine(database_connection)
        conn = engine.connect()

    except Exception as e:
        print(e)
        return

    session = iRODSSession(
        host=irods_info["host"],
        port=irods_info["port"],
        user=irods_info["user"],
        password=irods_info["password"],
        zone=irods_info["zone"],
    )
    session.connection_timeout = int(irods_info["timeout"])

    read_sql_statement = """SELECT id, object_store_id, uuid
                            FROM dataset
                            WHERE state = :state
                            AND NOT deleted
                            AND NOT purged
                            AND id >= :start_id
                            AND id <= :end_id
                            AND object_store_id IN :osi_keys"""

    update_sql_statement = """UPDATE dataset
                              SET object_store_id = :new_object_store_id
                              WHERE id = :objectid"""

    try:
        stmt = text(read_sql_statement).bindparams(bindparam("osi_keys", expanding=True))
        read_result = conn.execute(
            stmt, {"state": "ok", "start_id": start_dataset_id, "end_id": end_dataset_id, "osi_keys": list(osi_keys)}
        )
        rows = read_result.fetchall()
        for row in rows:
            objectid = row[0]
            object_store_id = row[1]
            uuid_without_dash = row[2]
            uuid_with_dash = str(uuid.UUID(uuid_without_dash))

            object_store_path = object_store_info.get(object_store_id)
            if object_store_path is None:
                print(f"Error: object_store_info_file does not have a value for {object_store_id}")
                raise Exception

            irods_resc = get_irods_resource(conn, objectid, object_store_id, irods_info)

            disk_sub_folder = os.path.join(*directory_hash_id(objectid))
            irods_sub_folder = os.path.join(*directory_hash_id(uuid_with_dash))
            disk_file_path = os.path.join(object_store_path, disk_sub_folder, "dataset_" + str(objectid) + ".dat")
            disk_folder_path = os.path.join(object_store_path, disk_sub_folder, "dataset_" + str(objectid) + "_files")
            irods_file_path = os.path.join(
                irods_info["home"], irods_sub_folder, "dataset_" + str(uuid_with_dash) + ".dat"
            )
            irods_file_collection_path = os.path.join(irods_info["home"], irods_sub_folder)
            irods_folder_collection_path = os.path.join(
                irods_file_collection_path, "dataset_" + str(uuid_with_dash) + "_files"
            )

            if copy_or_checksum == "copy":
                # Create the collection
                session.collections.create(irods_file_collection_path)

                # Add disk file to collection
                options = {kw.REG_CHKSUM_KW: "", kw.RESC_NAME_KW: irods_resc}
                session.data_objects.put(disk_file_path, irods_file_path, **options)
                print(f"Copied disk file {disk_file_path} to irods {irods_file_path}")

                if os.path.isdir(disk_folder_path):
                    disk_folder_path_all_files = disk_folder_path + "/*"

                    # Create the collection
                    session.collections.create(irods_folder_collection_path)

                    iput_command = (
                        "iput -R "
                        + irods_resc
                        + " -rk "
                        + disk_folder_path_all_files
                        + " "
                        + irods_folder_collection_path
                    )
                    subprocess.call(iput_command, shell=True)
                    print(f"Copied disk folder {disk_folder_path} to irods {irods_folder_collection_path}")

            if copy_or_checksum == "checksum":
                # Calculate disk file checksum. Then get the file checksum from irods and compare it with the calculated disk file checksum
                # Note that disk file checksum is ASCII, whereas irods file checksum is Unicode. get_file_checksum() converts checksum to unicode
                disk_file_checksum = get_file_checksum(disk_file_path)
                # Now get the file from irods
                try:
                    obj = session.data_objects.get(irods_file_path)
                    # obj.checksum is prepended with 'sha2:'. Remove that so we can compare it to disk file checksum
                    irods_file_checksum = obj.checksum[5:]
                    if irods_file_checksum != disk_file_checksum:
                        print(
                            f"Error: irods file checksum {irods_file_checksum} does not match disk file checksum {disk_file_checksum} for irods file {irods_file_path} and disk file {disk_file_path}"
                        )
                        continue
                except (DataObjectDoesNotExist, CollectionDoesNotExist) as e:
                    print(e)
                    continue
                except NetworkException as e:
                    print(e)
                    continue

                # Recursively verify that the checksum of all files in this folder matches that in irods
                if os.path.isdir(disk_folder_path):
                    # Recursively traverse the files in this folder
                    for root, _dirs, files in os.walk(disk_folder_path):
                        for file_name in files:
                            a_disk_file_path = os.path.join(root, file_name)
                            # Get checksum for disk file
                            a_disk_file_checksum = get_file_checksum(a_disk_file_path)

                            # Construct iords path for this disk file, so can get the file from irods, and compare its checksum with disk file checksum
                            # This is to extract the subfoler name for irods from the full disk path
                            irods_sub_folder = root.replace(disk_folder_path + "/", "")
                            # For some reason, join would not work here. I used string concatenation instead
                            an_irods_file_path = irods_folder_collection_path + "/" + irods_sub_folder + "/" + file_name

                            # Now get the file from irods
                            try:
                                obj = session.data_objects.get(an_irods_file_path)
                                # obj.checksum is prepended with 'sha2:'. Remove that so we can compare it to disk file checksum
                                an_irods_file_checksum = obj.checksum[5:]
                                if an_irods_file_checksum != a_disk_file_checksum:
                                    print(
                                        f"Error: irods file checksum {an_irods_file_checksum} does not match disk file checksum {a_disk_file_checksum} for irods file {an_irods_file_path} and disk file {a_disk_file_path}"
                                    )
                                    continue
                            except (DataObjectDoesNotExist, CollectionDoesNotExist) as e:
                                print(e)
                                continue
                            except NetworkException as e:
                                print(e)
                                continue

                    # Delete file on disk
                    print(f"Removing directory {disk_folder_path}")
                    shutil.rmtree(disk_folder_path)

                # Update object store id
                update_result = conn.execute(
                    text(update_sql_statement),
                    {"new_object_store_id": irods_info["object_store_id"], "objectid": objectid},
                )
                updated_rows = update_result.rowcount
                if updated_rows == 1:
                    print(
                        "Updated object store ID to {} in dataset table for object ID {}".format(
                            irods_info["object_store_id"], objectid
                        )
                    )
                else:
                    print(
                        "Error: Failed to update object store ID to {} in dataset table for object ID {}".format(
                            irods_info["object_store_id"], objectid
                        )
                    )

                # Delete file on disk
                print(f"Removing file {disk_file_path}")
                os.remove(disk_file_path)

    except Exception as e:
        print(e)
        session.cleanup()
        conn.rollback()
        conn.close()
        return

    session.cleanup()
    conn.commit()
    conn.close()


def get_irods_resource(conn, objectid, object_store_id, irods_info):
    try:
        irods_resc = irods_info["resc"]
        irods_tape_resc = irods_info["tape_resc"]
        irods_tape_resc_cuttoff = irods_info["tape_resc_cuttoff"]
        # Convert string to datetime
        irods_tape_resc_cuttoff_dt = datetime.strptime(irods_tape_resc_cuttoff, "%m/%d/%Y")

        stmt = text(last_accessed_sql_statement).bindparams(bindparam("store_ids", expanding=True))
        result = conn.execute(
            stmt, {"state": "ok", "min_id": objectid, "max_id": objectid, "store_ids": [object_store_id]}
        )
        row = result.fetchone()
        if row is None:
            print(
                f"Could not find the last access time for dataset with id {objectid}. Returning the default resc {irods_resc}."
            )
            return irods_resc

        dataset_id = row[0]
        if int(dataset_id) != objectid:
            print(
                f"The returned dataset id {dataset_id} does not match the passed in datsetid {objectid}. Returning the default resc {irods_resc}."
            )
            return irods_resc

        max_create_time = row[1]
        # Make max create time offset naive, so it can compared with offset naive tape cuttoff datetime
        max_create_time_dt = max_create_time.replace(tzinfo=None)
        # If the last time a dataset was accessed was prior to a cuttoff date, use the tape resource. Otherwise, use the regular (non-tape) resource
        if max_create_time_dt < irods_tape_resc_cuttoff_dt:
            print(
                f"The last time dataset with id {objectid} was accessed {max_create_time_dt} is prior to tape resource cuttoff {irods_tape_resc_cuttoff_dt}. Using tape resource in irods."
            )
            return irods_tape_resc

        print(
            f"The last time dataset with id {objectid} was accessed {max_create_time_dt} is after the tape resource cuttoff {irods_tape_resc_cuttoff_dt}. Using regular (non-tape) resource in irods."
        )
        return irods_resc

    except Exception as e:
        print(e)
        return


def get_file_checksum(disk_file_path):
    checksum_cmd = f"shasum -a 256 {disk_file_path} | xxd -r -p | base64"
    disk_file_checksum = subprocess.check_output(checksum_cmd, shell=True)
    # remove '\n' from the end of disk_file_checksum
    disk_file_checksum_len = len(disk_file_checksum)
    disk_file_checksum_trimmed = disk_file_checksum[0 : (disk_file_checksum_len - 1)]
    # Return Unicode string
    return disk_file_checksum_trimmed.decode("utf-8")


def print_help_msg():
    help_msg = """
               This script copies datasets from Disk to Irods.
               It operates on a range of dataset IDs (start_dataset_id and end_dtatset_id, both inclusive).
               It also takes in the name of 3 JSON configuration files.
               A sample JSON configuration file is provided in the Python script folder.

               1) object_store_info_file: Has Disk object store info (e.g. files info).
               2) irods_info_file: irods connection info, and misc. info (zone, home, obejct store ID, etc.).

               It also takes a flag copy_or_checksum.
               If copy: for all datasets from start_dataset_it to end_dataset_id, it copies disk files to irods.
                   This includes extra folders that come with the output of commands like fastqc.
               If checksum: for all datasets from start_dataset_id to end_dataset_id, it calculates the disk file checksum.
                   Then gets the irods file, and compares the disk file checksum to irods file checksum.
                   If checksums match:
                       It updates object_store_id dataset table (so Galaxy starts using the irods version of the file),
                       then DELETES the file from disk.
                   If the checksumdoes NOT match:
                       it prints and error message, does NOT update the dataset table or delete the disk file,
                       and continues with the next dataset in dataset ID range.

               In order to run this Python3 script, you need to install the following packages via pip3:
                   pip3 install galaxy.util
                   pip3 install sqlalchemy psycopg[binary]
                   pip3 install python_irodsclient

               Long-form input parameter specification:
               copy_files_to_irods --start_dataset_id=2 --end_dataset_id=3 --object_store_info_file=object_store_info.json
                   --irods_info_file=irods_info.json --config-file=galaxy.yml --copy_or_checksum=<copy|checksum>

               OR

               Short-form input parameter specification:
               copy_files_to_irods -s 2 -e 3 -o object_store_info.json -i irods_info.json -c galaxy.yml -C <copy|checksum>
               """
    print(help_msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--start_dataset_id", type=int, required=True)
    parser.add_argument("-e", "--end_dataset_id", type=int, required=True)
    parser.add_argument("-o", "--object_store_info_file", type=str, required=True)
    parser.add_argument("-i", "--irods_info_file", type=str, required=True)
    parser.add_argument("-C", "--copy_or_checksum", type=str, required=True, choices=["copy", "checksum"])
    populate_config_args(parser)

    args = parser.parse_args()
    print(args)

    app_properties = app_properties_from_args(args)
    config = galaxy.config.Configuration(**app_properties)
    database_connection = config.database_connection

    copy_files_to_irods(
        start_dataset_id=args.start_dataset_id,
        end_dataset_id=args.end_dataset_id,
        object_store_info_file=args.object_store_info_file,
        irods_info_file=args.irods_info_file,
        database_connection=database_connection,
        copy_or_checksum=args.copy_or_checksum,
    )
