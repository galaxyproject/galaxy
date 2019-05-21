/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import $ from "jquery";
import Vue from "vue";
import JobParameters from "./JobParameters.vue";

export const mountJobParameters = propsData => {
    $(".job-parameters").each((index, el) => {
        const component = Vue.extend(JobParameters);
        const jobId = $(el).attr("job_id");
        const datasetId = $(el).attr("dataset_id");
        const datasetType = $(el).attr("dataset_type") || "hda";
        propsData = propsData || {};
        propsData["jobId"] = jobId;
        propsData["datasetId"] = datasetId;
        propsData["datasetType"] = datasetType;
        return new component({ propsData: propsData }).$mount(el);
    });
};
