//==============================================================================
/** Map of possible HDA/collection/job states to their string equivalents.
 *      A port of galaxy.model.Dataset.states.
 */
var STATES = {
    // NOT ready states
    /** is uploading and not ready */
    UPLOAD: "upload",
    /** the job that will produce the dataset is being held due to concurrency limits */
    LIMITED: "limited",
    /** the job that will produce the dataset is dispatched to the runner */
    DISPATCHED: "dispatched",
    /** the job that will produce the dataset has been submitted to the executing resource */
    SUBMITTED: "submitted",
    /** the job that will produce the dataset is queued on the executing resource */
    QUEUED: "queued",
    /** the job that will produce the dataset is running */
    RUNNING: "running",
    /** metadata for the dataset is being discovered/set */
    SETTING_METADATA: "setting_metadata",

    // ready states
    /** just created and not yet picked up by a handler, or waiting for terminal inputs */
    NEW: "new",
    /** waiting for terminal inputs (db-skip-locked or db-transaction-isolation only) */
    WAITING: "waiting",
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
    /** the tool producing this dataset failed */
    ERROR: "error"
};

STATES.READY_STATES = [
    STATES.OK,
    STATES.EMPTY,
    STATES.PAUSED,
    STATES.FAILED_METADATA,
    STATES.NOT_VIEWABLE,
    STATES.DISCARDED,
    STATES.ERROR
];

STATES.NOT_READY_STATES = [
    STATES.UPLOAD,
    STATES.LIMITED,
    STATES.DISPATCHED,
    STATES.SUBMITTED,
    STATES.QUEUED,
    STATES.RUNNING,
    STATES.SETTING_METADATA,
    STATES.WAITING,
    STATES.NEW
];

//==============================================================================
export default STATES;
