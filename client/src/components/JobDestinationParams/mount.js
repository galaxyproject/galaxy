/**
 * Endpoint for mounting job metrics from non-Vue environment.
 */
import JobDestinationParams from "./JobDestinationParams.vue";
import { mountVueComponent } from "utils/mountVueComponent";

export const mountDestinationParams = (propsData = {}) => {
    const elements = document.querySelectorAll(".job-destination-parameters");
    Array.prototype.forEach.call(elements, function (el, i) {
        propsData.jobId = el.getAttribute("job_id");
        mountVueComponent(JobDestinationParams)(propsData, el);
    });
};
