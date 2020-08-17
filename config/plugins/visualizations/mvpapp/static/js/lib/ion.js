// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

function Ion (t, color, charge, terminus) {
	this.type = t;
	this.color = color;
	this.charge = charge;
	this.label = this.type;
	if(this.charge > 1)
		this.label += charge;
	this.label += "+";
	this.term = terminus;
}

// Source: http://en.wikipedia.org/wiki/Web_colors

// charge +1
Ion.A_1 = new Ion("a", "#008000", 1, "n"); // green
Ion.B_1 = new Ion("b", "#0000ff", 1, "n"); // blue
Ion.C_1 = new Ion("c", "#008B8B", 1, "n"); // dark cyan
Ion.X_1 = new Ion("x", "#4B0082", 1, "c"); // indigo
Ion.Y_1 = new Ion("y", "#ff0000", 1, "c"); // red
Ion.Z_1 = new Ion("z", "#FF8C00", 1, "c"); // dark orange

// charge +2
Ion.A_2 = new Ion("a", "#2E8B57", 2, "n"); // sea green
Ion.B_2 = new Ion("b", "#4169E1", 2, "n"); // royal blue
Ion.C_2 = new Ion("c", "#20B2AA", 2, "n"); // light sea green
Ion.X_2 = new Ion("x", "#800080", 2, "c"); // purple
Ion.Y_2 = new Ion("y", "#FA8072", 2, "c"); // salmon 
Ion.Z_2 = new Ion("z", "#FFA500", 2, "c"); // orange 

// charge +3
Ion.A_3 = new Ion("a", "#9ACD32", 3, "n"); // yellow green
Ion.B_3 = new Ion("b", "#00BFFF", 3, "n"); // deep sky blue
Ion.C_3 = new Ion("c", "#66CDAA", 3, "c"); // medium aquamarine
Ion.X_3 = new Ion("x", "#9932CC", 3, "c"); // dark orchid
Ion.Y_3 = new Ion("y", "#FFA07A", 3, "c"); // light salmon
Ion.Z_3 = new Ion("z", "#FFD700", 3, "n"); // gold

Ion.MH_1 = new Ion("mh", "#2F4F4F", 1, null);
Ion.MH_2 = new Ion("mh", "#708090", 2, null);

var _ions = [];
_ions["a"] = [];
_ions["a"][1] = Ion.A_1;
_ions["a"][2] = Ion.A_2;
_ions["a"][3] = Ion.A_3;
_ions["b"] = [];
_ions["b"][1] = Ion.B_1;
_ions["b"][2] = Ion.B_2;
_ions["b"][3] = Ion.B_3;
_ions["c"] = [];
_ions["c"][1] = Ion.C_1;
_ions["c"][2] = Ion.C_2;
_ions["c"][3] = Ion.C_3;
_ions["x"] = [];
_ions["x"][1] = Ion.X_1;
_ions["x"][2] = Ion.X_2;
_ions["x"][3] = Ion.X_3;
_ions["y"] = [];
_ions["y"][1] = Ion.Y_1;
_ions["y"][2] = Ion.Y_2;
_ions["y"][3] = Ion.Y_3;
_ions["z"] = [];
_ions["z"][1] = Ion.Z_1;
_ions["z"][2] = Ion.Z_2;
_ions["z"][3] = Ion.Z_3;
_ions["mh"] = [];
_ions["mh"][1] = Ion.MH_1;
_ions["mh"][2] = Ion.MH_2;

Ion.get = function _getIon(type, charge) {
	
	return _ions[type][charge];
}

Ion.getSeriesColor = function _getSeriesColor(ion) {
	
	return _ions[ion.type][ion.charge].color;
}


//-----------------------------------------------------------------------------
// Ion Series
//-----------------------------------------------------------------------------
var MASS_H_1 = 1.00782503207;  	// H(1)  Source: http://en.wikipedia.org/wiki/Isotopes_of_hydrogen
var MASS_C_12 = 12.0;           // C(12) Source: http://en.wikipedia.org/wiki/Isotopes_of_carbon
var MASS_N_14 = 14.0030740048;  // N(14) Source: http://en.wikipedia.org/wiki/Isotopes_of_nitrogen
var MASS_O_16 = 15.99491461956; // O(16) Source: http://en.wikipedia.org/wiki/Isotopes_of_oxygen

var MASS_H = 1.00782504; // Source: http://en.wikipedia.org/wiki/Isotopes_of_hydrogen
var MASS_C = 12.0107;    // Source: http://en.wikipedia.org/wiki/Isotopes_of_carbon
var MASS_N = 14.0067;	 // Source: http://en.wikipedia.org/wiki/Isotopes_of_nitrogen
var MASS_O = 15.9994;	 // Source: http://en.wikipedia.org/wiki/Isotopes_of_oxygen

var MASS_PROTON = 1.007276;

Ion.MASS_PROTON = MASS_PROTON;
Ion.MASS_H = MASS_H;
Ion.MASS_C = MASS_C;
Ion.MASS_N = MASS_N;
Ion.MASS_O = MASS_O;
Ion.MASS_H_1 = MASS_H_1;
Ion.MASS_C_12 = MASS_C_12;
Ion.MASS_N_14 = MASS_N_14;
Ion.MASS_O_16 = MASS_O_16;

// massType can be "mono" or "avg"
Ion.getSeriesIon = function _getSeriesIon(ion, peptide, idxInSeq, massType) {
	if(ion.type == "a")	
		return new Ion_A (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "b")
		return new Ion_B (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "c")
		return new Ion_C (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "x")
		return new Ion_X (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "y")
		return new Ion_Y (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "z")
		return new Ion_Z (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "mh")
		return new Ion_MH (peptide, ion.charge, massType);
}

function _makeIonLabel(type, index, charge) {
	var label = type+""+index;
	for(var i = 1; i <= charge; i+=1) 
		label += "+";
	return label;
}

function _getMz(neutralMass, charge) {
	return ( neutralMass + (charge * MASS_PROTON) ) / charge;
}

function _getWaterLossMz(sion) {
  var massType = sion.massType;
  var mass_h = MASS_H;
  var mass_o = MASS_O;
  if(massType == "mono") {
    mass_h = MASS_H_1;
    mass_o = MASS_O_16;
  }
	var neutralMass = (sion.mz * sion.charge) - (sion.charge * MASS_PROTON);
	return _getMz((neutralMass - (mass_h * 2 + mass_o)), sion.charge);
}

function _getAmmoniaLossMz(sion) {
  var massType = sion.massType;
  var mass_h = MASS_H;
  var mass_n = MASS_O;
  if(massType == "mono") {
    mass_h = MASS_H_1;  
    mass_n = MASS_N_14;
  }
	var neutralMass = (sion.mz * sion.charge) - (sion.charge * MASS_PROTON);
	return _getMz((neutralMass - (mass_h * 3 + mass_n)), sion.charge);
}

Ion.getMz = _getMz;
Ion.getWaterLossMz = _getWaterLossMz;
Ion.getAmmoniaLossMz = _getAmmoniaLossMz;

function Ion_A (peptide, endIdxPlusOne, charge, massType) {
	// Neutral mass:  	 [N]+[M]-CHO  ; N = mass of neutral N terminal group
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(endIdxPlusOne, "n") - (MASS_C_12 + MASS_O_16);
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(endIdxPlusOne, "n") - (MASS_C + MASS_O);
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(endIdxPlusOne, "n");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("a",endIdxPlusOne, charge);
	this.match = false;
	this.term = "n";
	return this;
}

function Ion_B (peptide, endIdxPlusOne, charge, massType) {
	// Neutral mass:    [N]+[M]-H  ; N = mass of neutral N terminal group
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(endIdxPlusOne, "n");
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(endIdxPlusOne, "n");
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(endIdxPlusOne, "n");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("b", endIdxPlusOne, charge);
	this.match = false;
	this.term = "n";
	return this;
}

function Ion_C (peptide, endIdxPlusOne, charge, massType) {
	// Neutral mass:    [N]+[M]+NH2  ; N = mass of neutral N terminal group
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(endIdxPlusOne, "n") + MASS_H_1 + (MASS_N_14 + 2*MASS_H_1);
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(endIdxPlusOne, "n") + MASS_H + (MASS_N + 2*MASS_H);
  this.massType = massType;
  this.subSequence = peptide.getSubSequence(endIdxPlusOne, "n");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("c", endIdxPlusOne, charge);
	this.match = false;
	this.term = "n";
	return this;
}

function Ion_X (peptide, startIdx, charge, massType) {
	// Neutral mass = [C]+[M]+CO-H ; C = mass of neutral C-terminal group (OH)
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(startIdx, "c") + 2*MASS_O_16 + MASS_C_12;
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(startIdx, "c") + 2*MASS_O + MASS_C;
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(startIdx, "c");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("x", peptide.sequence().length - startIdx, charge);
	this.match = false;
	this.term = "c";
	return this;
}

function Ion_Y (peptide, startIdx, charge, massType) {
	// Neutral mass = [C]+[M]+H ; C = mass of neutral C-terminal group (OH)
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(startIdx, "c") + 2*MASS_H_1 + MASS_O_16;
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(startIdx, "c") + 2*MASS_H + MASS_O;
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(startIdx, "c");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
    this.label = _makeIonLabel("y", peptide.sequence().length - startIdx, charge);
	this.match = false;
	this.term = "c";
	return this;
}

function Ion_Z (peptide, startIdx, charge, massType) {
	// Neutral mass = [C]+[M]-NH2 ; C = mass of neutral C-terminal group (OH)
	// We're really printing Z-dot ions so we add an H to make it OH+[M]-NH2 +H = [M]+O-N
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(startIdx, "c") + MASS_O_16 - MASS_N_14;
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(startIdx, "c") + MASS_O - MASS_N;
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(startIdx, "c");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("z", peptide.sequence().length - startIdx, charge);
	this.match = false;
	this.term = "c";
	return this;
}

function Ion_MH (peptide, charge, massType) {
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getNeutralMassMono();
	else if(massType == "avg")
		mass = peptide.getNeutralMassAvg();
	this.massType = massType;
	this.subSequence = peptide.sequence();
	this.charge = charge;
	this.mz = ( mass + (charge * MASS_PROTON) ) / charge;
	this.label = _makeIonLabel("MH", "", charge);
	this.match = false;
	this.term = null;
	return this;
}


function NeutralLoss (label, residues) {
	this.label = label;
	this.residues = residues;


	this.applies = function _applies(sion) {
		if(!this.residues) {
			return true;
		}
		if(sion.internal && sion.minus28) {
			return false;
		}
		var sequence = sion.subSequence;
		for(var i = 0; i < this.residues.length; i++) {
			if(sequence.indexOf(this.residues[i]) >= 0) {
				return true;
			}
		}
		return false;
	}
}


NeutralLoss.get = function _getNeutralLoss(label, residueSpecific) {
	if(!label) {
		return new NeutralLoss(null, null);
	} else if(label == 'nh3') {
		return new NeutralLoss('nh3', residueSpecific ? 'RKQN' : null);
	} else if(label == 'h2o') {
		return new NeutralLoss('h2o', residueSpecific ? 'STED' : null);
	}
	throw "unknown neutral loss label " + label;
}

