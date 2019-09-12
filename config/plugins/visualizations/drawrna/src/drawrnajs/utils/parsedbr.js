var exp = {};

exp.parseDbr = function(seq, dotbr){
	var round = [],
        nodes = [],
        links = [];

	var src, type;
	//Indices corresponding to opening brackets are pushed onto a stack
	//and are popped when a closing bracket is read.
	//Links (hbonds, phosphodiester bonds) are created as needed.
	for(var i = 0; i < seq.length; i++){
		nodes.push({name: seq[i].toUpperCase()});
		if(i > 0){
			links.push({source: i-1, target: i, type: "phosphodiester"});
		}
		switch(dotbr[i]){
			case "(":
				round.push(i);
				break;
			case ")":
				src = round.pop();
				type = exp.getType(exp.isWatsonCrick(seq[src], seq[i]));
				links.push({source: src, target: i, type: type});
				break;
			case ".":
				break;
		}
	}
	//Return graph in object format
	return {
        nodes: nodes,
		links: links
    };
}

exp.isWatsonCrick = function(nucOne, nucTwo){
	var watsonCrick = false;
	if(nucOne === "G" && nucTwo === "C" ||
		nucOne === "C" && nucTwo === "G" ||
		nucOne === "A" && nucTwo === "U" ||
		nucOne === "U" && nucTwo === "A" ||
		nucOne === "A" && nucTwo === "T" ||
		nucOne === "T" && nucTwo === "A") {
		watsonCrick = true;
	}
	return watsonCrick;
}

exp.getType = function(watsonCrick){
	if(watsonCrick){
		return "hbond";
	} else {
		return "violation";
	}
}

module.exports = exp;
