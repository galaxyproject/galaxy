'''From rodsKeyWdDef.hpp
'''

ALL_KW = "all"        # operation done on all replica #
COPIES_KW = "copies"    # the number of copies #
EXEC_LOCALLY_KW = "execLocally"    # execute locally #
FORCE_FLAG_KW = "forceFlag"    # force update #
CLI_IN_SVR_FIREWALL_KW = "cliInSvrFirewall"  # cli behind same firewall #
REG_CHKSUM_KW = "regChksum"    # register checksum #
VERIFY_CHKSUM_KW = "verifyChksum"   # verify checksum #
VERIFY_BY_SIZE_KW = "verifyBySize"  # verify by size - used by irsync #
OBJ_PATH_KW = "objPath"   # logical path of the object #
RESC_NAME_KW = "rescName"   # resource name #
DEST_RESC_NAME_KW = "destRescName"   # destination resource name #
DEF_RESC_NAME_KW = "defRescName"   # default resource name #
BACKUP_RESC_NAME_KW = "backupRescName"  # destination resource name #
DATA_TYPE_KW = "dataType"   # data type #
DATA_SIZE_KW = "dataSize"
CHKSUM_KW = "chksum"
ORIG_CHKSUM_KW = "orig_chksum"
VERSION_KW = "version"
FILE_PATH_KW = "filePath"   # the physical file path #
BUN_FILE_PATH_KW = "bunFilePath"  # the physical bun file path # # JMC - backport 4768
REPL_NUM_KW = "replNum"   # replica number #
WRITE_FLAG_KW = "writeFlag"   # whether it is opened for write #
REPL_STATUS_KW = "replStatus"   # status of the replica #
ALL_REPL_STATUS_KW = "allReplStatus"   # update all replStatus #
DATA_INCLUDED_KW = "dataIncluded"   # data included in the input buffer #
DATA_OWNER_KW = "dataOwner"
DATA_OWNER_ZONE_KW = "dataOwnerZone"
DATA_EXPIRY_KW = "dataExpiry"
DATA_COMMENTS_KW = "dataComments"
DATA_CREATE_KW = "dataCreate"
DATA_MODIFY_KW = "dataModify"
DATA_ACCESS_KW = "dataAccess"
DATA_ACCESS_INX_KW = "dataAccessInx"
NO_OPEN_FLAG_KW = "noOpenFlag"
PHYOPEN_BY_SIZE_KW = "phyOpenBySize"
STREAMING_KW = "streaming"
DATA_ID_KW = "dataId"
COLL_ID_KW = "collId"
DATA_MODE_KW = "dataMode"
STATUS_STRING_KW = "statusString"
DATA_MAP_ID_KW = "dataMapId"
NO_PARA_OP_KW = "noParaOpr"
LOCAL_PATH_KW = "localPath"
RSYNC_MODE_KW = "rsyncMode"
RSYNC_DEST_PATH_KW = "rsyncDestPath"
RSYNC_CHKSUM_KW = "rsyncChksum"
CHKSUM_ALL_KW = "ChksumAll"
FORCE_CHKSUM_KW = "forceChksum"
COLLECTION_KW = "collection"
ADMIN_KW = "irodsAdmin"
ADMIN_RMTRASH_KW = "irodsAdminRmTrash"
UNREG_KW = "unreg"
RMTRASH_KW = "irodsRmTrash"
RECURSIVE_OPR__KW = "recursiveOpr"
COLLECTION_TYPE_KW = "collectionType"
COLLECTION_INFO1_KW = "collectionInfo1"
COLLECTION_INFO2_KW = "collectionInfo2"
SEL_OBJ_TYPE_KW = "selObjType"
STRUCT_FILE_OPR_KW = "structFileOpr"
ALL_MS_PARAM_KW = "allMsParam"
UNREG_COLL_KW = "unregColl"
UPDATE_REPL_KW = "updateRepl"
RBUDP_TRANSFER_KW = "rbudpTransfer"
VERY_VERBOSE_KW = "veryVerbose"
RBUDP_SEND_RATE_KW = "rbudpSendRate"
RBUDP_PACK_SIZE_KW = "rbudpPackSize"
ZONE_KW = "zone"
REMOTE_ZONE_OPR_KW = "remoteZoneOpr"
REPL_DATA_OBJ_INP_KW = "replDataObjInp"
CROSS_ZONE_CREATE_KW = "replDataObjInp"  # use the same for backward compatibility #
QUERY_BY_DATA_ID_KW = "queryByDataID"
SU_CLIENT_USER_KW = "suClientUser"
RM_BUN_COPY_KW = "rmBunCopy"
KEY_WORD_KW = "keyWord"  # the msKeyValStr is a keyword #
CREATE_MODE_KW = "createMode"  # a msKeyValStr keyword #
OPEN_FLAGS_KW = "openFlags"  # a msKeyValStr keyword #
OFFSET_KW = "offset"  # a msKeyValStr keyword #
# DATA_SIZE_KW already defined #
NUM_THREADS_KW = "numThreads"  # a msKeyValStr keyword #
OPR_TYPE_KW = "oprType"  # a msKeyValStr keyword #
COLL_FLAGS_KW = "collFlags"  # a msKeyValStr keyword #
TRANSLATED_PATH_KW = "translatedPath"  # the path translated #
NO_TRANSLATE_LINKPT_KW = "noTranslateMntpt"  # don't translate mntpt #
BULK_OPR_KW = "bulkOpr"  # the bulk operation #
NON_BULK_OPR_KW = "nonBulkOpr"  # non bulk operation #
EXEC_CMD_RULE_KW = "execCmdRule"  # the rule that invoke execCmd #
EXEC_MY_RULE_KW = "execMyRule"  # the rule is invoked by rsExecMyRule #
STREAM_STDOUT_KW = "streamStdout"  # the stream stdout for execCmd #
REG_REPL_KW = "regRepl"  # register replica #
AGE_KW = "age"  # age of the file for itrim #
DRYRUN_KW = "dryrun"  # do a dry run #
ACL_COLLECTION_KW = "aclCollection"  # the collection from which the ACL should be used #
NO_CHK_COPY_LEN_KW = "noChkCopyLen"  # Don't check the len when transfering  #
TICKET_KW = "ticket"       # for ticket-based-access #
PURGE_CACHE_KW = "purgeCache"   # purge the cache copy right after the operation JMC - backport 4537
EMPTY_BUNDLE_ONLY_KW = "emptyBundleOnly"  # delete emptyBundleOnly # # JMC - backport 4552

# =-=-=-=-=-=-=-
# JMC - backport 4599
LOCK_TYPE_KW = "lockType"     # valid values are READ_LOCK_TYPE, WRITE_LOCK_TYPE and UNLOCK_TYPE #
LOCK_CMD_KW = "lockCmd"      # valid values are SET_LOCK_WAIT_CMD, SET_LOCK_CMD and GET_LOCK_CMD #
LOCK_FD_KW = "lockFd"       # Lock file desc for unlock #
MAX_SUB_FILE_KW = "maxSubFile"  # max number of files for tar file bundles #
MAX_BUNDLE_SIZE_KW = "maxBunSize"  # max size of a tar bundle in Gbs #
NO_STAGING_KW = "noStaging"

# =-=-=-=-=-=-=-
MAX_SUB_FILE_KW = "maxSubFile"  # max number of files for tar file bundles # # JMC - backport 4771

# OBJ_PATH_KW already defined #

# OBJ_PATH_KW already defined #
# COLL_NAME_KW already defined #
FILE_UID_KW = "fileUid"
FILE_OWNER_KW = "fileOwner"
FILE_GID_KW = "fileGid"
FILE_GROUP_KW = "fileGroup"
FILE_MODE_KW = "fileMode"
FILE_CTIME_KW = "fileCtime"
FILE_MTIME_KW = "fileMtime"
FILE_SOURCE_PATH_KW = "fileSourcePath"
EXCLUDE_FILE_KW = "excludeFile"

# The following are the keyWord definition for the rescCond key/value pair #
# RESC_NAME_KW is defined above #

RESC_ZONE_KW = "zoneName"
RESC_LOC_KW = "rescLoc"  # resc_net in DB #
RESC_TYPE_KW = "rescType"
RESC_CLASS_KW = "rescClass"
RESC_VAULT_PATH_KW = "rescVaultPath"  # resc_def_path in DB #
RESC_STATUS_KW = "rescStatus"
GATEWAY_ADDR_KW = "gateWayAddr"
RESC_MAX_OBJ_SIZE_KW = "rescMaxObjSize"
FREE_SPACE_KW = "freeSpace"
FREE_SPACE_TIME_KW = "freeSpaceTime"
FREE_SPACE_TIMESTAMP_KW = "freeSpaceTimeStamp"
RESC_TYPE_INX_KW = "rescTypeInx"
RESC_CLASS_INX_KW = "rescClassInx"
RESC_ID_KW = "rescId"
RESC_COMMENTS_KW = "rescComments"
RESC_CREATE_KW = "rescCreate"
RESC_MODIFY_KW = "rescModify"

# The following are the keyWord definition for the userCond key/value pair #

USER_NAME_CLIENT_KW = "userNameClient"
RODS_ZONE_CLIENT_KW = "rodsZoneClient"
HOST_CLIENT_KW = "hostClient"
CLIENT_ADDR_KW = "clientAddr"
USER_TYPE_CLIENT_KW = "userTypeClient"
AUTH_STR_CLIENT_KW = "authStrClient"  # user distin name #
USER_AUTH_SCHEME_CLIENT_KW = "userAuthSchemeClient"
USER_INFO_CLIENT_KW = "userInfoClient"
USER_COMMENT_CLIENT_KW = "userCommentClient"
USER_CREATE_CLIENT_KW = "userCreateClient"
USER_MODIFY_CLIENT_KW = "userModifyClient"
USER_NAME_PROXY_KW = "userNameProxy"
RODS_ZONE_PROXY_KW = "rodsZoneProxy"
HOST_PROXY_KW = "hostProxy"
USER_TYPE_PROXY_KW = "userTypeProxy"
AUTH_STR_PROXY_KW = "authStrProxy"  # dn #
USER_AUTH_SCHEME_PROXY_KW = "userAuthSchemeProxy"
USER_INFO_PROXY_KW = "userInfoProxy"
USER_COMMENT_PROXY_KW = "userCommentProxy"
USER_CREATE_PROXY_KW = "userCreateProxy"
USER_MODIFY_PROXY_KW = "userModifyProxy"
ACCESS_PERMISSION_KW = "accessPermission"
NO_CHK_FILE_PERM_KW = "noChkFilePerm"

# The following are the keyWord definition for the collCond key/value pair #

COLL_NAME_KW = "collName"
COLL_PARENT_NAME_KW = "collParentName"  # parent_coll_name in DB  #
COLL_OWNER_NAME_KW = "collOwnername"
COLL_OWNER_ZONE_KW = "collOwnerZone"
COLL_MAP_ID_KW = "collMapId"
COLL_INHERITANCE_KW = "collInheritance"
COLL_COMMENTS_KW = "collComments"
COLL_EXPIRY_KW = "collExpiry"
COLL_CREATE_KW = "collCreate"
COLL_MODIFY_KW = "collModify"
COLL_ACCESS_KW = "collAccess"
COLL_ACCESS_INX_KW = "collAccessInx"
COLL_ID_KW = "collId"

# The following are the keyWord definitions for the keyValPair_t input to chlModRuleExec.
#
RULE_NAME_KW = "ruleName"
RULE_REI_FILE_PATH_KW = "reiFilePath"
RULE_USER_NAME_KW = "userName"
RULE_EXE_ADDRESS_KW = "exeAddress"
RULE_EXE_TIME_KW = "exeTime"
RULE_EXE_FREQUENCY_KW = "exeFrequency"
RULE_PRIORITY_KW = "priority"
RULE_ESTIMATE_EXE_TIME_KW = "estimateExeTime"
RULE_NOTIFICATION_ADDR_KW = "notificationAddr"
RULE_LAST_EXE_TIME_KW = "lastExeTime"
RULE_EXE_STATUS_KW = "exeStatus"


EXCLUDE_FILE_KW = "excludeFile"
AGE_KW = "age"  # age of the file for itrim #

# =-=-=-=-=-=-=-
# irods general keywords definitions
RESC_HIER_STR_KW = "resc_hier"
DEST_RESC_HIER_STR_KW = "dest_resc_hier"
IN_PDMO_KW = "in_pdmo"
STAGE_OBJ_KW = "stage_object"
SYNC_OBJ_KW = "sync_object"
IN_REPL_KW = "in_repl"

# =-=-=-=-=-=-=-
# irods tcp keyword definitions
SOCKET_HANDLE_KW = "tcp_socket_handle"

# =-=-=-=-=-=-=-
# irods ssl keyword definitions
SSL_HOST_KW = "ssl_host"
SSL_SHARED_SECRET_KW = "ssl_shared_secret"
SSL_KEY_SIZE_KW = "ssl_key_size"
SSL_SALT_SIZE_KW = "ssl_salt_size"
SSL_NUM_HASH_ROUNDS_KW = "ssl_num_hash_rounds"
SSL_ALGORITHM_KW = "ssl_algorithm"

# =-=-=-=-=-=-=-
# irods data_object keyword definitions
PHYSICAL_PATH_KW = "physical_path"
MODE_KW = "mode_kw"
FLAGS_KW = "flags_kw"
# borrowed RESC_HIER_STR_KW

# =-=-=-=-=-=-=-
# irods file_object keyword definitions
LOGICAL_PATH_KW = "logical_path"
FILE_DESCRIPTOR_KW = "file_descriptor"
L1_DESC_IDX_KW = "l1_desc_idx"
SIZE_KW = "file_size"
REPL_REQUESTED_KW = "repl_requested"
# borrowed IN_PDMO_KW

# =-=-=-=-=-=-=-
# irods structured_object keyword definitions
HOST_ADDR_KW = "host_addr"
ZONE_NAME_KW = "zone_name"
PORT_NUM_KW = "port_num"
SUB_FILE_PATH_KW = "sub_file_path"
# borrowed OFFSET_KW
# borrowed DATA_TYPE_KW
# borrowed OPR_TYPE_KW

# =-=-=-=-=-=-=-
# irods spec coll keyword definitions
SPEC_COLL_CLASS_KW = "spec_coll_class"
SPEC_COLL_TYPE_KW = "spec_coll_type"
SPEC_COLL_OBJ_PATH_KW = "spec_coll_obj_path"
SPEC_COLL_RESOURCE_KW = "spec_coll_resource"
SPEC_COLL_RESC_HIER_KW = "spec_coll_resc_hier"
SPEC_COLL_PHY_PATH_KW = "spec_coll_phy_path"
SPEC_COLL_CACHE_DIR_KW = "spec_coll_cache_dir"
SPEC_COLL_CACHE_DIRTY = "spec_coll_cache_dirty"
SPEC_COLL_REPL_NUM = "spec_coll_repl_num"


DISABLE_STRICT_ACL_KW = "disable_strict_acls"
