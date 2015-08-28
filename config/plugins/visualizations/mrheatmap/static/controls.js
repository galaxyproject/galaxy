define([], function(){
	var Chromosome = Backbone.Model.extend({
	    value: null,
    	label: null,
    });

    var Chromosomes = Backbone.Collection.extend({
    	initialize: function() {}
    });

	var GenericTool = Backbone.Model.extend({

		initialize : function( options ){
			this.view = options.view;
		},
	});

    return {
    	Chromosome        : Chromosome,
    	Chromosomes       : Chromosomes,
		Generic           : GenericTool,
    }
});