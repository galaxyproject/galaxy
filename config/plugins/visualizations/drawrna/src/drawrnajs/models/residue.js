var Backbone = require("backbone");

var Residue = Backbone.Model.extend({
    defaults: {
        group: "nodes",
        selectable: true,
        locked: false,
        grabbable: true
    },
    initialize: function(data){
        this.set("name", data.name);
        this.set("color", data.color);
        this.set("x", data.x);
        this.set("y", data.y);
        this.set("id", data.id);
    }
})

module.exports = Residue;
