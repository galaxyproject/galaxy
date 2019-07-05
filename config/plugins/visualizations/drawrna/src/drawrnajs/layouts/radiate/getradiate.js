var calculateCoords = module.exports = function(seq, dotbr, links){
    //This function calculates the coordinates for each nucleotide
	//according to the radiate layout
	var coords = [];
	var centers = [];
	var angles = [];
	var dirAngle = -1;

	for(var i = 0; i < seq.length; i++){
		coords[i] = {x: 0, y: 0};
		centers[i] = {x: 0, y: 0};
	}

	if(2>1){
		dirAngle += 1.0 - Math.PI / 2.0;
		var i = 0;
		var x = 0.0;
		var y = 0.0;
		var vx = -Math.sin(dirAngle);
		var vy = Math.cos(dirAngle);

		while(i < seq.length){
			coords[i].x = x;
			coords[i].y = y;
			centers[i].x = x + 65 * vy;
			centers[i].y = y - 65 * vx;
			var j = getPartner(i, links);

			if(j > i){
				drawLoop(i, j, 	x + (65 * vx / 2.0), y
									+ (65 * vy / 2.0), dirAngle,
									coords, centers, angles, seq, links);
				centers[i].x = coords[i].x + 65 * vy;
				centers[i].y = y - 65 * vx;
				i = j;
				x += 65 * vx;
				y += 65 * vy;
				centers[i].x = coords[i].x + 65 * vy;
				centers[i].y = y - 65 * vx;
			}
			x += 35 * vx;
			y += 35 * vy;
			i += 1;
		}
	}
	else{
		drawLoop(0, seq.length-1, 0, 0, dirAngle, coords, centers, angles, seq, links);
	}
	return coords;
}

function getPartner(srcIndex, links){
	//Returns the partner of a nucleotide:
	//-1 means there is no partner
	var partner = -1;
	for(var i = 0; i < links.length; i++){
		if(links[i].type != "phosphodiester"){
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

function drawLoop(i, j, x, y, dirAngle, coords, centers, angles, seq, links){
	//Calculates loop coordinates
	if (i > j) {
		return;
	}

	// BasePaired
	if (getPartner(i, links) === j) {
		var normalAngle = Math.PI / 2.0;
		centers[i] = {x: x, y: y};
		centers[j] = {x: x, y: y};
		coords[i].x = (x + 65 * Math.cos(dirAngle - normalAngle) / 2.0);
			coords[i].y = (y + 65 * Math.sin(dirAngle - normalAngle) / 2.0);
			coords[j].x = (x + 65 * Math.cos(dirAngle + normalAngle) / 2.0);
			coords[j].y = (y + 65 * Math.sin(dirAngle + normalAngle) / 2.0);
			drawLoop(i + 1, j - 1, x + 40 * Math.cos(dirAngle), y + 40 * Math.sin(dirAngle), dirAngle, coords,
					centers, angles, seq, links);
	}
	else {
		//multi loop now
		var k = i;
		var basesMultiLoop = [];
		var helices = [];
		var l;
		while (k <= j) {
			l = getPartner(k, links);
			if (l > k) {
				basesMultiLoop.push(k);
				basesMultiLoop.push(l);
				helices.push(k);
				k = l + 1;
			}
			else {
				basesMultiLoop.push(k);
				k++;
			}
		}
		var mlSize = basesMultiLoop.length + 2;
		var numHelices = helices.length + 1;
		var totalLength = 35 * (mlSize - numHelices) + 65 * numHelices;
		var multiLoopRadius;
		var angleIncrementML;
		var angleIncrementBP;
		if (mlSize > 3) {
			multiLoopRadius = determineRadius(numHelices, mlSize - numHelices, (totalLength) / (2.0 * Math.PI), 65, 35);
			angleIncrementML = -2.0 * Math.asin(35 / (2.0 * multiLoopRadius));
			angleIncrementBP = -2.0 * Math.asin(65 / (2.0 * multiLoopRadius));
		}
		else {
			multiLoopRadius = 35.0;
			angleIncrementBP = -2.0 * Math.asin(65 / (2.0 * multiLoopRadius));
			angleIncrementML = (-2.0 * Math.PI - angleIncrementBP) / 2.0;
		}
		var centerDist = Math.sqrt(Math.max(Math.pow(multiLoopRadius, 2) - Math.pow(65 / 2.0, 2), 0.0)) - 40;
		var mlCenter = {x: x + (centerDist * Math.cos(dirAngle)),
						y: y + (centerDist * Math.sin(dirAngle))}
		// Base directing angle for (multi|hairpin) loop, from the center's
		// perspective
		var baseAngle = dirAngle
				// U-turn
				+ Math.PI
				// Account for already drawn supporting base-pair
				+ 0.5 * angleIncrementBP
				// Base cannot be paired twice, so next base is at
				// "unpaired base distance"
				+ 1.0 * angleIncrementML;

		var currUnpaired = [];
		var currInterval = {el1: 0, el2: baseAngle-1.0 * angleIncrementML};
		var intervals = [];

		for (k = basesMultiLoop.length - 1; k >= 0; k--) {
			l = basesMultiLoop[k];
			centers[l] = mlCenter;
			var isPaired = (getPartner(i, links) != -1);
			var isPaired3 = isPaired && (getPartner(i, links) < l);
			var isPaired5 = isPaired && !isPaired3;
			if (isPaired3) {
				baseAngle = correctHysteresis(baseAngle+angleIncrementBP/2.)-angleIncrementBP/2.;
				currInterval.el1 = baseAngle;
				intervals.push({el1: currUnpaired, el2: currInterval });
				currInterval = { el1: -1.0, el2: -1.0 };
				currUnpaired = [];
			}
			else if (isPaired5)
			{
				currInterval.el2 = baseAngle;
			}
			else
			{
				currUnpaired.push(l);
			}
			angles[l] = baseAngle;
			if (isPaired3)
			{
				baseAngle += angleIncrementBP;
			}
			else {
				baseAngle += angleIncrementML;
			}
		}
		currInterval.el1 = dirAngle - Math.PI - 0.5 * angleIncrementBP;
		intervals.push( {el1: currUnpaired, el2: currInterval } );

		for(var z = 0; z < intervals.length; z++){
			var mina = intervals[z].el2.el1;
			var maxa = normalizeAngle(intervals[z].el2.el2, mina);

			for (var n = 0; n < intervals[z].el1.length; n++){
				var ratio = (1. + n)/(1. + intervals[z].el1.length);
				var b = intervals[z].el1[n];
				angles[b] = mina + (1.-ratio)*(maxa-mina);
			}
		}

		for (k = basesMultiLoop.length - 1; k >= 0; k--) {
			l = basesMultiLoop[k];
			coords[l].x = mlCenter.x + multiLoopRadius * Math.cos(angles[l]);
			coords[l].y = mlCenter.y + multiLoopRadius * Math.sin(angles[l]);
		}

		var newAngle;
		var m, n;
		for (k = 0; k < helices.length; k++) {
			m = helices[k];
			n = getPartner(m, links);
			newAngle = (angles[m] + angles[n]) / 2.0;
			drawLoop(m + 1, n - 1, (40 * Math.cos(newAngle)) + (coords[m].x + coords[n].x) / 2.0,
						(40 * Math.sin(newAngle))
								+ (coords[m].y + coords[n].y) / 2.0, newAngle,
						coords, centers, angles, seq, links);
			}
		}
}

function determineRadius(nbHel, nbUnpaired, startRadius, bpdist, multidist) {
	var xmin = bpdist / 2.0;
	var xmax = 3.0 * multidist + 1;
	var x = (xmin + xmax) / 2.0;
	var y = 10000.0;
	var ymin = -1000.0;
	var ymax = 1000.0;
	var numIt = 0;
	var precision = 0.00001;
	while ((Math.abs(y) > precision) && (numIt < 10000)) {
		x = (xmin + xmax) / 2.0;
		y = objFun(nbHel, nbUnpaired, x, bpdist, multidist);
		ymin = objFun(nbHel, nbUnpaired, xmax, bpdist, multidist);
		ymax = objFun(nbHel, nbUnpaired, xmin, bpdist, multidist);
		if (ymin > 0.0) {
			xmax = xmax + (xmax - xmin);
		} else if ((y <= 0.0) && (ymax > 0.0)) {
			xmax = x;
		} else if ((y >= 0.0) && (ymin < 0.0)) {
			xmin = x;
		} else if (ymax < 0.0) {
			xmin = Math.max(xmin - (x - xmin),
					Math.max(bpdist / 2.0, multidist / 2.0));
			xmax = x;
		}
		numIt++;
	}
	return x;
}

function objFun(n1, n2, r, bpdist, multidist) {
	return ( n1 * 2.0 * Math.asin(bpdist / (2.0 * r)) + n2 * 2.0
				* Math.asin( multidist / (2.0 * r)) - (2.0 * Math.PI));
}

function correctHysteresis(angle){
	var hystAttr = [ 0.0, Math.PI/4.0, Math.PI/2.0, 3.0*Math.PI/4.0, Math.PI, 5.0*(Math.PI)/4.0, 3.0*(Math.PI)/2.0, 7.0*(Math.PI)/4.0];
	var result = normalizeAngleSec(angle);
	for (var i = 0; i < hystAttr.length; i++){
		var att = hystAttr[i];
		if (Math.abs(t.normalizeAngle(att-result,-Math.PI)) < 0.15){
			result = att;
		}
	}
	return result;
}

function normalizeAngleSec(angle){
	return t.normalizeAngle(angle,0.0);
}

function normalizeAngle(angle,fromVal) {
	var toVal = fromVal +2.0*Math.PI;
	var result = angle;
	while(result<fromVal){
		result += 2.0*Math.PI;
	}
	while(result >= toVal)
	{
		result -= 2.0*Math.PI;
	}
	return result;
}
