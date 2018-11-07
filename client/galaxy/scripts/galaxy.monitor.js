import { installMonitor } from "utils/installMonitor";
import { getAppRoot } from "onload/loadConfig";

const galaxyStub = { root: getAppRoot(), config: {} };

export default installMonitor("Galaxy", galaxyStub);
