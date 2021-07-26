import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";

async function jobDetails({ jobid }) {
    const url = `${getAppRoot()}api/jobs/${jobid}?full=True`;
    const { data } = await axios.get(url);
    return data;
}

async function jobProblems({ jobid }) {
    const url = `${getAppRoot()}api/jobs/${jobid}/common_problems`;
    const { data } = await axios.get(url);
    return data;
}

export const JobDetailsProvider = SingleQueryProvider(jobDetails);
export const JobProblemProvider = SingleQueryProvider(jobProblems);
