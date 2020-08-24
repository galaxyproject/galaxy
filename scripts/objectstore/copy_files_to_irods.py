import getopt
import json
import os
import uuid
import subprocess
import sys

import irods.keywords as kw
from irods.exception import CollectionDoesNotExist
from irods.exception import DataObjectDoesNotExist
from irods.exception import NetworkException
from irods.session import iRODSSession
from psycopg2 import connect


from galaxy.util import directory_hash_id


def copy_files_to_irods(start_dataset_id, end_dataset_id, object_store_info_file, irods_info_file, db_connection_info_file):
    conn = None
    session = None
    osi_keys = None
    read_sql_statement = None
    update_sql_statement = None
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
        print("start_dataset_id %d cannot be larger than end_dataset_id %d", start_dataset_id, end_dataset_id)
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
    print("osi_keys(): ", osi_keys)
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
        print(read_cursor.mogrify(read_sql_statement, args))
        print(read_sql_statement)

        read_cursor.execute(read_sql_statement, args)
        print("read_cursor.execute() completed")

        table_data = read_cursor.fetchall()
        print("read_cursor.fetchall() completed")
        for num, row in enumerate(table_data):
            print("row: ", row)
            print("\n")

            objectid = row[0]
            object_store_id = row[1]
            uuid_without_dash = row[2]

            print("Object ID: ", objectid)
            print("\n")
            print("Object Store ID: ", object_store_id)
            print("\n")
            print("uuid_without_dash: ", uuid_without_dash)
            print("\n")
            uuid_with_dash = str(uuid.UUID(uuid_without_dash))
            print("uuid_with_dash: ", uuid_with_dash)
            print("\n")

            object_store_path = object_store_info[object_store_id]
            print("object_store_path:", object_store_path)
            print("\n")

            disk_sub_folder = os.path.join(*directory_hash_id(objectid))
            print("disk_sub_folder: ", disk_sub_folder)
            irods_sub_folder = os.path.join(*directory_hash_id(uuid_with_dash))
            print("irods_sub_folder: ", irods_sub_folder)

            disk_file_path = os.path.join(object_store_path, disk_sub_folder, "dataset_" + str(objectid) + ".dat")
            print("disk_file_path: ", disk_file_path)
            disk_folder_path = os.path.join(object_store_path, disk_sub_folder, "dataset_" + str(objectid) + "_files")
            print("disk_folder_path: ", disk_folder_path)
            irods_file_path = os.path.join(irods_info["home"], irods_sub_folder, "dataset_" + str(uuid_with_dash) + ".dat")
            print("irods_file_path: ", irods_file_path)
            irods_file_collection_path = os.path.join(irods_info["home"], irods_sub_folder)
            print("irods_file_collection_path: ", irods_file_collection_path)
            irods_folder_collection_path = os.path.join(irods_file_collection_path, "dataset_" + str(uuid_with_dash) + "_files")
            print("irods_folder_collection_path: ", irods_folder_collection_path)

            # Create the collection
            session.collections.create(irods_file_collection_path)

            # Add disk file to collection
            options = {kw.DEST_RESC_NAME_KW: 'demoResc', kw.REG_CHKSUM_KW : ''}
            session.data_objects.put(disk_file_path, irods_file_path, **options)

            # Calculate disk file checksum before uploading it to irods
            # After disk file is uploaded to irods, we get the file checksum from irods and compare it with the calculated disk file checksum
            # Note that disk file checksum is ASCII, whereas irods file checksum is Unicode
            disk_file_checksum = get_file_checksum(disk_file_path)
            print("disk_file_checksum: ", disk_file_checksum)
            # Now get the file from irods
            try:
                obj = session.data_objects.get(irods_file_path)
                print("obj.checksum: ", obj.checksum)
                # obj.checksum is prepended with 'sha2:'. Remove that so we can compare it to disk file checksum
                irods_file_checksum = obj.checksum[5:]
                print("irods_file_checksum: ", irods_file_checksum)
                if irods_file_checksum != disk_file_checksum:
                    print("irods file checksum {} does not match disk file checksum {}".format(irods_file_checksum, disk_file_checksum))
                    return
            except (DataObjectDoesNotExist, CollectionDoesNotExist) as e:
                print(e)
                continue
            except NetworkException as e:
                print(e)
                continue

            if os.path.isdir(disk_folder_path):
                disk_folder_path_all_files = disk_folder_path + "/*"
                print("disk_folder_path_all_files: ", disk_folder_path_all_files)

                # Create the collection
                session.collections.create(irods_folder_collection_path)

                iput_command = "iput -r " + disk_folder_path_all_files + " " + irods_folder_collection_path
                subprocess.call(iput_command, shell=True)

            # Update object store id
            update_cursor = conn.cursor()
            print("irods object store id: ", irods_info["object_store_id"])
            update_cursor.execute(update_sql_statement, (irods_info["object_store_id"], objectid))
            updated_rows = update_cursor.rowcount
            print("updated_rows: ", updated_rows)
            update_cursor.close()

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
    print("checksum_cmd: ", checksum_cmd)
    disk_file_checksum = subprocess.check_output(checksum_cmd, shell=True)
    # remove '\n' from the end of disk_file_checksum
    print("disk_file_checksum: ", disk_file_checksum)
    disk_file_checksum_len = len(disk_file_checksum)
    print("disk_file_checksum_len: ", disk_file_checksum_len)
    disk_file_checksum_trimmed = disk_file_checksum[0:(disk_file_checksum_len - 1)]
    print("disk_file_checksum_trimmed: ", disk_file_checksum_trimmed)
    # Return Unicode string
    return disk_file_checksum_trimmed.decode("utf-8")


def print_help_msg():
    print("\nLong form input parameter specification:")
    print("copy_files_to_irods --start_dataset_id=2 --end_dataset_id=3 --object_store_info_file=object_store_info.json --irods_info_file=irods_info_file.json --db_connection_info_file=db_connection_info_file.json")
    print("\nOR")
    print("\nShort form input parameter specification:")
    print("copy_files_to_irods -s 2 -e 3 -o object_store_info.json -i irods_info_file.json -d db_connection_info_file.json")
    print("\n")


if __name__ == '__main__':
    start_dataset_id = None
    end_dataset_id = None
    object_store_info_file = None
    irods_info_file = None
    db_connection_info_file = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:e:o:i:d:", ["start_dataset_id=", "end_dataset_id=", "object_store_info_file=", "irods_info_file=", "db_connection_info_file="])
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

    if start_dataset_id is None or end_dataset_id is None or object_store_info_file is None or irods_info_file is None or db_connection_info_file is None:
        print("Did not specify one of the required input parameters!")
        print_help_msg()
        sys.exit(2)

    copy_files_to_irods(start_dataset_id=start_dataset_id, end_dataset_id=end_dataset_id, object_store_info_file=object_store_info_file, irods_info_file=irods_info_file, db_connection_info_file=db_connection_info_file)
