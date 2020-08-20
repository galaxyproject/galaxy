import getopt
import os
import uuid
import subprocess
import sys

import irods.keywords as kw
from irods.session import iRODSSession
from psycopg2 import connect


from galaxy.util import directory_hash_id


def copy_files_to_irods(start_dataset_id,
                        end_dataset_id,
                        object_store_info={"files1" : "/Users/kxk302/workspace/galaxy/database/files1", "files2" : "/Users/kxk302/workspace/galaxy/database/files2"},
                        irods_info={"home" : "/tempZone/home/rods", "host" : "localhost", "port" : "1247", "user" : "rods", "password" : "rods", "zone" : "tempZone", "timeout" : "30"},
                        connection_info={"dbname" : "galaxy", "user" : "postgres", "host" : "localhost", "password" : "password"}):
    conn = None
    session = None
    osi_keys = None
    sql_statement = None
    cursor = None
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

    if start_dataset_id > end_dataset_id:
        print("start_dataset_id %d cannot be larger than end_dataset_id %d", start_dataset_id, end_dataset_id)
        return

    try:
        # declare a new PostgreSQL connection object
        conn = connect(
            dbname=connection_info["dbname"],
            user=connection_info["user"],
            host=connection_info["host"],
            password=connection_info["password"]
        )
        conn.cursor()

    except Exception as e:
        print(e)
        return

    session = iRODSSession(host=irods_info["host"], port=irods_info["port"], user=irods_info["user"], password=irods_info["password"], zone=irods_info["zone"])
    session.connection_timeout = int(irods_info["timeout"])

    osi_keys = tuple(object_store_info.keys())
    print("osi_keys(): ", osi_keys)
    sql_statement = """SELECT id, object_store_id, uuid
                       FROM dataset
                       WHERE state = %s
                       AND NOT deleted
                       AND NOT purged
                       AND id >= %s
                       AND id <= %s
                       AND object_store_id IN %s"""
    try:
        cursor = conn.cursor()
        args = ('ok', start_dataset_id, end_dataset_id, osi_keys)
        print(cursor.mogrify(sql_statement, args))
        print(sql_statement)

        cursor.execute(sql_statement, args)
        print("cursor.execute() completed")

        table_data = cursor.fetchall()
        print("cursor.fetchall() completed")
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
            options = {kw.DEST_RESC_NAME_KW: 'demoResc'}
            session.data_objects.put(disk_file_path, irods_file_path, **options)

            if os.path.isdir(disk_folder_path):
                disk_folder_path_all_files = disk_folder_path + "/*"
                print("disk_folder_path_all_files: ", disk_folder_path_all_files)

                # Create the collection
                session.collections.create(irods_folder_collection_path)

                iput_command = "iput -r " + disk_folder_path_all_files + " " + irods_folder_collection_path
                subprocess.call(iput_command, shell=True)

    except Exception as e:
        print(e)
        session.cleanup()
        conn.rollback()
        cursor.close()
        conn.close()
        return

    session.cleanup()
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    print("Number of arguments: " + str(len(sys.argv)))
    print("Arguments list: " + str(sys.argv))

    start_dataset_id = None
    end_dataset_id = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:e:", ["start-dataset-id=", "end-dataset-id="])
    except getopt.GetoptError:
        print("copy_files_to_irods -s 2 -e 3")
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print("copy_files_to_irods -s 2 -e 3")
            sys.exit(2)
        elif opt in ("-s", "--start-dataset-id"):
            start_dataset_id = arg
        elif opt in ("-e", "--end-datset-id"):
            end_dataset_id = arg

    copy_files_to_irods(start_dataset_id=start_dataset_id, end_dataset_id=end_dataset_id)
