import os
import subprocess
import sys
import time
sys.path.insert(0, '../../packages/objectstore/')

from psycopg2 import connect, sql

from galaxy.util import directory_hash_id


def copy_file_to_irods(dataset_id, objectstore_id="", galaxy_dir="/Users/kxk302/workspace/galaxy", object_store_info={"files1" : "database/files1", "files2" : "database/files2"}, irods_home="/tempZone/home/rods"):
    cursor = None
    conn = None
    sql_statement = None
    sql_object = None
    uuid = None
    uuid_with_dash = None
    objectid = None
    object_store_id = None
    disk_sub_folder = None
    disk_file_path = None
    irods_sub_folder = None
    irods_file_path = None
    icommand_mkdir = None
    icommand_put = None

    try:
        # declare a new PostgreSQL connection object
        conn = connect(
            dbname="galaxy",
            user="postgres",
            host="localhost",
            password="password"
        )
        cursor = conn.cursor()

    except Exception as e:
        print(e)
        return

    sql_statement = "SELECT * FROM dataset WHERE state = \'ok\' AND deleted = False AND purged = False AND id = {} AND object_store_id = \'{}\';".format(dataset_id, objectstore_id)
    print(sql_statement)
    try:
        sql_object = sql.SQL(
            sql_statement
        )
        cursor.execute(sql_object)
        table_data = cursor.fetchall()

        for num, row in enumerate(table_data):
            print("row: ", row)
            print("\n")
            uuid = row[12]
            objectid = row[0]
            object_store_id = row[11]
            print("UUID: ", uuid)
            print("\n")
            uuid_with_dash = uuid[0:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]
            print("uuid_with_dash: ", uuid_with_dash)

            print("Object ID: ", objectid)
            print("\n")
            print("Object Store ID: ", object_store_id)
            print("\n")

            object_store_path = object_store_info[object_store_id]
            print("object_store_path:", object_store_path)
            print("\n")
            print("galaxy_dir:", galaxy_dir)
            print("\n")

            disk_sub_folder = os.path.join(*directory_hash_id(objectid))
            print("disk_sub_folder: ", disk_sub_folder)
            irods_sub_folder = os.path.join(*directory_hash_id(uuid_with_dash))
            print("irods_sub_folder: ", irods_sub_folder)

            disk_file_path = galaxy_dir + "/" + object_store_path + "/" + disk_sub_folder + "/" + "dataset_" + str(objectid) + ".dat"
            print("disk_file_path: ", disk_file_path)
            irods_file_path = irods_home + "/" + irods_sub_folder + "/" + "dataset_" + str(uuid) + ".dat"
            print("irods_file_path: ", irods_file_path)

            icommand_mkdir = "imkdir -p " + irods_sub_folder
            print("icommand_mkdir: ", icommand_mkdir)
            icommand_put = "iput " + disk_file_path + " " + irods_file_path
            print("icommand_put: ", icommand_put)

            subprocess.run([icommand_mkdir])
            time.sleep(1)
            subprocess.run([icommand_put])

    except Exception as e:
        print(e)
        return
