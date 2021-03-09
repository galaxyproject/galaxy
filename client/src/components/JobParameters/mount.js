/**
 * Endpoint for mounting job parameters from non-Vue environment.
 */
import JobParameters from "./JobParameters.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountJobParameters = (propsData = {}) => {
    const elements = document.querySelectorAll(".job-parameters");
    Array.prototype.forEach.call(elements, function (el, i) {
        const jobId = el.getAttribute("job_id");
        const datasetId = el.getAttribute("dataset_id");
        const param = el.getAttribute("param") || undefined;
        const datasetType = el.getAttribute("dataset_type") || "hda";
        propsData.jobId = jobId;
        propsData.datasetId = datasetId;
        propsData.param = param;
        propsData.datasetType = datasetType;
        mountVueComponent(JobParameters)(propsData, el);
    });
};
