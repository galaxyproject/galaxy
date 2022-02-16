export default {
    /** is uploading and not ready */
    upload: "warning",
    /** the job that will produce the dataset queued in the runner */
    queued: "warning",
    /** the job that will produce the dataset is running */
    running: "warning",
    /** metadata for the dataset is being discovered/set */
    setting_metadata: "warning",
    /** was created without a tool */
    new: "warning",
    /** job is being created, but not put into job queue yet */
    waiting: "default",
    /** has no data */
    empty: "danger",
    /** has successfully completed running */
    ok: "success",
    /** the job that will produce the dataset paused */
    paused: "info",
    /** metadata discovery/setting failed or errored (but otherwise ok) */
    failed_metadata: "danger",
    /** the tool producing this dataset failed */
    error: "danger",
    /** deleted while uploading */
    discarded: "danger",

    //TODO: not in trans.app.model.Dataset.states - is in database
    /** not accessible to the current user (i.e. due to permissions) */
    noPermission: "danger",
    // found in job-state summary model?
    // this an actual state value or something derived from deleted prop?
    deleted: "danger",
    loading: "warning",
};
