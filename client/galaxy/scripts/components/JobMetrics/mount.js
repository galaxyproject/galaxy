/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import $ from "jquery";
import Vue from "vue";
import JobMetrics from "./JobMetrics.vue";

export const mountJobMetrics = propsData => {
    $(".job-metrics").each((index, el) => {
        const jobId = $(el).attr("job_id");
        const datasetId = $(el).attr("dataset_id");
        const datasetType = $(el).attr("dataset_type") || "hda";
        const component = Vue.extend(JobMetrics);
        propsData = propsData || {};
        propsData["jobId"] = jobId;
        propsData["datasetId"] = datasetId;
        propsData["datasetType"] = datasetType;
        return new component({ propsData: propsData }).$mount(el);
    });
};
