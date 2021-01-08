import { combine } from "./scripts/combine.js";
import dataJSON from "./data/topics.json";
import toolsJSON from "./tools/topics.json";
import workflowsJSON from "./workflows/topics.json";
const topicsList = [dataJSON, toolsJSON, workflowsJSON];

export const newUserDict = combine(topicsList);
