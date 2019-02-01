import dataTypesMapping from "./json/datatypes.mapping.json";
import dataTypes from "./json/datatypes.json";
import toolsTestBuild from "./json/tools.test.build";

export default {
    "api/datatypes/mapping": {
        data: JSON.stringify(dataTypesMapping)
    },
    "api/datatypes": {
        data: JSON.stringify(dataTypes)
    },
    "api/tools/test/build": {
        data: JSON.stringify(toolsTestBuild)
    }
};
