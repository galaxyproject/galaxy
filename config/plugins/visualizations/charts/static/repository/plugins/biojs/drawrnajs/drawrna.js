var Backbone = require("backbone");
var Structure = require("./models/structure");
var Vispanel = require("./views/vispanel");

var Drawrnajs = Backbone.View.extend({
    initialize: function(opts){
        this.struct = new Structure(opts.seq, opts.dotbr, 'naview');
        this.vis = new Vispanel({ el: opts.el, struct: this.struct, resindex: opts.resindex });
    },
    render: function(){
        this.vis.render();
    }
});

module.exports = Drawrnajs;
