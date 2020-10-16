var Backbone = require("backbone");

var Link = Backbone.Model.extend({
    defaults: {
        group: "edges"
    },
    initialize: function(data){
        this.set("id", data.id);
        this.set("source", data.source);
        this.set("target", data.target);
        this.set("label", data.label);
        this.set("weight", data.weight);
        this.set("color", data.color);
    }
})

module.exports = Link;
