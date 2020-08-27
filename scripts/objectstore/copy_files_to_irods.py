import getopt
import json
import os
import uuid
import shutil
import subprocess
import sys

import irods.keywords as kw
from irods.exception import CollectionDoesNotExist
from irods.exception import DataObjectDoesNotExist
from irods.exception import NetworkException
from irods.session import iRODSSession
from psycopg2 import connect


from galaxy.util import directory_hash_id


def copy_files_to_irods(start_dataset_id, end_dataset_id, object_store_info_file, irods_info_file, db_connection_info_file, copy_or_checksum):
    conn = None
    session = None
    osi_keys = None
    read_sql_statement = None
    read_cursor = None
    args = None
    table_data = None
    objectid = None
    object_store_id = None
    uuid_without_dash = None
    uuid_with_dash = None
    object_store_path = None
    disk_sub_folder = None
    irods_sub_folder = None
    disk_file_path = None
    disk_folder_path = None
    irods_file_path = None
    irods_file_collection_path = None
    irods_folder_collection_path = None
    options = None
    iput_command = None
    object_store_info = None
    irods_info = None
    db_connection_info = None

    if start_dataset_id > end_dataset_id:
        print("Error: start_dataset_id {} cannot be larger than end_dataset_id {}".format(start_dataset_id, end_dataset_id))
        return

    # read object_store_info file
    with open(object_store_info_file, mode="r") as osi:
        object_store_info = json.load(osi)
    osi_keys = tuple(object_store_info.keys())

    # read irods_info_file
    with open(irods_info_file, mode="r") as ii:
        irods_info = json.load(ii)

    # read db_connectin_info file
    with open(db_connection_info_file, mode="r") as dci:
        db_connection_info = json.load(dci)

    try:
        # declare a new PostgreSQL connection object
        conn = connect(
            dbname=db_connection_info["dbname"],
            user=db_connection_info["user"],
            host=db_connection_info["host"],
            password=db_connection_info["password"]
        )
        conn.cursor()

    except Exception as e:
        print(e)
        return

    session = iRODSSession(host=irods_info["host"], port=irods_info["port"], user=irods_info["user"], password=irods_info["password"], zone=irods_info["zone"])
    session.connection_timeout = int(irods_info["timeout"])

    osi_keys = tuple(object_store_info.keys())
    read_sql_statement = """SELECT id, object_store_id, uuid
                            FROM dataset
                            WHERE state = %s
                            AND NOT deleted
                            AND NOT purged
                            AND id >= %s
                            AND id <= %s
                            AND object_store_id IN %s"""

    update_sql_statement = """UPDATE dataset
                              SET object_store_id = %s
                              WHERE id = %s"""
    try:
        read_cursor = conn.cursor()
        args = ('ok', start_dataset_id, end_dataset_id, osi_keys)
        read_cursor.mogrify(read_sql_statement, args)

        read_cursor.execute(read_sql_statement, args)

        table_data = read_cursor.fetchall()
        for num, row in enumerate(table_data):
            objectid = row[0]
            object_store_id = row[1]
            uuid_without_dash = row[2]
            uuid_with_dash = str(uuid.UUID(uuid_without_dash))

            object_store_path = object_store_info.get(object_store_id)
            if object_store_path is None:
                print("Error: object_store_info_file does not have a value for {}".format(object_store_id))
                raise Exception

            disk_sub_folder = os.path.join(*directory_hash_id(objectid))
            irods_sub_folder = os.path.join(*directory_hash_id(uuid_with_dash))
            disk_file_path = os.path.join(object_store_path, disk_sub_folder, "dataset_" + str(objectid) + ".dat")
            disk_folder_path = os.path.join(object_store_path, disk_sub_folder, "dataset_" + str(objectid) + "_files")
            irods_file_path = os.path.join(irods_info["home"], irods_sub_folder, "dataset_" + str(uuid_with_dash) + ".dat")
            irods_file_collection_path = os.path.join(irods_info["home"], irods_sub_folder)
            irods_folder_collection_path = os.path.join(irods_file_collection_path, "dataset_" + str(uuid_with_dash) + "_files")

            if copy_or_checksum == "copy":
                # Create the collection
                session.collections.create(irods_file_collection_path)

                # Add disk file to collection
                options = {kw.REG_CHKSUM_KW : ''}
                session.data_objects.put(disk_file_path, irods_file_path, **options)
                print("Copied disk file {} to irods {}".format(disk_file_path, irods_file_path))

                if os.path.isdir(disk_folder_path):
                    disk_folder_path_all_files = disk_folder_path + "/*"

                    # Create the collection
                    session.collections.create(irods_folder_collection_path)

                    iput_command = "iput -rk " + disk_folder_path_all_files + " " + irods_folder_collection_path
                    subprocess.call(iput_command, shell=True)
                    print("Copied disk folder {} to irods {}".format(disk_folder_path, irods_folder_collection_path))

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
                        print("Error: irods file checksum {} does not match disk file checksum {} for irods file {} and disk file {}".format(irods_file_checksum, disk_file_checksum, irods_file_path, disk_file_path))
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
                    for root, dirs, files in os.walk(disk_folder_path):
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
                                    print("Error: irods file checksum {} does not match disk file checksum {} for irods file {} and disk file {}".format(an_irods_file_checksum, a_disk_file_checksum, an_irods_file_path, a_disk_file_path))
                                    continue
                            except (DataObjectDoesNotExist, CollectionDoesNotExist) as e:
                                print(e)
                                continue
                            except NetworkException as e:
                                print(e)
                                continue

                    # Delete file on disk
                    print("Removing directory {}".format(disk_folder_path))
                    shutil.rmtree(disk_folder_path)

                # Update object store id
                update_cursor = conn.cursor()
                update_cursor.execute(update_sql_statement, (irods_info["object_store_id"], objectid))
                updated_rows = update_cursor.rowcount
                if updated_rows == 1:
                    print("Updated object store ID to {} in dataset table for object ID {}".format(irods_info["object_store_id"], objectid))
                else:
                    print("Error: Failed to update object store ID to {} in dataset table for object ID {}".format(irods_info["object_store_id"], objectid))
                update_cursor.close()

                # Delete file on disk
                print("Removing file {}".format(disk_file_path))
                os.remove(disk_file_path)

    except Exception as e:
        print(e)
        session.cleanup()
        conn.rollback()
        read_cursor.close()
        conn.close()
        return

    session.cleanup()
    conn.commit()
    read_cursor.close()
    conn.close()


def get_file_checksum(disk_file_path):
    checksum_cmd = "shasum -a 256 {} | xxd -r -p | base64".format(disk_file_path)
    disk_file_checksum = subprocess.check_output(checksum_cmd, shell=True)
    # remove '\n' from the end of disk_file_checksum
    disk_file_checksum_len = len(disk_file_checksum)
    disk_file_checksum_trimmed = disk_file_checksum[0:(disk_file_checksum_len - 1)]
    # Return Unicode string
    return disk_file_checksum_trimmed.decode("utf-8")


def print_help_msg():
    print("\nThis script copies datasets from Disk to Irods. It operates on a range of dataset IDs (start_dataset_id and end_dtatset_id, both inclusive).")
    print("It also takes in the name of 3 JSON configuration files (A sample JSON configuration file is provided in the Python script folder).")
    print("\n1) object_store_info_file: Has Disk object store info (e.g. files info).")
    print("2) irods_info_file: irods connection info, and misc. info (zone, home, obejct store ID, etc.).")
    print("3) db_connection_info: Galaxy DB connection info.")
    print("\nIt also takes a flag copy_or_checksum.")
    print("If copy: for all datasets from start_dataset_it to end_dataset_id, it copies disk files to irods. This includes extra folders that come with the output of commands like fastqc.")
    print("If checksum: for all datasets from start_dataset_id to end_dataset_id, it calculates the disk file checksum, gets the irods file, and compares the disk file checksum to irods file checksum.")
    print("If checksums match, it updates object_store_id dataset table (so Galaxy starts using the irods version of the file), then DELETES the file from disk.")
    print("If the checksumdoes NOT match: it prints and error message, does NOT update the dataset table or delete the disk file, and continues with the next dataset in dataset ID range.")
    print("\nIn order to run this Python3 script, you need to install the following packages via pip3:")
    print("\tpip3 install galaxy.util")
    print("\tpip3 install psycopg2")
    print("\tpip3 install python_irodsclient")
    print("\nLong-form input parameter specification:")
    print("copy_files_to_irods --start_dataset_id=2 --end_dataset_id=3 --object_store_info_file=object_store_info.json --irods_info_file=irods_info_file.json --db_connection_info_file=db_connection_info_file.json --copy_or_checksum=<copy|checksum>")
    print("\nOR")
    print("\nShort-form input parameter specification:")
    print("copy_files_to_irods -s 2 -e 3 -o object_store_info.json -i irods_info_file.json -d db_connection_info_file.json -c <copy|checksum>")
    print("\n")


if __name__ == '__main__':
    start_dataset_id = None
    end_dataset_id = None
    object_store_info_file = None
    irods_info_file = None
    db_connection_info_file = None
    copy_or_checksum = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:e:o:i:d:c:", ["start_dataset_id=", "end_dataset_id=", "object_store_info_file=", "irods_info_file=", "db_connection_info_file=", "copy_or_checksum="])
    except getopt.GetoptError:
        print_help_msg()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_help_msg()
            sys.exit(2)
        elif opt in ("-s", "--start_dataset_id"):
            start_dataset_id = arg
        elif opt in ("-e", "--end_datset_id"):
            end_dataset_id = arg
        elif opt in ("-o", "--object_store_info_file"):
            object_store_info_file = arg
        elif opt in ("-i", "--irods_info_file"):
            irods_info_file = arg
        elif opt in ("-d", "--db_connection-info-file"):
            db_connection_info_file = arg
        elif opt in ("-c", "--copy_or_checksum"):
            copy_or_checksum = arg

    if start_dataset_id is None or end_dataset_id is None or object_store_info_file is None or irods_info_file is None or db_connection_info_file is None or copy_or_checksum is None:
        print("Error: Did not specify one of the required input parameters!")
        print_help_msg()
        sys.exit(2)

    if copy_or_checksum != "copy" and copy_or_checksum != "checksum":
        print("Error: Invalid value specified for copy_or_checksum input parameter {}".format(copy_or_checksum))
        print_help_msg()
        sys.exit(2)

    copy_files_to_irods(start_dataset_id=start_dataset_id, end_dataset_id=end_dataset_id, object_store_info_file=object_store_info_file, irods_info_file=irods_info_file, db_connection_info_file=db_connection_info_file, copy_or_checksum=copy_or_checksum)
