/**
 * Endpoint for mounting job parameters from non-Vue environment.
 */
import $ from "jquery";
import Vue from "vue";
import JobParameters from "./JobParameters.vue";

export const mountJobParameters = (propsData = {}) => {
    $(".job-parameters").each((index, el) => {
        const jobId = $(el).attr("job_id");
        const datasetId = $(el).attr("dataset_id");
        const datasetType = $(el).attr("dataset_type") || "hda";
        const component = Vue.extend(JobParameters);
        propsData.jobId = jobId;
        propsData.datasetId = datasetId;
        propsData.datasetType = datasetType;
        return new component({ propsData: propsData }).$mount(el);
    });
};
