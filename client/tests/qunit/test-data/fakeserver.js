import dataTypesMapping from "./json/datatypes.mapping.json";
import dataTypes from "./json/datatypes.json";

export default {
    "api/datatypes/mapping": {
        data: JSON.stringify(dataTypesMapping),
    },
    "api/datatypes": {
        data: JSON.stringify(dataTypes),
    },
};
