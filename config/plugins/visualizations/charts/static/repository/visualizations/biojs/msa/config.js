define( [], function() {
    return {
        title       : 'Multiple Sequence Alignment',
        library     : 'BioJS',
        datatypes   : [ 'txt' ],
        keywords    : 'biojs',
        description : 'The MSA viewer is a modular, reusable component to visualize large MSAs interactively on the web.',
        settings    : {
            conserv: { label :'Show conservation', help : 'Do you want to display a bar diagram indicating sequence conservation?', type : 'boolean', value: 'true' },
            overviewbox: { label :'Show overview box', help : 'Do you want to display the overview box below the sequence alignments?', type : 'boolean', value: 'true' },
            menu: { label :'Show interactive menu', help : 'Do you want to show a menu for interactive configuration?', type : 'boolean', value: 'true' }
        }
    }
});