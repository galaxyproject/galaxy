//==============================================================================
/** Map of possible HDA/collection/job states to their string equivalents.
 *      A port of galaxy.model.Dataset.states.
 */
const RAW_STATES = {
    // NOT ready states
    /** is uploading and not ready */
    UPLOAD: "upload",
    /** the job that will produce the dataset queued in the runner */
    QUEUED: "queued",
    /** the job that will produce the dataset is running */
    RUNNING: "running",
    /** metadata for the dataset is being discovered/set */
    SETTING_METADATA: "setting_metadata",

    // ready states
    /** was created without a tool */
    NEW: "new",
    /** has no data */
    EMPTY: "empty",
    /** has successfully completed running */
    OK: "ok",

    /** the job that will produce the dataset paused */
    PAUSED: "paused",
    /** metadata discovery/setting failed or errored (but otherwise ok) */
    FAILED_METADATA: "failed_metadata",
    //TODO: not in trans.app.model.Dataset.states - is in database
    /** not accessible to the current user (i.e. due to permissions) */
    NOT_VIEWABLE: "noPermission",
    /** deleted while uploading */
    DISCARDED: "discarded",
    /** remote dataset not ingested yet */
    DEFERRED: "deferred",
    /** the tool producing this dataset failed */
    ERROR: "error",
};

const STATES = {
    ...RAW_STATES,
    READY_STATES: [
        RAW_STATES.OK,
        RAW_STATES.EMPTY,
        RAW_STATES.PAUSED,
        RAW_STATES.FAILED_METADATA,
        RAW_STATES.NOT_VIEWABLE,
        RAW_STATES.DEFERRED,
        RAW_STATES.DISCARDED,
        RAW_STATES.ERROR,
    ],
    NOT_READY_STATES: [
        RAW_STATES.UPLOAD,
        RAW_STATES.QUEUED,
        RAW_STATES.RUNNING,
        RAW_STATES.SETTING_METADATA,
        RAW_STATES.NEW,
    ],
    VALID_INPUT_STATES: Object.values(RAW_STATES).filter(
        (state) => ![RAW_STATES.ERROR, RAW_STATES.DISCARDED, RAW_STATES.FAILED_METADATA].includes(state)
    ),
};

//==============================================================================
export default STATES;
