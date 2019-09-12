var radiate = require("./radiate/getradiate");
var naview = require("./naview/getnaview");

var Layout = function(layout, nodes, links){
    this.layout = layout;
    this.nodes = nodes;
    this.links = links;
}

Layout.prototype.getCoords = function(){
    var coords = null;
    if(this.layout === "radiate"){
        coords = radiate(this.nodes, this.links);
    }
    else if(this.layout === "naview"){
        coords = naview(this.nodes, this.links);
    }
    else {
        throw new Error("Invalid layout");
    }
    return coords;
}

module.exports = Layout;
