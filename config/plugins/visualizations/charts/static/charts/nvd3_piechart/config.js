define([], function() {

return {
    title       : 'Pie chart',
    library     : 'nvd3.js',
    element     : 'svg',
    columns : {
        label : {
            title       : 'Labels',
            any_type    : true
        },
        y : {
            title       : 'Values'
        }
    }
};

});