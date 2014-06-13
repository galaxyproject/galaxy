define(['plugin/plugins/nvd3/nv.d3'], function() {

return $.extend(true, {}, {
    title       : 'Pie chart',
    category    : 'Area charts',
    library     : 'NVD3',
    tag         : 'svg',
    keywords    : 'small',
    columns : {
        label : {
            title       : 'Labels',
            is_label    : true,
            is_auto     : true
        },
        y : {
            title       : 'Values',
            is_numeric  : true
        }
    },
    
    settings : {
        main_separator : {
            type        : 'separator',
            title       : 'Pie chart settings'
        },
       
        donut_ratio : {
            title       : 'Donut ratio',
            info        : 'Determine how large the donut hole will be.',
            type        : 'select',
            init        : '0.5',
            data        : [
                {
                    label   : '50%',
                    value   : '0.5'
                },
                {
                    label   : '25%',
                    value   : '0.25'
                },
                {
                    label   : '10%',
                    value   : '0.10'
                },
                {
                    label   : '0%',
                    value   : '0'
                }
            ]
        },
        
        show_legend : {
            title       : 'Show legend',
            info        : 'Would you like to add a legend?',
            type        : 'radiobutton',
            init        : 'false',
            data        : [
                {
                    label   : 'Yes',
                    value   : 'true'
                },
                {
                    label   : 'No',
                    value   : 'false'
                }
            ]
        },
       
        label_separator : {
            type        : 'separator',
            title       : 'Label settings'
        },
       
        label_type : {
            title       : 'Donut label',
            info        : 'What would you like to show for each slice?',
            type        : 'select',
            init        : 'percent',
            data        : [
                {
                    label   : '-- Nothing --',
                    value   : 'hide',
                    hide    : 'label_outside'
                },
                {
                    label   : 'Label column',
                    value   : 'key',
                    show    : 'label_outside'
                },
                {
                    label   : 'Value column',
                    value   : 'value',
                    show    : 'label_outside'
                },
                {
                    label   : 'Percentage',
                    value   : 'percent',
                    show    : 'label_outside'
                }
            ],
        },

        label_outside : {
            title       : 'Show outside',
            info        : 'Would you like to show labels outside the donut?',
            type        : 'radiobutton',
            init        : 'false',
            data        : [
                {
                    label   : 'Yes',
                    value   : 'true'
                },
                {
                    label   : 'No',
                    value   : 'false'
                }
            ]
        },
        
        use_panels : {
            init        : 'true',
            hide        : true
        }
    }
});
});