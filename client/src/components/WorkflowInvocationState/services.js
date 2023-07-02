import axios from "axios";
import { getRootFromIndexLink } from "onload";

const getUrl = (path) => getRootFromIndexLink() + path;

export function getInvocationJobsSummary(invocationId) {
    const url = getUrl(`api/invocations/${invocationId}/jobs_summary`);
    return axios.get(url);
}

export function cancelWorkflowScheduling(invocationId) {
    const url = getUrl(`api/invocations/${invocationId}`);
    return axios.delete(url);
}
