const STATES = {
    /** deleted while uploading */
    DISCARDED: "discarded",
    /** remote dataset not ingested yet */
    DEFERRED: "deferred",
    /** dataset has been deleted */
    DELETED: "deleted",
    /** dataset is being been deleted */
    DELETING: "deleting",
    /** has no data */
    EMPTY: "empty",
    /** the tool producing this dataset failed */
    ERROR: "error",
    /** metadata discovery/setting failed or errored (but otherwise ok) */
    FAILED_METADATA: "failed_metadata",
    /** was created without a tool */
    NEW: "new",
    /** not accessible to the current user (i.e. due to permissions) */
    NOT_VIEWABLE: "noPermission",
    /** has successfully completed running */
    OK: "ok",
    /** the job that will produce the dataset paused */
    PAUSED: "paused",
    /** the job that will produce the dataset queued in the runner */
    QUEUED: "queued",
    /** the job that will produce the dataset is running */
    RUNNING: "running",
    /** the job has been resubmitted */
    RESUBMITTED: "resubmitted",
    /** metadata for the dataset is being discovered/set */
    SETTING_METADATA: "setting_metadata",
    /** the job has been skipped */
    SKIPPED: "skipped",
    /** the job has been stopped */
    STOP: "stop",
    /** the job is stopping */
    STOPPING: "stopping",
    /** is uploading and not ready */
    UPLOAD: "upload",
    /** the job is waiting */
    WAITING: "waiting",
};

export default {
    ...STATES,
    OK_STATES: [STATES.OK, STATES.DEFERRED, STATES.FAILED_METADATA],
    READY_STATES: [
        STATES.DEFERRED,
        STATES.DISCARDED,
        STATES.EMPTY,
        STATES.ERROR,
        STATES.FAILED_METADATA,
        STATES.NOT_VIEWABLE,
        STATES.OK,
        STATES.PAUSED,
        STATES.SKIPPED,
        STATES.STOP,
        STATES.STOPPING,
    ],
    PENDING_STATES: [
        STATES.NEW,
        STATES.QUEUED,
        STATES.RESUBMITTED,
        STATES.RUNNING,
        STATES.SETTING_METADATA,
        STATES.UPLOAD,
        STATES.WAITING,
    ],
    ERROR_STATES: [STATES.DELETED, STATES.DELETING, STATES.ERROR],
};
