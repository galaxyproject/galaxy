define([], function() {
return {
    'api/datatypes/mapping': {
        data: '{"ext_to_class_name" : {"txt" : "Text", "data":"Data","tabular":"Tabular", "binary": "Binary", "bam": "Bam" }, "class_to_classes": { "Data": { "Data": true }, "Text": { "Text": true, "Data": true }, "Tabular": { "Tabular": true, "Text": true, "Data": true }, "Binary": { "Data": true, "Binary": true }, "Bam": { "Data": true, "Binary": true, "Bam": true }}}'
    },
    'api/datatypes': {
        data: '["RData", "ab1", "affybatch", "txt"]'
    },
    'api/tools/test/build': {
        data: '{ "id": "test", "name": "_name", "version": "_version", "description": "_description", "display": "true", "requirements": [ { "name": "req_name_a", "version": "req_version_a" }, { "name": "req_name_b", "version": "req_version_b" } ], "inputs": [ { "name": "a", "type": "text" }, { "name": "b",  "type": "conditional", "test_param": { "name": "c",  "type": "select", "value": "h" }, "cases": [ { "name": "d", "value": "d", "inputs": [ { "name": "f", "type": "text" }, { "name": "g",  "type": "text" } ] }, { "name": "h", "value": "h", "inputs": [ { "name": "i",  "type": "text" }, { "name": "j",  "type": "text" } ] } ] }, { "name": "k",  "type": "repeat", "cache": [[ { "name": "l",  "type": "text" }, { "name": "m",  "type": "conditional", "test_param": { "name": "n",  "type": "select", "value": "o" }, "cases": [ { "name": "o", "value": "o", "inputs": [ { "name": "p",  "type": "text" }, { "name": "q",  "type": "text" } ] }, { "name": "r", "value": "r", "inputs": [ { "name": "s",  "type": "text" }, { "name": "t",  "type": "text" } ] } ] } ] ], "inputs" : [ { "name": "l",  "type": "text" }, { "name": "m",  "type": "conditional", "test_param": { "name": "n",  "type": "select", "value": "o" }, "cases": [ { "name": "o", "value": "o", "inputs": [ { "name": "p",  "type": "text" }, { "name": "q",  "type": "text" } ] }, { "name": "r", "value": "r", "inputs": [ { "name": "s",  "type": "text" }, { "name": "t",  "type": "text" } ] } ] } ] } ] }'
    }
}
});