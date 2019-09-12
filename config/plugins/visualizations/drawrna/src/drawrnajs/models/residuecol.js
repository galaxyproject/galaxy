var Backbone = require("backbone");
var Residue = require("./residue");
var _ = require("underscore");

var ResidueCol = Backbone.Collection.extend({
    model: Residue,
    setResidueColor: function(group, color){
        _.each(this.where({name: group}),
            function(el){ el.set("color", color); });
    },
    setSelectionColor: function(group, color){
        var el = null;

        for(var i=0; i<group.length; i++){
            el = group[i];
            this.where({id: el.id()})[0].set("color", color);
        }
    }
});

module.exports = ResidueCol;
