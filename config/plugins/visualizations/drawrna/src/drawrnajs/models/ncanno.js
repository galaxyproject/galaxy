var Backbone = require("backbone");

var Anno = Backbone.Model.extend({
    defaults: {
        base1: "wc",
        base2: "wc",
        stericity: "cis",
        edge: null
    },
    initialize: function(b1, b2, st, edge){
        this.set("base1", b1);
        this.set("base2", b2);
        this.set("edge", edge);
        this.set("stericity", st);
    },
    getLabels: function(){
        var labels = [];
        for(var i=1; i<3; i++){
            switch(this.get("base" + i)){
                case "wc":
                    labels.push("Watson-Crick");
                    break;
                case "hg":
                    labels.push("Hoogsteen");
                    break;
                case "sg":
                    labels.push("Sugar");
                    break;
            }
        }
        labels.push(this.get("stericity"));
        return labels;
    }
})

module.exports = Anno;
