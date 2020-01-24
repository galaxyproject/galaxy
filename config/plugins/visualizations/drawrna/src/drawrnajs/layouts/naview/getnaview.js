var NAView = require("./naview");

getCoordsNAVIEW = module.exports = function(nodes, links){
	//Calculates coordinates according to the NAView layout
	var pairTable = [];

	for(var i=0; i<nodes.length; i++){
		pairTable.push(getPartner(i, links));
	}
	var naView = new NAView();
	var xy = naView.naview_xy_coordinates(pairTable);

	// Updating individual base positions
	var coords = []
	for (var i = 0; i < nodes.length; i++) {
		coords.push({
			x: Math.round(xy.x[i] * 2.5),
			y: Math.round(xy.y[i] * 2.5)
		});
	}
	return coords;
}

function getPartner(srcIndex, links){
	//Returns the partner of a nucleotide:
	//-1 means there is no partner
	var partner = -1;
	for(var i = 0; i < links.length; i++){
		if(links[i].type !== "phosphodiester" && links[i].type !== "index"){
			if(links[i].source === srcIndex){
				partner = links[i].target;
				break;
			}
			else if(links[i].target === srcIndex){
				partner = links[i].source;
				break;
			}
			else {
				continue;
			}
		}
	}
	return partner;
}
