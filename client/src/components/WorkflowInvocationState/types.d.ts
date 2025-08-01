export type ReasonToLevel = {
    history_deleted: "cancel";
    user_request: "cancel";
    cancelled_on_review: "cancel";
    dataset_failed: "error";
    collection_failed: "error";
    job_failed: "error";
    output_not_found: "error";
    expression_evaluation_failed: "error";
    when_not_boolean: "error";
    unexpected_failure: "error";
    workflow_output_not_found: "warning";
    workflow_parameter_invalid: "error";
};
