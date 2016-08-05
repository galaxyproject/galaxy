# if you're copying these from the docs, you might find the following regex helpful:
# s/\(\w\+\)\s\+\(-\d\+\)/class \1(SystemException):\r    code = \2/g

class PycommandsException(Exception):
    pass

class NetworkException(PycommandsException):
    pass

class DoesNotExist(PycommandsException):
    pass

class DataObjectDoesNotExist(PycommandsException):
    pass

class CollectionDoesNotExist(PycommandsException):
    pass

class UserDoesNotExist(PycommandsException):
    pass

class UserGroupDoesNotExist(PycommandsException):
    pass

class ResourceDoesNotExist(PycommandsException):
    pass

class QueryException(PycommandsException):
    pass

class NoResultFound(QueryException):
    pass

class MultipleResultsFound(QueryException):
    pass

class iRODSExceptionMeta(type):
    codes = {}
    def __init__(self, name, bases, attrs):
        if 'code' in attrs:
            iRODSExceptionMeta.codes[attrs['code']] = self

class iRODSException(Exception):
    __metaclass__ = iRODSExceptionMeta
    pass

def get_exception_by_code(code):
    return iRODSExceptionMeta.codes[code]()

class SystemException(iRODSException):
    pass

class SYS_SOCK_OPEN_ERR(SystemException):
    code = -1000
class SYS_SOCK_BIND_ERR(SystemException):
    code = -2000
class SYS_SOCK_ACCEPT_ERR(SystemException):
    code = -3000
class SYS_HEADER_READ_LEN_ERR(SystemException):
    code = -4000
class SYS_HEADER_WRITE_LEN_ERR(SystemException):
    code = -5000
class SYS_HEADER_TPYE_LEN_ERR(SystemException):
    code = -6000
class SYS_CAUGHT_SIGNAL(SystemException):
    code = -7000
class SYS_GETSTARTUP_PACK_ERR(SystemException):
    code = -8000
class SYS_EXCEED_CONNECT_CNT(SystemException):
    code = -9000
class SYS_USER_NOT_ALLOWED_TO_CONN(SystemException):
    code = -10000
class SYS_READ_MSG_BODY_INPUT_ERR(SystemException):
    code = -11000
class SYS_UNMATCHED_API_NUM(SystemException):
    code = -12000
class SYS_NO_API_PRIV(SystemException):
    code = -13000
class SYS_API_INPUT_ERR(SystemException):
    code = -14000
class SYS_PACK_INSTRUCT_FORMAT_ERR(SystemException):
    code = -15000
class SYS_MALLOC_ERR(SystemException):
    code = -16000
class SYS_GET_HOSTNAME_ERR(SystemException):
    code = -17000
class SYS_OUT_OF_FILE_DESC(SystemException):
    code = -18000
class SYS_FILE_DESC_OUT_OF_RANGE(SystemException):
    code = -19000
class SYS_UNRECOGNIZED_REMOTE_FLAG(SystemException):
    code = -20000
class SYS_INVALID_SERVER_HOST(SystemException):
    code = -21000
class SYS_SVR_TO_SVR_CONNECT_FAILED(SystemException):
    code = -22000
class SYS_BAD_FILE_DESCRIPTOR(SystemException):
    code = -23000
class SYS_INTERNAL_NULL_INPUT_ERR(SystemException):
    code = -24000
class SYS_CONFIG_FILE_ERR(SystemException):
    code = -25000
class SYS_INVALID_ZONE_NAME(SystemException):
    code = -26000
class SYS_COPY_LEN_ERR(SystemException):
    code = -27000
class SYS_PORT_COOKIE_ERR(SystemException):
    code = -28000
class SYS_KEY_VAL_TABLE_ERR(SystemException):
    code = -29000
class SYS_INVALID_RESC_TYPE(SystemException):
    code = -30000
class SYS_INVALID_FILE_PATH(SystemException):
    code = -31000
class SYS_INVALID_RESC_INPUT(SystemException):
    code = -32000
class SYS_INVALID_PORTAL_OPR(SystemException):
    code = -33000
class SYS_PARA_OPR_NO_SUPPORT(SystemException):
    code = -34000
class SYS_INVALID_OPR_TYPE(SystemException):
    code = -35000
class SYS_NO_PATH_PERMISSION(SystemException):
    code = -36000
class SYS_NO_ICAT_SERVER_ERR(SystemException):
    code = -37000
class SYS_AGENT_INIT_ERR(SystemException):
    code = -38000
class SYS_PROXYUSER_NO_PRIV(SystemException):
    code = -39000
class SYS_NO_DATA_OBJ_PERMISSION(SystemException):
    code = -40000
class SYS_DELETE_DISALLOWED(SystemException):
    code = -41000
class SYS_OPEN_REI_FILE_ERR(SystemException):
    code = -42000
class SYS_NO_RCAT_SERVER_ERR(SystemException):
    code = -43000
class SYS_UNMATCH_PACK_INSTRUCTI_NAME(SystemException):
    code = -44000
class SYS_SVR_TO_CLI_MSI_NO_EXIST(SystemException):
    code = -45000
class SYS_COPY_ALREADY_IN_RESC(SystemException):
    code = -46000
class SYS_RECONN_OPR_MISMATCH(SystemException):
    code = -47000
class SYS_INPUT_PERM_OUT_OF_RANGE(SystemException):
    code = -48000
class SYS_FORK_ERROR(SystemException):
    code = -49000
class SYS_PIPE_ERROR(SystemException):
    code = -50000
class SYS_EXEC_CMD_STATUS_SZ_ERROR(SystemException):
    code = -51000
class SYS_PATH_IS_NOT_A_FILE(SystemException):
    code = -52000
class SYS_UNMATCHED_SPEC_COLL_TYPE(SystemException):
    code = -53000
class SYS_TOO_MANY_QUERY_RESULT(SystemException):
    code = -54000
class SYS_SPEC_COLL_NOT_IN_CACHE(SystemException):
    code = -55000
class SYS_SPEC_COLL_OBJ_NOT_EXIST(SystemException):
    code = -56000
class SYS_REG_OBJ_IN_SPEC_COLL(SystemException):
    code = -57000
class SYS_DEST_SPEC_COLL_SUB_EXIST(SystemException):
    code = -58000
class SYS_SRC_DEST_SPEC_COLL_CONFLICT(SystemException):
    code = -59000
class SYS_UNKNOWN_SPEC_COLL_CLASS(SystemException):
    code = -60000
class SYS_DUPLICATE_XMSG_TICKET(SystemException):
    code = -61000
class SYS_UNMATCHED_XMSG_TICKET(SystemException):
    code = -62000
class SYS_NO_XMSG_FOR_MSG_NUMBER(SystemException):
    code = -63000 
class SYS_COLLINFO_2_FORMAT_ERR(SystemException):
    code = -64000 
class SYS_CACHE_STRUCT_FILE_RESC_ERR(SystemException):
    code = -65000 
class SYS_NOT_SUPPORTED(SystemException):
    code = -66000
class SYS_TAR_STRUCT_FILE_EXTRACT_ERR(SystemException):
    code = -67000
class SYS_STRUCT_FILE_DESC_ERR(SystemException):
    code = -68000
class SYS_TAR_OPEN_ERR(SystemException):
    code = -69000
class SYS_TAR_EXTRACT_ALL_ERR(SystemException):
    code = -70000
class SYS_TAR_CLOSE_ERR(SystemException):
    code = -71000
class SYS_STRUCT_FILE_PATH_ERR(SystemException):
    code = -72000
class SYS_MOUNT_MOUNTED_COLL_ERR(SystemException):
    code = -73000
class SYS_COLL_NOT_MOUNTED_ERR(SystemException):
    code = -74000
class SYS_STRUCT_FILE_BUSY_ERR(SystemException):
    code = -75000
class SYS_STRUCT_FILE_INMOUNTED_COLL(SystemException):
    code = -76000
class SYS_COPY_NOT_EXIST_IN_RESC(SystemException):
    code = -77000
class SYS_RESC_DOES_NOT_EXIST(SystemException):
    code = -78000
class SYS_COLLECTION_NOT_EMPTY(SystemException):
    code = -79000
class SYS_OBJ_TYPE_NOT_STRUCT_FILE(SystemException):
    code = -80000
class SYS_WRONG_RESC_POLICY_FOR_BUN_OPR(SystemException):
    code = -81000
class SYS_DIR_IN_VAULT_NOT_EMPTY(SystemException):
    code = -82000
class SYS_OPR_FLAG_NOT_SUPPORT(SystemException):
    code = -83000
class SYS_TAR_APPEND_ERR(SystemException):
    code = -84000
class SYS_INVALID_PROTOCOL_TYPE(SystemException):
    code = -85000
class SYS_UDP_CONNECT_ERR(SystemException):
    code = -86000
class SYS_UDP_TRANSFER_ERR(SystemException):
    code = -89000
class SYS_UDP_NO_SUPPORT_ERR(SystemException):
    code = -90000
class SYS_READ_MSG_BODY_LEN_ERR(SystemException):
    code = -91000
class CROSS_ZONE_SOCK_CONNECT_ERR(SystemException):
    code = -92000
class SYS_NO_FREE_RE_THREAD(SystemException):
    code = -93000
class SYS_BAD_RE_THREAD_INX(SystemException):
    code = -94000
class SYS_CANT_DIRECTLY_ACC_COMPOUND_RESC(SystemException):
    code = -95000
class SYS_SRC_DEST_RESC_COMPOUND_TYPE(SystemException):
    code = -96000
class SYS_CACHE_RESC_NOT_ON_SAME_HOST(SystemException):
    code = -97000
class SYS_NO_CACHE_RESC_IN_GRP(SystemException):
    code = -98000
class SYS_UNMATCHED_RESC_IN_RESC_GRP(SystemException):
    code = -99000
class SYS_CANT_MV_BUNDLE_DATA_TO_TRASH(SystemException):
    code = -100000
class SYS_CANT_MV_BUNDLE_DATA_BY_COPY(SystemException):
    code = -101000
class SYS_EXEC_TAR_ERR(SystemException):
    code = -102000
class SYS_CANT_CHKSUM_COMP_RESC_DATA(SystemException):
    code = -103000
class SYS_CANT_CHKSUM_BUNDLED_DATA(SystemException):
    code = -104000
class SYS_RESC_IS_DOWN(SystemException):
    code = -105000
class SYS_UPDATE_REPL_INFO_ERR(SystemException):
    code = -106000
class SYS_COLL_LINK_PATH_ERR(SystemException):
    code = -107000
class SYS_LINK_CNT_EXCEEDED_ERR(SystemException):
    code = -108000
class SYS_CROSS_ZONE_MV_NOT_SUPPORTED(SystemException):
    code = -109000
class SYS_RESC_QUOTA_EXCEEDED(SystemException):
    code = -110000

class UserInputException(iRODSException):
    pass

class USER_AUTH_SCHEME_ERR(UserInputException):
    code = -300000
class USER_AUTH_STRING_EMPTY(UserInputException):
    code = -301000
class USER_RODS_HOST_EMPTY(UserInputException):
    code = -302000
class USER_RODS_HOSTNAME_ERR(UserInputException):
    code = -303000
class USER_SOCK_OPEN_ERR(UserInputException):
    code = -304000
class USER_SOCK_CONNECT_ERR(UserInputException):
    code = -305000
class USER_STRLEN_TOOLONG(UserInputException):
    code = -306000
class USER_API_INPUT_ERR(UserInputException):
    code = -307000
class USER_PACKSTRUCT_INPUT_ERR(UserInputException):
    code = -308000
class USER_NO_SUPPORT_ERR(UserInputException):
    code = -309000
class USER_FILE_DOES_NOT_EXIST(UserInputException):
    code = -310000
class USER_FILE_TOO_LARGE(UserInputException):
    code = -311000
class OVERWITE_WITHOUT_FORCE_FLAG(UserInputException):
    code = -312000
class UNMATCHED_KEY_OR_INDEX(UserInputException):
    code = -313000
class USER_CHKSUM_MISMATCH(UserInputException):
    code = -314000
class USER_BAD_KEYWORD_ERR(UserInputException):
    code = -315000
class USER__NULL_INPUT_ERR(UserInputException):
    code = -316000
class USER_INPUT_PATH_ERR(UserInputException):
    code = -317000
class USER_INPUT_OPTION_ERR(UserInputException):
    code = -318000
class USER_INVALID_USERNAME_FORMAT(UserInputException):
    code = -319000
class USER_DIRECT_RESC_INPUT_ERR(UserInputException):
    code = -320000
class USER_NO_RESC_INPUT_ERR(UserInputException):
    code = -321000
class USER_PARAM_LABEL_ERR(UserInputException):
    code = -322000
class USER_PARAM_TYPE_ERR(UserInputException):
    code = -323000
class BASE64_BUFFER_OVERFLOW(UserInputException):
    code = -324000
class BASE64_INVALID_PACKET(UserInputException):
    code = -325000
class USER_MSG_TYPE_NO_SUPPORT(UserInputException):
    code = -326000
class USER_RSYNC_NO_MODE_INPUT_ERR(UserInputException):
    code = -337000
class USER_OPTION_INPUT_ERR(UserInputException):
    code = -338000
class SAME_SRC_DEST_PATHS_ERR(UserInputException):
    code = -339000
class USER_RESTART_FILE_INPUT_ERR(UserInputException):
    code = -340000
class RESTART_OPR_FAILED(UserInputException):
    code = -341000
class BAD_EXEC_CMD_PATH(UserInputException):
    code = -342000
class EXEC_CMD_OUTPUT_TOO_LARGE(UserInputException):
    code = -343000
class EXEC_CMD_ERROR(UserInputException):
    code = -344000
class BAD_INPUT_DESC_INDEX(UserInputException):
    code = -345000
class USER_PATH_EXCEEDS_MAX(UserInputException):
    code = -346000
class USER_SOCK_CONNECT_TIMEDOUT(UserInputException):
    code = -347000
class USER_API_VERSION_MISMATCH(UserInputException):
    code = -348000
class USER_INPUT_FORMAT_ERR(UserInputException):
    code = -349000
class USER_ACCESS_DENIED(UserInputException):
    code = -350000
class CANT_RM_MV_BUNDLE_TYPE(UserInputException):
    code = -351000
class NO_MORE_RESULT(UserInputException):
    code = -352000
class NO_KEY_WD_IN_MS_INP_STR(UserInputException):
    code = -353000
class CANT_RM_NON_EMPTY_HOME_COLL(UserInputException):
    code = -354000
class CANT_UNREG_IN_VAULT_FILE(UserInputException):
    code = -355000
class NO_LOCAL_FILE_RSYNC_IN_MSI(UserInputException):
    code = -356000

class FileDriverException(iRODSException):
    pass

class FILE_INDEX_LOOKUP_ERR(FileDriverException):
    code = -500000 
class UNIX_FILE_OPEN_ERR(FileDriverException):
    code = -510000 
class UNIX_FILE_CREATE_ERR(FileDriverException):
    code = -511000 
class UNIX_FILE_READ_ERR(FileDriverException):
    code = -512000 
class UNIX_FILE_WRITE_ERR(FileDriverException):
    code = -513000 
class UNIX_FILE_CLOSE_ERR(FileDriverException):
    code = -514000 
class UNIX_FILE_UNLINK_ERR(FileDriverException):
    code = -515000 
class UNIX_FILE_STAT_ERR(FileDriverException):
    code = -516000 
class UNIX_FILE_FSTAT_ERR(FileDriverException):
    code = -517000 
class UNIX_FILE_LSEEK_ERR(FileDriverException):
    code = -518000 
class UNIX_FILE_FSYNC_ERR(FileDriverException):
    code = -519000 
class UNIX_FILE_MKDIR_ERR(FileDriverException):
    code = -520000 
class UNIX_FILE_RMDIR_ERR(FileDriverException):
    code = -521000 
class UNIX_FILE_OPENDIR_ERR(FileDriverException):
    code = -522000 
class UNIX_FILE_CLOSEDIR_ERR(FileDriverException):
    code = -523000 
class UNIX_FILE_READDIR_ERR(FileDriverException):
    code = -524000 
class UNIX_FILE_STAGE_ERR(FileDriverException):
    code = -525000 
class UNIX_FILE_GET_FS_FREESPACE_ERR(FileDriverException):
    code = -526000 
class UNIX_FILE_CHMOD_ERR(FileDriverException):
    code = -527000 
class UNIX_FILE_RENAME_ERR(FileDriverException):
    code = -528000 
class UNIX_FILE_TRUNCATE_ERR(FileDriverException):
    code = -529000 
class UNIX_FILE_LINK_ERR(FileDriverException):
    code = -530000

class UniversalMSSDriverException(FileDriverException):
    pass

class UNIV_MSS_SYNCTOARCH_ERR(UniversalMSSDriverException):
    code = -550000
class UNIV_MSS_STAGETOCACHE_ERR(UniversalMSSDriverException):
    code = -551000
class UNIV_MSS_UNLINK_ERR(UniversalMSSDriverException):
    code = -552000
class UNIV_MSS_MKDIR_ERR(UniversalMSSDriverException):
    code = -553000
class UNIV_MSS_CHMOD_ERR(UniversalMSSDriverException):
    code = -554000
class UNIV_MSS_STAT_ERR(UniversalMSSDriverException):
    code = -555000

class HPSSDriverException(FileDriverException):
    pass

class HPSS_AUTH_NOT_SUPPORTED(HPSSDriverException):
    code = -600000
class HPSS_FILE_OPEN_ERR(HPSSDriverException):
    code = -610000
class HPSS_FILE_CREATE_ERR(HPSSDriverException):
    code = -611000
class HPSS_FILE_READ_ERR(HPSSDriverException):
    code = -612000
class HPSS_FILE_WRITE_ERR(HPSSDriverException):
    code = -613000
class HPSS_FILE_CLOSE_ERR(HPSSDriverException):
    code = -614000
class HPSS_FILE_UNLINK_ERR(HPSSDriverException):
    code = -615000
class HPSS_FILE_STAT_ERR(HPSSDriverException):
    code = -616000
class HPSS_FILE_FSTAT_ERR(HPSSDriverException):
    code = -617000
class HPSS_FILE_LSEEK_ERR(HPSSDriverException):
    code = -618000
class HPSS_FILE_FSYNC_ERR(HPSSDriverException):
    code = -619000
class HPSS_FILE_MKDIR_ERR(HPSSDriverException):
    code = -620000
class HPSS_FILE_RMDIR_ERR(HPSSDriverException):
    code = -621000
class HPSS_FILE_OPENDIR_ERR(HPSSDriverException):
    code = -622000
class HPSS_FILE_CLOSEDIR_ERR(HPSSDriverException):
    code = -623000
class HPSS_FILE_READDIR_ERR(HPSSDriverException):
    code = -624000
class HPSS_FILE_STAGE_ERR(HPSSDriverException):
    code = -625000
class HPSS_FILE_GET_FS_FREESPACE_ERR(HPSSDriverException):
    code = -626000
class HPSS_FILE_CHMOD_ERR(HPSSDriverException):
    code = -627000
class HPSS_FILE_RENAME_ERR(HPSSDriverException):
    code = -628000
class HPSS_FILE_TRUNCATE_ERR(HPSSDriverException):
    code = -629000
class HPSS_FILE_LINK_ERR(HPSSDriverException):
    code = -630000
class HPSS_AUTH_ERR(HPSSDriverException):
    code = -631000
class HPSS_WRITE_LIST_ERR(HPSSDriverException):
    code = -632000
class HPSS_READ_LIST_ERR(HPSSDriverException):
    code = -633000
class HPSS_TRANSFER_ERR(HPSSDriverException):
    code = -634000
class HPSS_MOVER_PROT_ERR(HPSSDriverException):
    code = -635000

class AmazonS3Exception(FileDriverException):
    pass

class S3_INIT_ERROR(AmazonS3Exception):
    code = -701000
class S3_PUT_ERROR(AmazonS3Exception):
    code = -702000
class S3_GET_ERROR(AmazonS3Exception):
    code = -703000
class S3_FILE_UNLINK_ERR(AmazonS3Exception):
    code = -715000
class S3_FILE_STAT_ERR(AmazonS3Exception):
    code = -716000
class S3_FILE_COPY_ERR(AmazonS3Exception):
    code = -717000

class CatalogLibraryException(iRODSException):
    pass

class CATALOG_NOT_CONNECTED(CatalogLibraryException):
    code = -801000
class CAT_ENV_ERR(CatalogLibraryException):
    code = -802000
class CAT_CONNECT_ERR(CatalogLibraryException):
    code = -803000
class CAT_DISCONNECT_ERR(CatalogLibraryException):
    code = -804000
class CAT_CLOSE_ENV_ERR(CatalogLibraryException):
    code = -805000
class CAT_SQL_ERR(CatalogLibraryException):
    code = -806000
class CAT_GET_ROW_ERR(CatalogLibraryException):
    code = -807000
class CAT_NO_ROWS_FOUND(CatalogLibraryException):
    code = -808000
class CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME(CatalogLibraryException):
    code = -809000
class CAT_INVALID_RESOURCE_TYPE(CatalogLibraryException):
    code = -810000
class CAT_INVALID_RESOURCE_CLASS(CatalogLibraryException):
    code = -811000
class CAT_INVALID_RESOURCE_NET_ADDR(CatalogLibraryException):
    code = -812000
class CAT_INVALID_RESOURCE_VAULT_PATH(CatalogLibraryException):
    code = -813000
class CAT_UNKNOWN_COLLECTION(CatalogLibraryException):
    code = -814000
class CAT_INVALID_DATA_TYPE(CatalogLibraryException):
    code = -815000
class CAT_INVALID_ARGUMENT(CatalogLibraryException):
    code = -816000
class CAT_UNKNOWN_FILE(CatalogLibraryException):
    code = -817000
class CAT_NO_ACCESS_PERMISSION(CatalogLibraryException):
    code = -818000
class CAT_SUCCESS_BUT_WITH_NO_INFO(CatalogLibraryException):
    code = -819000
class CAT_INVALID_USER_TYPE(CatalogLibraryException):
    code = -820000
class CAT_COLLECTION_NOT_EMPTY(CatalogLibraryException):
    code = -821000
class CAT_TOO_MANY_TABLES(CatalogLibraryException):
    code = -822000
class CAT_UNKNOWN_TABLE(CatalogLibraryException):
    code = -823000
class CAT_NOT_OPEN(CatalogLibraryException):
    code = -824000
class CAT_FAILED_TO_LINK_TABLES(CatalogLibraryException):
    code = -825000
class CAT_INVALID_AUTHENTICATION(CatalogLibraryException):
    code = -826000
class CAT_INVALID_USER(CatalogLibraryException):
    code = -827000
class CAT_INVALID_ZONE(CatalogLibraryException):
    code = -828000
class CAT_INVALID_GROUP(CatalogLibraryException):
    code = -829000
class CAT_INSUFFICIENT_PRIVILEGE_LEVEL(CatalogLibraryException):
    code = -830000
class CAT_INVALID_RESOURCE(CatalogLibraryException):
    code = -831000
class CAT_INVALID_CLIENT_USER(CatalogLibraryException):
    code = -832000
class CAT_NAME_EXISTS_AS_COLLECTION(CatalogLibraryException):
    code = -833000
class CAT_NAME_EXISTS_AS_DATAOBJ(CatalogLibraryException):
    code = -834000
class CAT_RESOURCE_NOT_EMPTY(CatalogLibraryException):
    code = -835000
class CAT_NOT_A_DATAOBJ_AND_NOT_A_COLLECTION(CatalogLibraryException):
    code = -836000
class CAT_RECURSIVE_MOVE(CatalogLibraryException):
    code = -837000
class CAT_LAST_REPLICA(CatalogLibraryException):
    code = -838000
class CAT_OCI_ERROR(CatalogLibraryException):
    code = -839000
class CAT_PASSWORD_EXPIRED(CatalogLibraryException):
    code = -840000
class CAT_PASSWORD_ENCODING_ERROR(CatalogLibraryException):
    code = -850000
class CAT_TABLE_ACCESS_DENIED(CatalogLibraryException):
    code = -851000

class RDSException(iRODSException):
    pass

class RDA_NOT_COMPILED_IN(RDSException):
    code = -880000
class RDA_NOT_CONNECTED(RDSException):
    code = -881000
class RDA_ENV_ERR(RDSException):
    code = -882000
class RDA_CONNECT_ERR(RDSException):
    code = -883000
class RDA_DISCONNECT_ERR(RDSException):
    code = -884000
class RDA_CLOSE_ENV_ERR(RDSException):
    code = -885000
class RDA_SQL_ERR(RDSException):
    code = -886000
class RDA_CONFIG_FILE_ERR(RDSException):
    code = -887000
class RDA_ACCESS_PROHIBITED(RDSException):
    code = -888000
class RDA_NAME_NOT_FOUND(RDSException):
    code = -889000

class MiscException(iRODSException):
    pass

class FILE_OPEN_ERR(MiscException):
    code = -900000
class FILE_READ_ERR(MiscException):
    code = -901000
class FILE_WRITE_ERR(MiscException):
    code = -902000
class PASSWORD_EXCEEDS_MAX_SIZE(MiscException):
    code = -903000
class ENVIRONMENT_VAR_HOME_NOT_DEFINED(MiscException):
    code = -904000
class UNABLE_TO_STAT_FILE(MiscException):
    code = -905000
class AUTH_FILE_NOT_ENCRYPTED(MiscException):
    code = -906000
class AUTH_FILE_DOES_NOT_EXIST(MiscException):
    code = -907000
class UNLINK_FAILED(MiscException):
    code = -908000
class NO_PASSWORD_ENTERED(MiscException):
    code = -909000
class REMOTE_SERVER_AUTHENTICATION_FAILURE(MiscException):
    code = -910000
class REMOTE_SERVER_AUTH_NOT_PROVIDED(MiscException):
    code = -911000
class REMOTE_SERVER_AUTH_EMPTY(MiscException):
    code = -912000
class REMOTE_SERVER_SID_NOT_DEFINED(MiscException):
    code = -913000

class GSIKRBException(iRODSException):
    pass

class GSIException(GSIKRBException):
    pass

class GSI_NOT_COMPILED_IN(GSIException):
    code = -921000
class GSI_NOT_BUILT_INTO_CLIENT(GSIException):
    code = -922000
class GSI_NOT_BUILT_INTO_SERVER(GSIException):
    code = -923000
class GSI_ERROR_IMPORT_NAME(GSIException):
    code = -924000
class GSI_ERROR_INIT_SECURITY_CONTEXT(GSIException):
    code = -925000
class GSI_ERROR_SENDING_TOKEN_LENGTH(GSIException):
    code = -926000
class GSI_ERROR_READING_TOKEN_LENGTH(GSIException):
    code = -927000
class GSI_ERROR_TOKEN_TOO_LARGE(GSIException):
    code = -928000
class GSI_ERROR_BAD_TOKEN_RCVED(GSIException):
    code = -929000
class GSI_SOCKET_READ_ERROR(GSIException):
    code = -930000
class GSI_PARTIAL_TOKEN_READ(GSIException):
    code = -931000
class GSI_SOCKET_WRITE_ERROR(GSIException):
    code = -932000
class GSI_ERROR_FROM_GSI_LIBRARY(GSIException):
    code = -933000
class GSI_ERROR_IMPORTING_NAME(GSIException):
    code = -934000
class GSI_ERROR_ACQUIRING_CREDS(GSIException):
    code = -935000
class GSI_ACCEPT_SEC_CONTEXT_ERROR(GSIException):
    code = -936000
class GSI_ERROR_DISPLAYING_NAME(GSIException):
    code = -937000
class GSI_ERROR_RELEASING_NAME(GSIException):
    code = -938000
class GSI_DN_DOES_NOT_MATCH_USER(GSIException):
    code = -939000
class GSI_QUERY_INTERNAL_ERROR(GSIException):
    code = -940000
class GSI_NO_MATCHING_DN_FOUND(GSIException):
    code = -941000
class GSI_MULTIPLE_MATCHING_DN_FOUND(GSIException):
    code = -942000

class KRBException(GSIKRBException):
    pass

class KRB_NOT_COMPILED_IN(KRBException):
    code = -951000
class KRB_NOT_BUILT_INTO_CLIENT(KRBException):
    code = -952000
class KRB_NOT_BUILT_INTO_SERVER(KRBException):
    code = -953000
class KRB_ERROR_IMPORT_NAME(KRBException):
    code = -954000
class KRB_ERROR_INIT_SECURITY_CONTEXT(KRBException):
    code = -955000
class KRB_ERROR_SENDING_TOKEN_LENGTH(KRBException):
    code = -956000
class KRB_ERROR_READING_TOKEN_LENGTH(KRBException):
    code = -957000
class KRB_ERROR_TOKEN_TOO_LARGE(KRBException):
    code = -958000
class KRB_ERROR_BAD_TOKEN_RCVED(KRBException):
    code = -959000
class KRB_SOCKET_READ_ERROR(KRBException):
    code = -960000
class KRB_PARTIAL_TOKEN_READ(KRBException):
    code = -961000
class KRB_SOCKET_WRITE_ERROR(KRBException):
    code = -962000
class KRB_ERROR_FROM_KRB_LIBRARY(KRBException):
    code = -963000
class KRB_ERROR_IMPORTING_NAME(KRBException):
    code = -964000
class KRB_ERROR_ACQUIRING_CREDS(KRBException):
    code = -965000
class KRB_ACCEPT_SEC_CONTEXT_ERROR(KRBException):
    code = -966000
class KRB_ERROR_DISPLAYING_NAME(KRBException):
    code = -967000
class KRB_ERROR_RELEASING_NAME(KRBException):
    code = -968000
class KRB_USER_DN_NOT_FOUND(KRBException):
    code = -969000
class KRB_NAME_MATCHES_MULTIPLE_USERS(KRBException):
    code = -970000
class KRB_QUERY_INTERNAL_ERROR(KRBException):
    code = -971000

class RuleEngineException(iRODSException):
    pass

class OBJPATH_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1000000
class RESCNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1001000
class DATATYPE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1002000
class DATASIZE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1003000
class CHKSUM_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1004000
class VERSION_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1005000
class FILEPATH_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1006000
class REPLNUM_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1007000
class REPLSTATUS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1008000
class DATAOWNER_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1009000
class DATAOWNERZONE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1010000
class DATAEXPIRY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1011000
class DATACOMMENTS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1012000
class DATACREATE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1013000
class DATAMODIFY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1014000
class DATAACCESS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1015000
class DATAACCESSINX_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1016000
class NO_RULE_FOUND_ERR(RuleEngineException):
    code = -1017000
class NO_MORE_RULES_ERR(RuleEngineException):
    code = -1018000
class UNMATCHED_ACTION_ERR(RuleEngineException):
    code = -1019000
class RULES_FILE_READ_ERROR(RuleEngineException):
    code = -1020000
class ACTION_ARG_COUNT_MISMATCH(RuleEngineException):
    code = -1021000
class MAX_NUM_OF_ARGS_IN_ACTION_EXCEEDED(RuleEngineException):
    code = -1022000
class UNKNOWN_PARAM_IN_RULE_ERR(RuleEngineException):
    code = -1023000
class DESTRESCNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1024000
class BACKUPRESCNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1025000
class DATAID_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1026000
class COLLID_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1027000
class RESCGROUPNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1028000
class STATUSSTRING_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1029000
class DATAMAPID_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1030000
class USERNAMECLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1031000
class RODSZONECLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1032000
class USERTYPECLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1033000
class HOSTCLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1034000
class AUTHSTRCLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1035000
class USERAUTHSCHEMECLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1036000
class USERINFOCLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1037000
class USERCOMMENTCLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1038000
class USERCREATECLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1039000
class USERMODIFYCLIENT_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1040000
class USERNAMEPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1041000
class RODSZONEPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1042000
class USERTYPEPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1043000
class HOSTPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1044000
class AUTHSTRPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1045000
class USERAUTHSCHEMEPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1046000
class USERINFOPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1047000
class USERCOMMENTPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1048000
class USERCREATEPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1049000
class USERMODIFYPROXY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1050000
class COLLNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1051000
class COLLPARENTNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1052000
class COLLOWNERNAME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1053000
class COLLOWNERZONE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1054000
class COLLEXPIRY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1055000
class COLLCOMMENTS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1056000
class COLLCREATE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1057000
class COLLMODIFY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1058000
class COLLACCESS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1059000
class COLLACCESSINX_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1060000
class COLLMAPID_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1062000
class COLLINHERITANCE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1063000
class RESCZONE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1065000
class RESCLOC_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1066000
class RESCTYPE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1067000
class RESCTYPEINX_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1068000
class RESCCLASS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1069000
class RESCCLASSINX_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1070000
class RESCVAULTPATH_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1071000
class NUMOPEN_ORTS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1072000
class PARAOPR_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1073000
class RESCID_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1074000
class GATEWAYADDR_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1075000
class RESCMAX_BJSIZE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1076000
class FREESPACE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1077000
class FREESPACETIME_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1078000
class FREESPACETIMESTAMP_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1079000
class RESCINFO_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1080000
class RESCCOMMENTS_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1081000
class RESCCREATE_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1082000
class RESCMODIFY_EMPTY_IN_STRUCT_ERR(RuleEngineException):
    code = -1083000
class INPUT_ARG_NOT_WELL_FORMED_ERR(RuleEngineException):
    code = -1084000
class INPUT_ARG_OUT_OF_ARGC_RANGE_ERR(RuleEngineException):
    code = -1085000
class INSUFFICIENT_INPUT_ARG_ERR(RuleEngineException):
    code = -1086000
class INPUT_ARG_DOES_NOT_MATCH_ERR(RuleEngineException):
    code = -1087000
class RETRY_WITHOUT_RECOVERY_ERR(RuleEngineException):
    code = -1088000
class CUT_ACTION_PROCESSED_ERR(RuleEngineException):
    code = -1089000
class ACTION_FAILED_ERR(RuleEngineException):
    code = -1090000
class FAIL_ACTION_ENCOUNTERED_ERR(RuleEngineException):
    code = -1091000
class VARIABLE_NAME_TOO_LONG_ERR(RuleEngineException):
    code = -1092000
class UNKNOWN_VARIABLE_MAP_ERR(RuleEngineException):
    code = -1093000
class UNDEFINED_VARIABLE_MAP_ERR(RuleEngineException):
    code = -1094000
class NULL_VALUE_ERR(RuleEngineException):
    code = -1095000
class DVARMAP_FILE_READ_ERROR(RuleEngineException):
    code = -1096000
class NO_RULE_OR_MSI_FUNCTION_FOUND_ERR(RuleEngineException):
    code = -1097000
class FILE_CREATE_ERROR(RuleEngineException):
    code = -1098000
class FMAP_FILE_READ_ERROR(RuleEngineException):
    code = -1099000
class DATE_FORMAT_ERR(RuleEngineException):
    code = -1100000
class RULE_FAILED_ERR(RuleEngineException):
    code = -1101000
class NO_MICROSERVICE_FOUND_ERR(RuleEngineException):
    code = -1102000
class INVALID_REGEXP(RuleEngineException):
    code = -1103000
class INVALID_OBJECT_NAME(RuleEngineException):
    code = -1104000
class INVALID_OBJECT_TYPE(RuleEngineException):
    code = -1105000
class NO_VALUES_FOUND(RuleEngineException):
    code = -1106000
class NO_COLUMN_NAME_FOUND(RuleEngineException):
    code = -1107000
class BREAK_ACTION_ENCOUNTERED_ERR(RuleEngineException):
    code = -1108000
class CUT_ACTION_ON_SUCCESS_PROCESSED_ERR(RuleEngineException):
    code = -1109000
class MSI_OPERATION_NOT_ALLOWED(RuleEngineException):
    code = -1110000

class PHPException(iRODSException):
    pass

class PHP_EXEC_SCRIPT_ERR(PHPException):
    code = -1600000
class PHP_REQUEST_STARTUP_ERR(PHPException):
    code = -1601000
class PHP_OPEN_SCRIPT_FILE_ERR(PHPException):
    code = -1602000 
