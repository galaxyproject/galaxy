import os
import time
import uuid

from psycopg2 import connect, sql

from galaxy.util import directory_hash_id


def copy_files_to_irods(start_dataset_id, end_dataset_id, object_store_info={"files1" : "/Users/kxk302/workspace/galaxy/database/files1", "files2" : "/Users/kxk302/workspace/galaxy/database/files2"}, irods_home="/tempZone/home/rods", connection_info={"dbname" : "galaxy", "user" : "postgres", "host" : "localhost", "password" : "password"}):
    conn = None

    if start_dataset_id >= end_dataset_id:
        print("start_dataset_id %d must be smaller than end_dataset_id %d", start_dataset_id, end_dataset_id)
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

    for dataset_id in range(start_dataset_id, end_dataset_id):
        copy_file_to_irods(dataset_id, object_store_info, irods_home, conn)

    conn.close()


def copy_file_to_irods(dataset_id, object_store_info, irods_home, conn):
    cursor = None
    sql_statement = None
    sql_object = None
    uuid_without_dash = None
    uuid_with_dash = None
    objectid = None
    object_store_id = None
    disk_sub_folder = None
    disk_file_path = None
    irods_sub_folder = None
    irods_file_path = None
    icommand_mkdir = None
    icommand_put = None

    sql_statement = "SELECT id, object_store_id, uuid FROM dataset WHERE state = \'ok\' AND deleted = False AND purged = False AND id = {};".format(dataset_id)
    print(sql_statement)
    try:
        cursor = conn.cursor()

        sql_object = sql.SQL(
            sql_statement
        )
        cursor.execute(sql_object)
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
            irods_file_path = os.path.join(irods_home, irods_sub_folder, "dataset_" + str(uuid_with_dash) + ".dat")
            print("irods_file_path: ", irods_file_path)

            icommand_mkdir = "imkdir -p " + irods_sub_folder
            print("icommand_mkdir: ", icommand_mkdir)
            icommand_put = "iput " + disk_file_path + " " + irods_file_path
            print("icommand_put: ", icommand_put)

    except Exception as e:
        print(e)
        conn.rollback()
        return

    conn.commit()
    cursor.close()
