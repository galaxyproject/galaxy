import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

const TERMINAL_JOB_STATES = ["ok", "error", "deleted", "paused"];

async function getInvocation({ id }) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/any/steps/${id}`);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

const stepIsTerminal = (step) => {
    const isTerminal =
        ["scheduled", "cancelled", "failed"].includes(step.state) &&
        step.jobs.every((job) => TERMINAL_JOB_STATES.includes(job.state));
    return isTerminal;
};

export default SingleQueryProvider(getInvocation, stepIsTerminal);
