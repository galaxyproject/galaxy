import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

async function jobDetails({ jobid }) {
    const url = `${getAppRoot()}api/jobs/${jobid}?full=True`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

async function jobProblems({ jobid }) {
    const url = `${getAppRoot()}api/jobs/${jobid}/common_problems`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const JobDetailsProvider = SingleQueryProvider(jobDetails);
export const JobProblemProvider = SingleQueryProvider(jobProblems);
