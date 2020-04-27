/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import $ from "jquery";
import JobMetrics from "./JobMetrics.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountJobMetrics = (propsData = {}) => {
    $(".job-metrics").each((index, el) => {
        const jobId = $(el).attr("job_id");
        const aws_estimate = $(el).attr("aws_estimate");
        const datasetId = $(el).attr("dataset_id");
        const datasetType = $(el).attr("dataset_type") || "hda";
        propsData.jobId = jobId;
        propsData.datasetId = datasetId;
        propsData.datasetType = datasetType;
        propsData.aws_estimate = aws_estimate;
        mountVueComponent(JobMetrics)(propsData, el);
    });
};
