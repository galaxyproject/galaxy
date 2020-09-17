/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import $ from "jquery";
import JobDestinationParams from "./JobDestinationParams.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDestinationParams = (propsData = {}) => {
    $(".job-destination-parameters").each((index, el) => {
        propsData.jobId = $(el).attr("job_id");
        mountVueComponent(JobDestinationParams)(propsData, el);
    });
};
