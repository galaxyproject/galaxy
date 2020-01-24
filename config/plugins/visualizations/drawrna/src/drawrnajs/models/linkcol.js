var Backbone = require("backbone");
var Link = require("./link");
var pdbr = require("../utils/parsedbr");

var LinkCol = Backbone.Collection.extend({
    model: Link,
    initialize: function(model, stl, residues){
        this.style = stl;
        this.residues = residues;
    },
    newBond: function(src, target){
        var res1 = this.residues.at(parseInt(src));
        var res2 = this.residues.at(parseInt(target));
        var type = pdbr.getType(pdbr.isWatsonCrick(res1, res2));
        var style = this.style;

        this.add(new Link({
            id: src + "to" + target,
            source: src,
            target: target,
            label: type,
            weight: style.getWeight(type),
            color: style.getColor(type)
        }));
    }
});

module.exports = LinkCol;
