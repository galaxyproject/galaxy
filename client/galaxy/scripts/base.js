define( ["libs/backbone/backbone"], function( Backbone ) {

	var Base = function() {
		if( this.initialize ) {
			this.initialize.apply(this, arguments);
		}
	};
	Base.extend = Backbone.Model.extend;

	return {
		Base: Base,
		Backbone: Backbone
	};

});