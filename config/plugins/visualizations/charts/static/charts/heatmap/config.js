define([], function() {

return {
    title   : 'Heatmap',
    library : '',
    tag     : 'div',
    use_panels  : true,
    columns : {
        col_label : {
            title       : 'Columns',
            is_label    : true
        },
        row_label : {
            title       : 'Rows',
            is_label    : true
        },
        value : {
            title       : 'Observations'
        },
    }
};

});