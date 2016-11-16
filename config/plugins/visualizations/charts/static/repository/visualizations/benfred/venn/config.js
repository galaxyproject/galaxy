define( [], function() {
    return {
        title       : 'Venn Diagram',
        library     : 'benfred',
        tag         : 'svg',
        datatypes   : [ 'tabular', 'csv' ],
        keywords    : 'default venn overlap circle',
        description : 'A javascript library for laying out area proportional venn and euler diagrams hosted at https://github.com/benfred/venn.js.',
        exports     : [ 'png', 'svg', 'pdf' ],
        groups      : {
            key: {
                label       : 'Provide a label',
                type        : 'text',
                placeholder : 'Data label',
                value       : 'Data label'
            },
            observation : {
                label       : 'Column with observations',
                type        : 'data_column',
                is_label    : true
            }
        }
    }
});