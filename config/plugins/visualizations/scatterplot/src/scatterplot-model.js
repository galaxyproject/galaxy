var ScatterplotModel = Visualization.extend({

    defaults : {
        type    : 'scatterplot',

        config  : {
            // shouldn't be needed for properly saved splots - also often incorrect
            //xColumn : 0,
            //yColumn : 1,
            
            pagination  : {
                currPage    : 0,
                perPage     : 3000
            },

            // graph style
            width   : 400,
            height  : 400,

            margin : {
                top     : 16,
                right   : 16,
                bottom  : 40,
                left    : 54
            },

            xTicks   : 10,
            xLabel   : 'X',
            yTicks   : 10,
            yLabel   : 'Y',

            datapointSize   : 4,
            animDuration    : 500,

            scale       : 1,
            translate   : [ 0, 0 ]
        }
    }
});
