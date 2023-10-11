/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export type InvocationMessageResponseModel =
    | GenericInvocationCancellationReviewFailedEncodedDatabaseIdField
    | GenericInvocationCancellationHistoryDeletedEncodedDatabaseIdField
    | GenericInvocationCancellationUserRequestEncodedDatabaseIdField
    | GenericInvocationFailureDatasetFailedEncodedDatabaseIdField
    | GenericInvocationFailureCollectionFailedEncodedDatabaseIdField
    | GenericInvocationFailureJobFailedEncodedDatabaseIdField
    | GenericInvocationFailureOutputNotFoundEncodedDatabaseIdField
    | GenericInvocationFailureExpressionEvaluationFailedEncodedDatabaseIdField
    | GenericInvocationFailureWhenNotBooleanEncodedDatabaseIdField
    | GenericInvocationUnexpectedFailureEncodedDatabaseIdField
    | GenericInvocationEvaluationWarningWorkflowOutputNotFoundEncodedDatabaseIdField;

export interface GenericInvocationCancellationHistoryDeletedEncodedDatabaseIdField {
    reason: "history_deleted";
    /**
     * History ID of history that was deleted.
     */
    history_id: string;
}
export interface GenericInvocationCancellationHistoryDeletedInt {
    reason: "history_deleted";
    /**
     * History ID of history that was deleted.
     */
    history_id: number;
}
export interface GenericInvocationCancellationReviewFailedEncodedDatabaseIdField {
    reason: "cancelled_on_review";
    /**
     * Workflow step id of paused step that did not pass review.
     */
    workflow_step_id: number;
}
export interface GenericInvocationCancellationReviewFailedInt {
    reason: "cancelled_on_review";
    /**
     * Workflow step id of paused step that did not pass review.
     */
    workflow_step_id: number;
}
export interface GenericInvocationCancellationUserRequestEncodedDatabaseIdField {
    reason: "user_request";
}
export interface GenericInvocationCancellationUserRequestInt {
    reason: "user_request";
}
export interface GenericInvocationEvaluationWarningWorkflowOutputNotFoundEncodedDatabaseIdField {
    reason: "workflow_output_not_found";
    workflow_step_id: number;
    /**
     * Output that was designated as workflow output but that has not been found
     */
    output_name: string;
}
export interface GenericInvocationEvaluationWarningWorkflowOutputNotFoundInt {
    reason: "workflow_output_not_found";
    workflow_step_id: number;
    /**
     * Output that was designated as workflow output but that has not been found
     */
    output_name: string;
}
export interface GenericInvocationFailureCollectionFailedEncodedDatabaseIdField {
    reason: "collection_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * HistoryDatasetCollectionAssociation ID that relates to failure.
     */
    hdca_id?: string;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id: number;
}
export interface GenericInvocationFailureCollectionFailedInt {
    reason: "collection_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * HistoryDatasetCollectionAssociation ID that relates to failure.
     */
    hdca_id?: number;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id: number;
}
export interface GenericInvocationFailureDatasetFailedEncodedDatabaseIdField {
    reason: "dataset_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * HistoryDatasetAssociation ID that relates to failure.
     */
    hda_id: string;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id?: number;
}
export interface GenericInvocationFailureDatasetFailedInt {
    reason: "dataset_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * HistoryDatasetAssociation ID that relates to failure.
     */
    hda_id: number;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id?: number;
}
export interface GenericInvocationFailureExpressionEvaluationFailedEncodedDatabaseIdField {
    reason: "expression_evaluation_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * May contain details to help troubleshoot this problem.
     */
    details?: string;
}
export interface GenericInvocationFailureExpressionEvaluationFailedInt {
    reason: "expression_evaluation_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * May contain details to help troubleshoot this problem.
     */
    details?: string;
}
export interface GenericInvocationFailureJobFailedEncodedDatabaseIdField {
    reason: "job_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * Job ID that relates to failure.
     */
    job_id?: string;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id: number;
}
export interface GenericInvocationFailureJobFailedInt {
    reason: "job_failed";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * Job ID that relates to failure.
     */
    job_id?: number;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id: number;
}
export interface GenericInvocationFailureOutputNotFoundEncodedDatabaseIdField {
    reason: "output_not_found";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    output_name: string;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id: number;
}
export interface GenericInvocationFailureOutputNotFoundInt {
    reason: "output_not_found";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    output_name: string;
    /**
     * Workflow step id of step that caused failure.
     */
    dependent_workflow_step_id: number;
}
export interface GenericInvocationFailureWhenNotBooleanEncodedDatabaseIdField {
    reason: "when_not_boolean";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * Contains details to help troubleshoot this problem.
     */
    details: string;
}
export interface GenericInvocationFailureWhenNotBooleanInt {
    reason: "when_not_boolean";
    /**
     * Workflow step id of step that failed.
     */
    workflow_step_id: number;
    /**
     * Contains details to help troubleshoot this problem.
     */
    details: string;
}
export interface GenericInvocationUnexpectedFailureEncodedDatabaseIdField {
    reason: "unexpected_failure";
    /**
     * May contains details to help troubleshoot this problem.
     */
    details?: string;
}
export interface GenericInvocationUnexpectedFailureInt {
    reason: "unexpected_failure";
    /**
     * May contains details to help troubleshoot this problem.
     */
    details?: string;
}
