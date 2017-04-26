define( [], function() {
    return {
        title       : 'NGL Viewer',
        library     : 'NGL',
        datatypes   : [ 'pdb' ],
        keywords    : 'NGL protein viewer pdb',
        description : 'NGL Viewer is a WebGL based molecular visualization hosted at http://arose.github.io/ngl/.',
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
                    help    : '',
                    data    : [ { label : 'Axes', value : 'axes' },
                                { label : 'Base', value : 'base' },
                                { label : 'Backbone', value : 'backbone' },
                                { label : 'Ball+Stick', value : 'ball+stick' },
                                { label : 'Cartoon', value : 'cartoon' },
                                { label : 'Contact', value : 'contact' },
                                { label : 'Helixorient', value : 'helixorient' },
                                { label : 'Hyperball', value : 'hyperball' },
                                { label : 'Label', value : 'label' },
                                { label : 'Licorice', value : 'licorice' },
                                { label : 'Line', value : 'line' },
                                { label : 'Point', value : 'point' },
                                { label : 'Ribbon', value : 'ribbon' },
                                { label : 'Rocket', value : 'rocket' },
                                { label : 'Rope', value : 'rope' },
                                { label : 'Spacefill', value : 'spacefill' },
                                { label : 'Surface', value : 'surface' },
                                { label : 'Trace', value : 'trace' },
                                { label : 'Tube', value : 'tube' },
                                { label : 'Unitcell', value : 'unitcell' } ]
                }
            },
            radius: {
                name  : 'radius',
                label : 'Radius',
                help  : 'Select a number providing a fixed radius used for rendering the representation.',
                type  : 'float',
                min   : 0.001,
                max   : 10.0,
                value : 0.05
            },
            scale: {
                name  : 'scale',
                label : 'Scale',
                help  : 'Select a number that scales the value defined by the *radius* parameter.',
                type  : 'float',
                min   : 0.001,
                max   : 10.0,
                value : 0.7
            },
            colorscheme : {
                label   : 'Color Scheme',
                help    : 'Select color scheme of the molecule scene.',
                type    : 'select',
                display : 'radio',
                value   : 'atomindex',
                data    : [ { label : 'Element', value : 'element' },
                            { label : 'Picking', value : 'picking' },
                            { label : 'Random', value : 'random' },
                            { label : 'Uniform', value : 'uniform' },
                            { label : 'Atomindex', value : 'atomindex' },
                            { label : 'Residue Index', value : 'residueindex' },
                            { label : 'Chain Index', value : 'chainindex' },
                            { label : 'Chain Name', value : 'chainname' },
                            { label : 'Chain Id', value : 'chainid' },
                            { label : 'Polymer', value : 'polymer' },
                            { label : 'Model Index', value : 'modelindex' },
                            { label : 'Entity Type', value : 'entitytype' },
                            { label : 'Molecule Type', value : 'moleculetype' },
                            { label : 'Secondary Structure', value : 'sstruc' },
                            { label : 'Bfactor', value : 'bfactor' },
                            { label : 'Resname', value : 'resname' },
                            { label : 'Hydrophobicity', value : 'hydrophobicity' },
                            { label : 'Value', value : 'value' },
                            { label : 'Volume', value : 'volume' },
                            { label : 'Occupancy', value : 'occupancy' } ]
            },
            backcolor : {
                label   : 'Background Color',
                help    : 'Select background color of the viewer.',
                type    : 'select',
                display : 'radio',
                value   : 'white',
                data    : [ { label : 'Light', value : 'white' }, { label : 'Dark', value : 'black' } ]
            },
            spin : {
                label   : 'Spin',
                help    : 'Spin the molecule view.',
                type    : 'select',
                display : 'radio',
                value   : false,
                data    : [ { label : 'On', value : true }, { label : 'Off', value : false } ]
            },
            assembly : {
                label   : 'Assembly',
                help    : 'Select a name of an assembly object.',
                type    : 'select',
                display : 'radio',
                value   : 'default',
                data    : [ { label : 'Default', value : 'default' }, { label : 'AU', value : '' },
                            { label : 'BU1', value : 'BU1' }, { label : 'UNITCELL', value : 'UNITCELL' },
                            { label : 'SUPERCELL', value: 'SUPERCELL' } ]
            },
            opacity : {
                name  : 'opacity',
                label : 'Opacity',
                help  : 'Select opacity for the molecule scene.',
                type  : 'float',
                min   : 0.0,
                max   : 1.0,
                value : 1.0

            }
        }
    }
});
