define([], function() {

return {
    title       : 'Pie chart',
    library     : 'nvd3.js',
    element     : 'svg',
    columns : {
        label : {
            title       : 'Labels',
            is_label    : true
        },
        y : {
            title       : 'Values'
        }
    }
};

});