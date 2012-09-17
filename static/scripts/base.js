define( "libs/backbone", function( backbone ) {

	var Base = function() {
		if( this.initialize ) {
			this.initialize.apply(this, arguments);
		}
	};
	Base.extend = backbone.Backbone.Model.extend;

	return {
		Base: Base,
		Backbone: backbone.Backbone
	};

});