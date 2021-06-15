/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import JobMetrics from "./JobMetrics.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountJobMetrics = (propsData = {}) => {
    const elements = document.querySelectorAll(".job-metrics");
    Array.prototype.forEach.call(elements, function (el, i) {
        const jobId = el.getAttribute("job_id");
        const aws_estimate = el.getAttribute("aws_estimate");
        const datasetId = el.getAttribute("dataset_id");
        const datasetType = el.getAttribute("dataset_type") || "hda";
        propsData.jobId = jobId;
        propsData.datasetId = datasetId;
        propsData.datasetType = datasetType;
        propsData.aws_estimate = aws_estimate;
        mountVueComponent(JobMetrics)(propsData, el);
    });
};
