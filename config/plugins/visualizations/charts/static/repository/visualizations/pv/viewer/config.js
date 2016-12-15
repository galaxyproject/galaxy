define( [], function() {
    return {
        title       : 'PV Protein Viewer',
        library     : 'PV',
        datatypes   : [ 'pdb' ],
        keywords    : 'pv protein viewer pdb structure',
        description : 'PV is a pdb/protein viewer hosted at https://biasmv.github.io/pv/.',
        settings    : {
            quality : {
                label   : 'Quality',
                help    : 'Select the rendering quality.',
                type    : 'select',
                display : 'radio',
                value   : 'medium',
                data    : [ { label : 'High', value : 'high' }, { label : 'Medium', value : 'medium' }, { label : 'Low', value : 'low' } ]
            },
            viewer : {
                type        : 'conditional',
                test_param  : {
                    name    : 'mode',
                    label   : 'Display mode',
                    type    : 'select',
                    display : 'radio',
                    value   : 'cartoon',
                    help    : 'Select the rendering mode.',
                    data    : [ { label : 'Cartoon',        value : 'cartoon' },
                                { label : 'Lines',          value : 'lines' },
                                { label : 'Points',         value : 'points' },
                                { label : 'Spheres',        value : 'spheres' },
                                { label : 'Trace',          value : 'trace' },
                                { label : 'Trace (line)',   value : 'lineTrace' },
                                { label : 'Trace (smooth)', value : 'sline' },
                                { label : 'Tube',           value : 'tube' } ]
                },
                cases       : [ { value : 'cartoon', inputs: [ {
                                    name  : 'radius',
                                    label : 'Radius',
                                    help  : 'Radius of tube profile. Also influences the profile thickness for helix and strand profiles.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 3,
                                    value : 0.3
                                } ] },
                                { value : 'lines', inputs: [ {
                                    name  : 'lineWidth',
                                    label : 'Line width',
                                    help  : 'Specify the line width.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 10,
                                    value : 4
                                } ] },
                                { value : 'points', inputs: [ {
                                    name  : 'pointSize',
                                    label : 'Point size',
                                    help  : 'Specify the point size.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 10,
                                    value : 1
                                } ] },
                                { value : 'spheres' },
                                { value : 'trace', inputs: [ {
                                    name  : 'radius',
                                    label : 'Radius',
                                    help  : 'Specify the tube radius.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 3,
                                    value : 0.3
                                } ] },
                                { value : 'lineTrace', inputs: [ {
                                    name  : 'lineWidth',
                                    label : 'Line width',
                                    help  : 'Specify the line width.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 10,
                                    value : 4
                                } ] },
                                { value : 'sline', inputs: [ {
                                    name  : 'lineWidth',
                                    label : 'Line width',
                                    help  : 'Specify the line width.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 10,
                                    value : 4
                                } ] },
                                { value : 'tube', inputs: [ {
                                    name  : 'radius',
                                    label : 'Radius',
                                    help  : 'Specify the tube radius.',
                                    type  : 'float',
                                    min   : 0.1,
                                    max   : 3,
                                    value : 0.3
                                } ] }
                            ]
            }
        }
    }
});