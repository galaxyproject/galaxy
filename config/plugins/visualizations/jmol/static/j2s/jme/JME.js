Clazz.declarePackage("jme");
Clazz.load(["javax.swing.JFrame", "$.JPanel", "java.util.ArrayList", "javax.swing.JTextField"], ["jme.MultiBox", "$.QueryBox", "$.JME"], ["java.io.FileInputStream", "java.util.StringTokenizer", "JU.Rdr", "javax.swing.JButton", "$.JComboBox", "$.JLabel", "jme.JMEmol"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.myFrame = null;
this.aboutBoxPoint = null;
this.smilesBoxPoint = null;
this.atomxBoxPoint = null;
this.atomicSymbol = null;
this.$action = 0;
this.active_an = 0;
this.application = false;
this.infoText = "JME Molecular Editor by Peter Ertl";
this.sd = 24;
this.arrowWidth = 48;
this.$font = null;
this.fontBold = null;
this.fontSmall = null;
this.fontMet = null;
this.fontBoldMet = null;
this.fontSmallMet = null;
this.fontSize = 0;
this.bwMode = false;
this.runsmi = false;
this.depictcgi = null;
this.depictservlet = null;
this.canonize = true;
this.stereo = true;
this.multipart = false;
this.xButton = true;
this.rButton = false;
this.showHydrogens = true;
this.query = false;
this.reaction = false;
this.autoez = false;
this.writesmi = false;
this.writemi = false;
this.writemol = false;
this.number = false;
this.star = false;
this.autonumber = false;
this.jmeh = false;
this.depict = false;
this.depictBorder = false;
this.keepHydrogens = true;
this.canvasBg = null;
this.atomColors = null;
this.atomBgColors = null;
this.depictScale = 1.;
this.nocenter = false;
this.polarnitro = false;
this.$showAtomNumbers = false;
this.$smiles = null;
this.jmeString = null;
this.molString = null;
this.dimension = null;
this.topMenu = null;
this.leftMenu = null;
this.infoArea = null;
this.molecularArea = null;
this.doMenu = true;
this.movePossible = false;
this.lastAction = 0;
this.newMolecule = false;
this.xold = 0;
this.yold = 0;
this.afterClear = false;
this.mouseShift = false;
this.smilesBox = null;
this.atomxBox = null;
this.aboutBox = null;
this.queryBox = null;
this.point = null;
this.c = null;
this.n = null;
this.o = null;
this.s = null;
this.p = null;
this.f = null;
this.cl = null;
this.br = null;
this.i = null;
this.any = null;
this.anyec = null;
this.halogen = null;
this.aromatic = null;
this.nonaromatic = null;
this.ring = null;
this.nonring = null;
this.anyBond = null;
this.aromaticBond = null;
this.ringBond = null;
this.nonringBond = null;
this.sdBond = null;
this.choiced = null;
this.choiceh = null;
this.dyMode = true;
this.molText = null;
this.mol = null;
this.nmols = 0;
this.actualMolecule = 0;
this.saved = 0;
this.template = null;
this.tmol = null;
this.mols = null;
this.smol = null;
this.psColor = null;
this.molStack = null;
this.stackPointer = -1;
this.doTags = false;
this.webme = false;
this.apointx = null;
this.apointy = null;
this.bpointx = null;
this.bpointy = null;
this.revertStereo = false;
this.relativeStereo = false;
this.allHs = false;
this.markUsed = true;
this.currentMark = 1;
this.infoImage = null;
this.clearImage = null;
this.deleteImage = null;
this.deleterImage = null;
this.chargeImage = null;
this.templatesImage = null;
this.rtemplatesImage = null;
this.undoImage = null;
this.endImage = null;
this.smiImage = null;
this.smitImage = null;
this.smartsImage = null;
this.stereoImage = null;
this.stereoxImage = null;
this.embedded = false;
Clazz.instantialize(this, arguments);}, jme, "JME", javax.swing.JPanel, [java.awt.event.MouseListener, java.awt.event.KeyListener, java.awt.event.MouseMotionListener]);
Clazz.prepareFields (c$, function(){
this.aboutBoxPoint =  new java.awt.Point(500, 10);
this.smilesBoxPoint =  new java.awt.Point(200, 50);
this.atomxBoxPoint =  new java.awt.Point(150, 420);
this.atomicSymbol =  new javax.swing.JTextField("H");
this.canvasBg = java.awt.Color.white;
this.point =  new java.awt.Point(20, 200);
this.mols =  new Array(99);
this.psColor =  new Array(7);
this.molStack =  new java.util.ArrayList();
});
Clazz.makeConstructor(c$, 
function(){
this.construct (null, true);
});
Clazz.makeConstructor(c$, 
function(frame, embedded){
Clazz.superConstructor (this, jme.JME, []);
if (frame != null) {
this.setFrame(frame);
}this.embedded = embedded;
this.mol =  new jme.JMEmol(this);
this.psColor[0] = java.awt.Color.gray;
this.psColor[1] =  new java.awt.Color(255, 153, 153);
this.psColor[2] =  new java.awt.Color(255, 204, 102);
this.psColor[3] =  new java.awt.Color(255, 255, 153);
this.psColor[4] =  new java.awt.Color(102, 255, 255);
this.psColor[5] =  new java.awt.Color(51, 204, 255);
this.psColor[6] =  new java.awt.Color(255, 153, 255);
this.initialize();
this.start();
}, "javax.swing.JFrame,~B");
Clazz.defineMethod(c$, "setFrame", 
function(frame){
this.myFrame = frame;
frame.add("Center", this);
frame.addKeyListener(this);
this.addMouseListener(this);
this.addMouseMotionListener(this);
this.application = true;
}, "javax.swing.JFrame");
c$.main = Clazz.defineMethod(c$, "main", 
function(args){
var frame =  new javax.swing.JFrame("JME 2D Molecular Editor");
frame.setDefaultCloseOperation(3);
var jme =  new jme.JME(frame, false);
var w = 432;
var h = 384;
frame.setBounds(300, 200, w, h);
if (args.length == 1) jme.options(args[0]);
frame.setVisible(true);
var fileName = null;
for (var i = 0; i < args.length; i++) {
if ("-embedded".equals(args[i])) {
jme.embedded = true;
} else if ("-s".equals(args[i])) {
} else if (args[i].startsWith("-f")) {
fileName = args[++i];
} else if (args[i].startsWith("-o")) {
jme.options(args[++i]);
}}
if (fileName != null) {
jme.dimension = jme.getSize();
try {
jme.readMolecule(JU.Rdr.streamToString( new java.io.FileInputStream(fileName)));
} catch (e) {
if (Clazz.exceptionOf(e,"java.io.IOException")){
System.err.println("File " + fileName + " could not be read");
} else {
throw e;
}
}
}}, "~A");
Clazz.defineMethod(c$, "getColor", 
function(){
return jme.JME.bgColor;
});
Clazz.defineMethod(c$, "activateQuery", 
function(){
if (this.$action != 107) {
this.$action = 107;
this.repaint();
}});
Clazz.defineMethod(c$, "initialize", 
function(){
this.dimension = this.getSize();
this.setLayout(null);
this.fontSize = 12;
if (this.$font == null) {
this.$font =  new java.awt.Font("Helvetica", 0, this.fontSize);
this.fontMet = this.getFontMetrics(this.$font);
}if (this.fontBold == null) {
this.fontBold =  new java.awt.Font("Helvetica", 1, this.fontSize);
this.fontBoldMet = this.getFontMetrics(this.fontBold);
}var fs = this.fontSize;
if (this.fontSmall == null) {
this.fontSmall =  new java.awt.Font("Helvetica", 0, fs);
this.fontSmallMet = this.getFontMetrics(this.fontSmall);
}this.query = false;
this.reaction = false;
this.autoez = false;
this.stereo = true;
this.canonize = true;
this.xButton = true;
this.rButton = false;
jme.JME.ACTIONA = 10;
this.showHydrogens = true;
this.$action = 202;
jme.JME.atomicData();
this.validate();
});
Clazz.defineMethod(c$, "start", 
function(){
this.dimension = this.getSize();
if (this.jmeString != null) {
this.readMolecule(this.jmeString);
} else if (this.molString != null) this.readMolFile(this.molString);
});
Clazz.defineMethod(c$, "stop", 
function(){
if (this.smilesBox != null) this.smilesBox.dispose();
if (this.atomxBox != null) this.atomxBox.dispose();
if (this.aboutBox != null) this.aboutBox.dispose();
if (this.queryBox != null) this.queryBox.dispose();
this.mols = null;
});
Clazz.defineMethod(c$, "ping", 
function(){
});
Clazz.defineMethod(c$, "smiles", 
function(){
var smiles = this.Smiles();
this.repaint();
return smiles;
});
Clazz.defineMethod(c$, "nonisomericSmiles", 
function(){
var originalStereo = this.stereo;
this.stereo = false;
var smiles = this.Smiles();
this.stereo = originalStereo;
this.repaint();
return smiles;
});
Clazz.defineMethod(c$, "Smiles", 
function(){
var s;
if (this.reaction) s = this.partSmiles(1) + ">" + this.partSmiles(2) + ">" + this.partSmiles(3);
 else {
s = this.partSmiles(0);
if (s.length > 0) {
this.molStack.add( new jme.JMEmol(this.mol));
this.stackPointer = this.molStack.size() - 1;
}}return s;
});
Clazz.defineMethod(c$, "partSmiles", 
function(pp){
var s = "";
for (var m = 1; m <= this.nmols; m++) {
if (pp > 0) {
var p = this.mols[m].reactionPart();
if (p != pp) continue;
}var smiles = this.mols[m].createSmiles();
if (smiles.length > 0) {
if (s.length > 0) s += ".";
s += smiles;
}}
return s;
}, "~N");
Clazz.defineMethod(c$, "reset", 
function(){
this.$action = 202;
this.newMolecule = false;
this.nmols = 0;
this.actualMolecule = 0;
this.mol =  new jme.JMEmol(this);
this.mol.maxMark = 0;
this.molText = null;
this.depictScale = 1.;
this.repaint();
});
Clazz.defineMethod(c$, "clear", 
function(){
this.$action = 202;
this.newMolecule = false;
if (this.nmols == 0) return;
this.mol.save();
this.afterClear = true;
for (var i = this.actualMolecule; i < this.nmols; i++) this.mols[i] = this.mols[i + 1];

this.nmols--;
this.actualMolecule = this.nmols;
if (this.nmols > 0) this.mol = this.mols[this.actualMolecule];
 else {
this.mol =  new jme.JMEmol(this);
this.mol.maxMark = 0;
}});
Clazz.defineMethod(c$, "jmeFile", 
function(){
var s = "";
if (this.reaction) s = this.partJme(1) + ">" + this.partJme(2) + ">" + this.partJme(3);
 else s = this.partJme(0);
return s;
});
Clazz.defineMethod(c$, "partJme", 
function(pp){
var s = "";
for (var m = 1; m <= this.nmols; m++) {
if (pp > 0) {
var p = this.mols[m].reactionPart();
if (p != pp) continue;
}var jme = this.mols[m].createJME();
if (jme.length > 0) {
if (s.length > 0) s += "|";
s += jme;
}}
return s;
}, "~N");
Clazz.defineMethod(c$, "getReactionParts", 
function(){
var part =  Clazz.newIntArray (4, this.nmols + 1, 0);
for (var p = 1; p <= 3; p++) {
var np = 0;
for (var m = 1; m <= this.nmols; m++) if (this.mols[m].reactionPart() == p) part[p][++np] = m;

part[p][0] = np;
}
return part;
});
Clazz.defineMethod(c$, "readMolecule", 
function(molecule){
this.reset();
var lastReactant = 0;
var firstProduct = 0;
var st =  new java.util.StringTokenizer(molecule, "|>", true);
var isReaction = (molecule.indexOf(">") > -1);
var rx = 1;
var nt = st.countTokens();
this.nmols = 0;
for (var i = 1; i <= nt; i++) {
var s = st.nextToken();
s.trim();
if (s.equals("|")) continue;
if (s.equals(">")) {
rx++;
if (rx == 2) lastReactant = this.nmols;
 else if (rx == 3) firstProduct = this.nmols + 1;
continue;
}this.mol =  new jme.JMEmol(this, s, true);
if (this.mol.natoms == 0) {
this.info("ERROR - problems in reading/processing molecule !");
System.err.println("ERROR while processing\n" + s);
continue;
}this.nmols++;
this.actualMolecule = this.nmols;
this.mols[this.nmols] = this.mol;
this.smol = null;
}
if (rx == 2) {
firstProduct = lastReactant + 1;
this.info("ERROR - strange reaction - fixing !");
System.err.println("ERROR - reactant and product should be separated by >>\n");
} else if (rx > 3) {
this.info("ERROR - strange reaction !");
System.err.println("ERROR - strange reaction !\n");
return;
}if (this.nmols > 1 && !isReaction) this.options("multipart");
if (isReaction && !this.reaction) this.options("reaction");
if (!isReaction && this.reaction) this.options("noreaction");
if (!isReaction) this.alignMolecules(1, this.nmols, 0);
 else {
this.alignMolecules(1, lastReactant, 1);
this.alignMolecules(lastReactant + 1, firstProduct - 1, 2);
this.alignMolecules(firstProduct, this.nmols, 3);
}this.setMol(false);
this.repaint();
}, "~S");
Clazz.defineMethod(c$, "setTemplate", 
function(t, name){
this.afterClear = false;
this.tmol =  new jme.JMEmol(this, t, true);
this.tmol.complete();
this.$action = 253;
this.info(name);
this.repaint();
}, "~S,~S");
Clazz.defineMethod(c$, "alignMolecules", 
function(m1, m2, part){
if (this.nocenter) return;
var nm = m2 - m1 + 1;
if (nm <= 0 || m1 > this.nmols || m2 > this.nmols) return;
var center =  Clazz.newDoubleArray (4, 0);
var RBOND = 25;
var share =  Clazz.newDoubleArray (99, 0);
var sumx = 0.;
var sumy = 0.;
var maxy = 0.;
for (var i = m1; i <= m2; i++) {
this.mols[i].centerPoint(center);
sumx += center[2];
sumy += center[3];
if (center[3] > maxy) maxy = center[3];
share[i] = center[2];
if (part == 2) share[i] = center[3];
}
if (this.depict) {
sumx += RBOND * (nm + 1);
sumy += RBOND * (nm + 1);
maxy += RBOND;
}if (this.dimension.width == 0 || this.dimension.height == 0) this.dimension = this.getSize();
if (this.dimension.width == 0) this.dimension.width = 400;
if (this.dimension.height == 0) this.dimension.height = 300;
var scalex = 1.;
var scaley = 1.;
var xsize = this.dimension.width;
var ysize = this.dimension.height;
if (!this.depict) {
xsize -= this.sd;
ysize -= 3 * this.sd;
}if (part == 1 || part == 3) xsize = Clazz.doubleToInt((xsize - this.arrowWidth) / 2);
 else if (part == 2) ysize = Clazz.doubleToInt(ysize / 2);
if (sumx >= xsize) scalex = (xsize) / sumx;
if (maxy >= ysize) scaley = (ysize) / maxy;
var medzera = 0.;
if (this.depict) {
this.depictScale = Math.min(scalex, scaley);
medzera = RBOND * xsize / sumx;
if (part == 2) medzera = RBOND * ysize / sumy;
}for (var i = m1; i <= m2; i++) {
if (part == 2) share[i] = share[i] * ysize / sumy;
 else share[i] = share[i] * xsize / sumx;
}
var shiftx = -xsize / 2.;
var shifty = 0.;
if (part == 1) shiftx = -xsize - this.arrowWidth / 2.;
 else if (part == 3) shiftx = this.arrowWidth / 2.;
 else if (part == 2) {
shiftx = 0.;
shifty = -ysize;
}for (var i = m1; i <= m2; i++) {
if (this.depict) {
for (var a = 1; a <= this.mols[i].natoms; a++) {
this.mols[i].x[a] *= this.depictScale;
this.mols[i].y[a] *= this.depictScale;
}
this.mols[i].center();
}if (part == 2) shifty += (share[i] / 2. + medzera);
 else shiftx += (share[i] / 2. + medzera);
for (var a = 1; a <= this.mols[i].natoms; a++) {
this.mols[i].x[a] += shiftx;
this.mols[i].y[a] += shifty;
}
if (part == 2) shifty += share[i] / 2.;
 else shiftx += share[i] / 2.;
if (!this.depict) this.mols[i].findBondCenters();
}
}, "~N,~N,~N");
Clazz.defineMethod(c$, "molFile", 
function(){
var s = "";
if (this.reaction) {
var part = this.getReactionParts();
s += "$RXN\n\n\nJME Molecular Editor\n";
s += jme.JMEmol.iformat(part[1][0], 3) + jme.JMEmol.iformat(part[3][0], 3) + "\n";
for (var i = 1; i <= part[1][0]; i++) s += "$MOL" + "\n" + this.mols[part[1][i]].createMolFile(this.$smiles);

for (var i = 1; i <= part[3][0]; i++) s += "$MOL" + "\n" + this.mols[part[3][i]].createMolFile(this.$smiles);

} else {
if (this.nmols > 1) this.mol =  new jme.JMEmol(this, this.mols, this.nmols);
if (this.mol.natoms > 0) s = this.mol.createMolFile("");
if (this.nmols > 1) this.mol = this.mols[this.actualMolecule];
}return s;
});
Clazz.defineMethod(c$, "readMolFile", 
function(s){
this.reset();
if (s.startsWith("$RXN")) {
this.reaction = true;
this.multipart = true;
var separator = jme.JMEmol.findSeparator(s);
var st =  new java.util.StringTokenizer(s, separator, true);
var line = "";
for (var i = 1; i <= 5; i++) {
line = jme.JMEmol.nextData(st, separator);
}
var nr = Integer.$valueOf(line.substring(0, 3).trim()).intValue();
var np = Integer.$valueOf(line.substring(3, 6).trim()).intValue();
jme.JMEmol.nextData(st, separator);
for (var p = 1; p <= nr + np; p++) {
var m = "";
while (true) {
var ns = jme.JMEmol.nextData(st, separator);
if (ns == null || ns.equals("$MOL")) break;
m += ns + separator;
}
this.mols[++this.nmols] =  new jme.JMEmol(this, m);
}
this.alignMolecules(1, nr, 1);
this.alignMolecules(nr + 1, nr + np, 3);
} else {
this.reaction = false;
this.mol =  new jme.JMEmol(this, s);
this.setMol(true);
}this.repaint();
}, "~S");
Clazz.defineMethod(c$, "setMol", 
function(checkMultipart){
if (this.mol == null || this.mol.natoms == 0) {
return true;
}if (this.atomBgColors != null && this.mol != null) this.mol.setAtomColors(this.atomBgColors, true);
if (this.atomColors != null && this.mol != null) this.mol.setAtomColors(this.atomColors, false);
if (!checkMultipart) return false;
var nparts = this.mol.checkMultipart(false);
if (nparts == 1) {
this.mols[++this.nmols] = this.mol;
} else {
this.multipart = true;
for (var p = 1; p <= nparts; p++) this.mols[++this.nmols] =  new jme.JMEmol(this, this.mol, p);

}this.actualMolecule = 1;
this.mol = this.mols[this.actualMolecule];
this.smol = null;
this.alignMolecules(1, nparts, 0);
return true;
}, "~B");
Clazz.defineMethod(c$, "setSubstituent", 
function(s){
var pressed = -1;
if (s.equals("Select substituent")) {
pressed = 202;
s = "";
} else if (s.equals("-C(=O)OH")) pressed = 235;
 else if (s.equals("-C(=O)OMe")) pressed = 240;
 else if (s.equals("-OC(=O)Me")) pressed = 241;
 else if (s.equals("-CMe3")) pressed = 233;
 else if (s.equals("-CF3")) pressed = 236;
 else if (s.equals("-CCl3")) pressed = 237;
 else if (s.equals("-NO2")) pressed = 234;
 else if (s.equals("-NMe2")) pressed = 243;
 else if (s.equals("-SO2-NH2")) pressed = 252;
 else if (s.equals("-NH-SO2-Me")) pressed = 244;
 else if (s.equals("-SO3H")) pressed = 239;
 else if (s.equals("-PO3H2")) pressed = 251;
 else if (s.equals("-C#N")) pressed = 242;
 else if (s.equals("-C#C-Me")) pressed = 245;
 else if (s.equals("-C#CH")) pressed = 238;
if (pressed > 0) this.menuAction(pressed);
 else s = "Not known group!";
this.info(s);
this.repaint();
}, "~S");
Clazz.defineMethod(c$, "options", 
function(parameters){
parameters = parameters.toLowerCase();
if (parameters.indexOf("norbutton") > -1) this.rButton = false;
 else if (parameters.indexOf("rbutton") > -1) this.rButton = true;
if (parameters.indexOf("nohydrogens") > -1) this.showHydrogens = false;
 else if (parameters.indexOf("hydrogens") > -1) this.showHydrogens = true;
if (parameters.indexOf("keephs") > -1) this.keepHydrogens = true;
if (parameters.indexOf("removehs") > -1) this.keepHydrogens = false;
if (parameters.indexOf("noquery") > -1) this.query = false;
 else if (parameters.indexOf("query") > -1) this.query = true;
if (parameters.indexOf("noreaction") > -1) this.reaction = false;
 else if (parameters.indexOf("reaction") > -1) this.reaction = true;
if (parameters.indexOf("noautoez") > -1) this.autoez = false;
 else if (parameters.indexOf("autoez") > -1) this.autoez = true;
if (parameters.indexOf("nostereo") > -1) this.stereo = false;
 else if (parameters.indexOf("stereo") > -1) this.stereo = true;
if (parameters.indexOf("nocanonize") > -1) this.canonize = false;
 else if (parameters.indexOf("canonize") > -1) this.canonize = true;
if (parameters.indexOf("nomultipart") > -1) this.multipart = false;
 else if (parameters.indexOf("multipart") > -1) this.multipart = true;
if (parameters.indexOf("nonumber") > -1) {
this.number = false;
this.autonumber = false;
} else if (parameters.indexOf("number") > -1) {
this.number = true;
this.autonumber = false;
}if (parameters.indexOf("autonumber") > -1) {
this.autonumber = true;
this.number = true;
}if (parameters.indexOf("star") > -1) {
this.star = true;
this.number = true;
}if (parameters.indexOf("polarnitro") > -1) this.polarnitro = true;
if (parameters.indexOf("depict") > -1) {
this.depict = true;
this.sd = 0;
this.molecularArea = null;
this.alignMolecules(1, this.nmols, 0);
}if (parameters.indexOf("nodepict") > -1) {
this.depict = false;
for (var i = 1; i <= this.nmols; i++) {
this.mols[i].scaling();
this.mols[i].center();
}
this.depictScale = 1;
this.sd = 24;
if (this.mol != null) this.mol.needRecentering = true;
}if (parameters.indexOf("border") > -1) {
this.depictBorder = true;
}if (parameters.indexOf("writesmi") > -1) this.writesmi = true;
if (parameters.indexOf("writemi") > -1) this.writemi = true;
if (parameters.indexOf("writemol") > -1) this.writemol = true;
if (parameters.indexOf("nocenter") > -1) this.nocenter = true;
if (parameters.indexOf("jmeh") > -1) this.jmeh = true;
if (parameters.indexOf("showan") > -1) this.$showAtomNumbers = true;
if (this.reaction) {
this.number = true;
this.multipart = true;
}if (!this.depict) this.depictBorder = false;
if (this.rButton) jme.JME.ACTIONA++;
this.repaint();
}, "~S");
Clazz.defineMethod(c$, "setText", 
function(text){
this.molText = text;
this.repaint();
}, "~S");
Clazz.defineMethod(c$, "showAtomNumbers", 
function(){
if (this.mol != null) this.mol.numberAtoms();
});
Clazz.defineMethod(c$, "hasPrevious", 
function(){
if (this.molStack.size() == 0 || this.stackPointer == 0) return false;
return true;
});
Clazz.defineMethod(c$, "getPreviousMolecule", 
function(){
this.getFromStack(-1);
});
Clazz.defineMethod(c$, "getFromStack", 
function(n){
this.info("");
this.clear();
this.stackPointer += n;
this.mol =  new jme.JMEmol(this.molStack.get(this.stackPointer));
this.mol.complete();
this.mol.center();
this.nmols = 1;
this.actualMolecule = 1;
this.mols[1] = this.mol;
this.repaint();
this.smol = null;
}, "~N");
Clazz.overrideMethod(c$, "paint", 
function(g){
this.update(g);
}, "java.awt.Graphics");
Clazz.overrideMethod(c$, "update", 
function(g){
var d = this.getSize();
if (this.dimension == null || (d.width != this.dimension.width) || (d.height != this.dimension.height) || this.molecularArea == null || this.infoArea == null) {
this.dimension = d;
var imagew = d.width - this.sd;
var imageh = d.height - this.sd * 3;
if (imagew < 1) imagew = 1;
if (imageh < 1) imageh = 1;
this.molecularArea = this.createImage(imagew, imageh);
this.drawMolecularArea(g);
if (this.depict) return;
this.topMenu = this.createImage(d.width, this.sd * 2);
this.drawTopMenu(g);
imageh = d.height - this.sd * 2;
if (imageh < 1) imageh = 1;
this.leftMenu = this.createImage(this.sd, imageh);
this.drawLeftMenu(g);
this.infoArea = this.createImage(imagew, this.sd);
this.drawInfo(g);
} else {
this.drawMolecularArea(g);
if (this.depict) return;
this.drawInfo(g);
if (this.doMenu) {
this.drawTopMenu(g);
this.drawLeftMenu(g);
}this.doMenu = true;
}}, "java.awt.Graphics");
c$.atomicData = Clazz.defineMethod(c$, "atomicData", 
function(){
for (var i = 0; i < 23; i++) {
jme.JME.color[i] = java.awt.Color.orange;
jme.JME.zlabel[i] = "X";
}
jme.JME.zlabel[1] = "H";
jme.JME.color[1] = java.awt.Color.darkGray;
jme.JME.zlabel[2] = "B";
jme.JME.color[2] = java.awt.Color.orange;
jme.JME.zlabel[3] = "C";
jme.JME.color[3] = java.awt.Color.darkGray;
jme.JME.zlabel[4] = "N";
jme.JME.color[4] = java.awt.Color.blue;
jme.JME.zlabel[5] = "O";
jme.JME.color[5] = java.awt.Color.red;
jme.JME.zlabel[9] = "F";
jme.JME.color[9] = java.awt.Color.magenta;
jme.JME.zlabel[10] = "Cl";
jme.JME.color[10] = java.awt.Color.magenta;
jme.JME.zlabel[11] = "Br";
jme.JME.color[11] = java.awt.Color.magenta;
jme.JME.zlabel[12] = "I";
jme.JME.color[12] = java.awt.Color.magenta;
jme.JME.zlabel[8] = "S";
jme.JME.color[8] = java.awt.Color.yellow.darker();
jme.JME.zlabel[7] = "P";
jme.JME.color[7] = java.awt.Color.orange;
jme.JME.zlabel[6] = "Si";
jme.JME.color[6] = java.awt.Color.darkGray;
jme.JME.zlabel[13] = "Se";
jme.JME.color[13] = java.awt.Color.darkGray;
jme.JME.zlabel[18] = "X";
jme.JME.color[18] = java.awt.Color.darkGray;
jme.JME.zlabel[19] = "R";
jme.JME.color[19] = java.awt.Color.darkGray;
jme.JME.zlabel[20] = "R1";
jme.JME.color[20] = java.awt.Color.darkGray;
jme.JME.zlabel[21] = "R2";
jme.JME.color[21] = java.awt.Color.darkGray;
jme.JME.zlabel[22] = "R3";
jme.JME.color[22] = java.awt.Color.darkGray;
});
Clazz.defineMethod(c$, "drawMolecularArea", 
function(g){
this.paintMolecularArea(this.molecularArea);
g.drawImage(this.molecularArea, this.sd, this.sd * 2, this);
}, "java.awt.Graphics");
Clazz.defineMethod(c$, "paintMolecularArea", 
function(img){
var og = img.getGraphics();
og.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON);
var imgWidth = img.getWidth();
var imgHeight = img.getHeight();
og.setColor(this.canvasBg);
og.fillRect(0, 0, imgWidth, imgHeight);
for (var m = 1; m <= this.nmols; m++) this.mols[m].draw(og);

if (!this.depict) {
og.setColor(jme.JME.bgColor.darker());
og.drawLine(imgWidth - 1, 0, imgWidth - 1, imgHeight - 1);
og.setColor(jme.JME.bgColor);
og.drawLine(imgWidth - 2, 0, imgWidth - 2, imgHeight - 1);
og.setColor(jme.JME.brightColor);
og.drawLine(imgWidth - 3, 0, imgWidth - 3, imgHeight - 1);
}if (this.reaction) {
var pWidth = this.arrowWidth;
var pStart = Clazz.doubleToInt((imgWidth - pWidth) / 2);
var m = Clazz.doubleToInt(this.arrowWidth / 8);
og.setColor(java.awt.Color.magenta);
og.drawLine(pStart, Clazz.doubleToInt(imgHeight / 2), pStart + pWidth, Clazz.doubleToInt(imgHeight / 2));
og.drawLine(pStart + pWidth, Clazz.doubleToInt(imgHeight / 2), pStart + pWidth - m, Clazz.doubleToInt(imgHeight / 2) + m);
og.drawLine(pStart + pWidth, Clazz.doubleToInt(imgHeight / 2), pStart + pWidth - m, Clazz.doubleToInt(imgHeight / 2) - m);
}if (this.depict) {
this.$font =  new java.awt.Font("Helvetica", 0, this.fontSize);
this.fontMet = this.getFontMetrics(this.$font);
if (this.molText != null) {
var w = this.fontMet.stringWidth(this.molText);
var xstart = Math.round((imgWidth - w) / 2.);
var ystart = imgHeight - this.fontSize;
og.setColor(java.awt.Color.black);
og.setFont(this.$font);
og.drawString(this.molText, xstart, ystart);
}}}, "java.awt.image.BufferedImage");
Clazz.defineMethod(c$, "drawTopMenu", 
function(g){
var og = this.topMenu.getGraphics();
var imgWidth = this.dimension.width;
var imgHeight = this.sd * 2;
og.setColor(jme.JME.bgColor);
og.fillRect(0, 0, imgWidth, imgHeight);
og.setColor(jme.JME.bgColor.darker());
og.drawLine(imgWidth - 1, 0, imgWidth - 1, imgHeight - 1);
og.drawLine(0, imgHeight - 1, imgWidth - 1 - 2, imgHeight - 1);
og.setColor(jme.JME.brightColor);
og.drawLine(0, 0, imgWidth - 1, 0);
og.drawLine(12 * this.sd, 0, 12 * this.sd, imgHeight - 1);
for (var i = 1; i <= 12; i++) {
this.createSquare(og, i, 1);
this.createSquare(og, i, 2);
}
g.drawImage(this.topMenu, 0, 0, this);
}, "java.awt.Graphics");
Clazz.defineMethod(c$, "drawLeftMenu", 
function(g){
var og = this.leftMenu.getGraphics();
var imgWidth = this.sd;
var imgHeight = this.dimension.height - this.sd * 2;
og.setColor(jme.JME.bgColor);
og.fillRect(0, 0, imgWidth, imgHeight);
og.setColor(jme.JME.brightColor);
og.drawLine(0, 0, 0, imgHeight - 1);
og.drawLine(0, jme.JME.ACTIONA * this.sd, imgHeight - 1, jme.JME.ACTIONA * this.sd);
og.setColor(jme.JME.bgColor.darker());
og.drawLine(imgWidth - 1, 0, imgWidth - 1, imgHeight - 1 - this.sd);
og.drawLine(0, imgHeight - 1, imgWidth - 1, imgHeight - 1);
for (var i = 3; i <= jme.JME.ACTIONA + 2; i++) this.createSquare(og, 1, i);

g.drawImage(this.leftMenu, 0, this.sd * 2, this);
}, "java.awt.Graphics");
Clazz.defineMethod(c$, "drawInfo", 
function(g){
var og = this.infoArea.getGraphics();
var imgWidth = this.dimension.width - this.sd;
var imgHeight = this.sd;
og.setColor(jme.JME.bgColor);
og.fillRect(0, 0, imgWidth, imgHeight);
og.setColor(jme.JME.brightColor);
og.drawLine(0, 0, imgWidth - 1 - 2, 0);
og.setColor(jme.JME.bgColor.darker());
og.drawLine(0, imgHeight - 1, imgWidth - 1, imgHeight - 1);
og.drawLine(imgWidth - 1, 0, imgWidth - 1, imgHeight - 1);
og.setFont(this.fontSmall);
og.setColor(java.awt.Color.black);
if (this.infoText.startsWith("E")) og.setColor(java.awt.Color.red);
og.drawString(this.infoText, 10, 15);
g.drawImage(this.infoArea, this.sd, this.dimension.height - this.sd, this);
}, "java.awt.Graphics");
Clazz.defineMethod(c$, "menuAction", 
function(pressed){
if (pressed == 0) return;
var action_old = this.$action;
this.$action = pressed;
if (pressed <= 300) {
switch (pressed) {
case 102:
this.clear();
break;
case 110:
this.$action = action_old;
if (this.smol == null) {
this.actualMolecule = this.nmols;
this.clear();
} else if (this.afterClear) {
this.saved = ++this.nmols;
this.actualMolecule = this.nmols;
this.afterClear = false;
}if (this.smol == null) break;
this.mol =  new jme.JMEmol(this.smol);
this.mol.complete();
this.mols[this.saved] = this.mol;
break;
case 152:
var ssize = this.molStack.size();
this.$action = action_old;
if (ssize == 0) this.info("No molecules in molstack");
 else if (this.stackPointer == 0) this.info("Bottom of molstack reached");
 else this.getFromStack(-1);
break;
case 151:
ssize = this.molStack.size();
this.$action = action_old;
if (ssize == 0) this.info("No molecules in molstack");
 else if (this.stackPointer == ssize - 1) this.info("Top of molstack reached");
 else this.getFromStack(1);
break;
case 101:
if (this.smilesBox != null && this.smilesBox.isVisible()) {
this.smilesBoxPoint = this.smilesBox.getLocationOnScreen();
this.smilesBox.dispose();
this.smilesBox = null;
}this.smilesBox =  new jme.MultiBox(1, this);
this.$action = action_old;
break;
case 107:
if (this.queryBox != null && this.queryBox.isVisible()) {
this.point = this.queryBox.getLocationOnScreen();
this.queryBox.dispose();
this.queryBox = null;
}this.queryBox =  new jme.QueryBox(this);
break;
case 112:
if (this.aboutBox != null && this.aboutBox.isVisible()) {
this.aboutBoxPoint = this.aboutBox.getLocationOnScreen();
this.aboutBox.dispose();
this.aboutBox = null;
}this.aboutBox =  new jme.MultiBox(0, this);
this.$action = action_old;
break;
case 103:
this.newMolecule = true;
this.$action = action_old;
break;
case 105:
if (this.autonumber) {
if (this.mouseShift) {
this.mouseShift = false;
this.mol.numberAtoms();
this.$action = action_old;
}}this.currentMark = 1;
break;
case 111:
if (this.embedded) {
if (this.myFrame != null) this.myFrame.setVisible(false);
return;
}System.exit(0);
break;
case 109:
this.$action = action_old;
var part = this.mol.reactionPart();
if (part == 2) {
this.info("Copying the agent not possible !");
break;
}var center =  Clazz.newDoubleArray (4, 0);
this.mol.centerPoint(center);
this.mol =  new jme.JMEmol(this.mol);
var dx = Clazz.doubleToInt(Clazz.doubleToInt((this.dimension.width - this.sd) / 2) - center[0]);
for (var i = 1; i <= this.mol.natoms; i++) this.mol.x[i] += dx * 2;

this.mol.complete();
this.mols[++this.nmols] = this.mol;
this.actualMolecule = this.nmols;
break;
case 104:
if (this.mol.touchedAtom > 0) {
this.mol.save();
this.mol.deleteAtom(this.mol.touchedAtom);
this.mol.touchedAtom = 0;
} else if (this.mol.touchedBond > 0) {
this.mol.save();
this.mol.deleteBond(this.mol.touchedBond);
this.mol.touchedBond = 0;
}this.mol.valenceState();
break;
default:
break;
}
} else {
switch (pressed) {
case 301:
this.active_an = 3;
break;
case 401:
this.active_an = 4;
break;
case 501:
this.active_an = 5;
break;
case 701:
this.active_an = 9;
break;
case 801:
this.active_an = 10;
break;
case 901:
this.active_an = 11;
break;
case 1001:
this.active_an = 12;
break;
case 601:
this.active_an = 8;
break;
case 1101:
this.active_an = 7;
break;
case 1300:
this.active_an = 1;
break;
case 1201:
if (!this.webme) {
if (this.atomxBox != null && this.atomxBox.isVisible()) {
this.atomxBoxPoint = this.atomxBox.getLocationOnScreen();
this.atomxBox.dispose();
this.atomxBox = null;
}if (this.mol.touchedAtom == 0) this.atomxBox =  new jme.MultiBox(2, this);
}this.active_an = 18;
break;
case 1301:
this.active_an = 19;
break;
case 1302:
this.active_an = 20;
break;
case 1303:
this.active_an = 21;
break;
case 1304:
this.active_an = 22;
break;
}
if (this.mol.touchedAtom > 0) {
if (this.active_an != this.mol.an[this.mol.touchedAtom] && this.active_an != 18) {
this.mol.save();
this.mol.an[this.mol.touchedAtom] = this.active_an;
this.mol.q[this.mol.touchedAtom] = 0;
this.mol.nh[this.mol.touchedAtom] = 0;
}if (this.active_an == 18) {
var xx = this.atomicSymbol.getText();
this.mol.setAtom(this.mol.touchedAtom, xx);
}this.mol.valenceState();
}}this.repaint();
}, "~N");
Clazz.defineMethod(c$, "createSquare", 
function(g, xpos, ypos){
var square = ypos * 100 + xpos;
var xstart = (xpos - 1) * this.sd;
var ystart = (ypos - 1) * this.sd;
if (xpos == 1 && ypos > 2) ystart -= (2 * this.sd);
g.setColor(jme.JME.bgColor);
if (square == this.$action) g.fill3DRect(xstart + 1, ystart + 1, this.sd, this.sd, false);
 else g.fill3DRect(xstart, ystart, this.sd, this.sd, true);
if (square == 1301 && !this.rButton) return;
if (square == 111 && !this.application) return;
if (square == 107 && !this.query) return;
if (square == 201 && !this.stereo) return;
if (square == 103 && !this.multipart) return;
if (square == 105 && !(this.number || this.autonumber)) return;
if (square == 109 && !this.reaction) return;
var m = Clazz.doubleToInt(this.sd / 4);
if (ypos < 3) {
g.setColor(java.awt.Color.black);
switch (square) {
case 101:
if (!this.bwMode) {
g.setColor(java.awt.Color.yellow);
g.fillOval(xstart + 3, ystart + 3, this.sd - 6, this.sd - 6);
g.setColor(java.awt.Color.black);
}g.drawOval(xstart + 3, ystart + 3, this.sd - 6, this.sd - 6);
g.drawArc(xstart + 6, ystart + 6, this.sd - 12, this.sd - 12, -35, -110);
g.fillRect(xstart + 9, ystart + 9, 2, 4);
g.fillRect(xstart + this.sd - 10, ystart + 9, 2, 4);
if (Math.random() < 0.04) {
g.setColor(java.awt.Color.red);
g.fillRect(xstart + 10, ystart + 18, 4, 4);
}if (Math.random() > 0.96) {
g.setColor(java.awt.Color.yellow);
g.fillRect(xstart + this.sd - 10, ystart + 8, 2, 3);
}break;
case 111:
this.squareText(g, xstart, ystart, "END");
break;
case 107:
g.setColor(java.awt.Color.orange);
g.fillRect(xstart + 4, ystart + 4, this.sd - 8, this.sd - 8);
g.setColor(java.awt.Color.black);
g.drawRect(xstart + 4, ystart + 4, this.sd - 8, this.sd - 8);
g.drawArc(xstart + 6, ystart + 6, this.sd - 11, this.sd - 12, -35, -110);
g.fillRect(xstart + 9, ystart + 9, 2, 4);
g.fillRect(xstart + this.sd - 10, ystart + 9, 2, 4);
break;
case 108:
this.squareText(g, xstart, ystart, "+ /  ");
g.drawLine(xstart + 15, ystart + 13, xstart + 19, ystart + 13);
break;
case 110:
g.drawArc(xstart + 6, ystart + 7, this.sd - 12, this.sd - 14, 270, 270);
g.drawLine(xstart + 6, ystart + 13, xstart + 3, ystart + 10);
g.drawLine(xstart + 6, ystart + 13, xstart + 9, ystart + 10);
break;
case 109:
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2));
g.drawLine(xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - Clazz.doubleToInt(m * 3 / 2), ystart + Clazz.doubleToInt(this.sd / 2) + Clazz.doubleToInt(m / 2));
g.drawLine(xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - Clazz.doubleToInt(m * 3 / 2), ystart + Clazz.doubleToInt(this.sd / 2) - Clazz.doubleToInt(m / 2));
break;
case 102:
g.setColor(java.awt.Color.white);
g.fillRect(xstart + 3, ystart + 5, this.sd - 7, this.sd - 11);
g.setColor(java.awt.Color.black);
g.drawRect(xstart + 3, ystart + 5, this.sd - 7, this.sd - 11);
break;
case 103:
g.setColor(jme.JME.bgColor);
if (this.newMolecule) g.fill3DRect(xstart + 1, ystart + 1, this.sd, this.sd, false);
g.setColor(java.awt.Color.black);
this.squareText(g, xstart, ystart, "NEW");
break;
case 106:
g.setColor(java.awt.Color.red);
g.drawLine(xstart + 7, ystart + 7, xstart + this.sd - 7, ystart + this.sd - 7);
g.drawLine(xstart + 8, ystart + 7, xstart + this.sd - 6, ystart + this.sd - 7);
g.drawLine(xstart + 7, ystart + this.sd - 7, xstart + this.sd - 7, ystart + 7);
g.drawLine(xstart + 8, ystart + this.sd - 7, xstart + this.sd - 6, ystart + 7);
g.setColor(java.awt.Color.black);
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + 12, ystart + Clazz.doubleToInt(this.sd / 2));
this.squareText(g, xstart + 6, ystart, "R");
break;
case 104:
g.setColor(java.awt.Color.red);
g.drawLine(xstart + 7, ystart + 7, xstart + this.sd - 7, ystart + this.sd - 7);
g.drawLine(xstart + 8, ystart + 7, xstart + this.sd - 6, ystart + this.sd - 7);
g.drawLine(xstart + 7, ystart + this.sd - 7, xstart + this.sd - 7, ystart + 7);
g.drawLine(xstart + 8, ystart + this.sd - 7, xstart + this.sd - 6, ystart + 7);
g.setColor(java.awt.Color.black);
break;
case 105:
if (this.star) {
g.setColor(java.awt.Color.cyan);
g.drawLine(xstart + 11, ystart + 5, xstart + 9, ystart + 9);
g.drawLine(xstart + 9, ystart + 9, xstart + 4, ystart + 9);
g.drawLine(xstart + 4, ystart + 9, xstart + 8, ystart + 12);
g.drawLine(xstart + 8, ystart + 12, xstart + 6, ystart + 18);
g.drawLine(xstart + 6, ystart + 18, xstart + 11, ystart + 15);
g.drawLine(xstart + 12, ystart + 5, xstart + 14, ystart + 9);
g.drawLine(xstart + 14, ystart + 9, xstart + 19, ystart + 9);
g.drawLine(xstart + 19, ystart + 9, xstart + 15, ystart + 12);
g.drawLine(xstart + 15, ystart + 12, xstart + 17, ystart + 18);
g.drawLine(xstart + 17, ystart + 18, xstart + 12, ystart + 15);
g.setColor(java.awt.Color.black);
} else this.squareText(g, xstart, ystart, "123");
break;
case 112:
g.setColor(java.awt.Color.blue);
g.fillRect(xstart + 4, ystart + 4, this.sd - 8, this.sd - 8);
g.setColor(java.awt.Color.black);
g.drawRect(xstart + 4, ystart + 4, this.sd - 8, this.sd - 8);
this.squareTextBold(g, xstart + 1, ystart - 1, java.awt.Color.white, "i");
break;
case 201:
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) + 2);
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) - 2);
g.drawLine(xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) + 2, xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) - 2);
break;
case 202:
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2));
break;
case 203:
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2) - 2, xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) - 2);
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2) + 2, xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) + 2);
break;
case 204:
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2), xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2));
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2) - 2, xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) - 2);
g.drawLine(xstart + m, ystart + Clazz.doubleToInt(this.sd / 2) + 2, xstart + this.sd - m, ystart + Clazz.doubleToInt(this.sd / 2) + 2);
break;
case 205:
g.drawLine(xstart + Clazz.doubleToInt(m / 2), ystart + m * 2 + Clazz.doubleToInt(m / 3), xstart + Clazz.doubleToInt(m / 2) * 3, ystart + m * 2 - Clazz.doubleToInt(m / 3));
g.drawLine(xstart + Clazz.doubleToInt(m / 2) * 3, ystart + m * 2 - Clazz.doubleToInt(m / 3), xstart + Clazz.doubleToInt(m / 2) * 5, ystart + m * 2 + Clazz.doubleToInt(m / 3));
g.drawLine(xstart + Clazz.doubleToInt(m / 2) * 5, ystart + m * 2 + Clazz.doubleToInt(m / 3), xstart + Clazz.doubleToInt(m / 2) * 7, ystart + m * 2 - Clazz.doubleToInt(m / 3));
break;
case 206:
this.drawRingIcon(g, xstart, ystart + 2, 3);
break;
case 207:
this.drawRingIcon(g, xstart, ystart, 4);
break;
case 208:
this.drawRingIcon(g, xstart, ystart, 5);
break;
case 209:
this.drawRingIcon(g, xstart, ystart, 1);
break;
case 210:
this.drawRingIcon(g, xstart, ystart, 6);
break;
case 211:
this.drawRingIcon(g, xstart, ystart, 7);
break;
case 212:
this.drawRingIcon(g, xstart, ystart, 8);
break;
}
} else {
var dan = 3;
if (square == 301) dan = 3;
 else if (square == 401) dan = 4;
 else if (square == 501) dan = 5;
 else if (square == 601) dan = 8;
 else if (square == 701) dan = 9;
 else if (square == 801) dan = 10;
 else if (square == 901) dan = 11;
 else if (square == 1001) dan = 12;
 else if (square == 1101) dan = 7;
 else if (square == 1201) dan = 18;
 else if (square == 1301) dan = 19;
this.squareTextBold(g, xstart, ystart, jme.JME.color[dan], jme.JME.zlabel[dan]);
}}, "java.awt.Graphics,~N,~N");
Clazz.defineMethod(c$, "squareText", 
function(g, xstart, ystart, text){
g.setFont(this.fontSmall);
var hSmall = this.fontSmallMet.getAscent();
var w = this.fontSmallMet.stringWidth(text);
g.drawString(text, xstart + Clazz.doubleToInt((this.sd - w) / 2), ystart + Clazz.doubleToInt((this.sd - hSmall) / 2) + hSmall);
}, "java.awt.Graphics,~N,~N,~S");
Clazz.defineMethod(c$, "squareTextBold", 
function(g, xstart, ystart, col, text){
var h = this.fontBoldMet.getAscent();
var w = this.fontBoldMet.stringWidth(text);
g.setFont(this.fontBold);
g.setColor(col);
if (this.bwMode) g.setColor(java.awt.Color.black);
g.drawString(text, xstart + Clazz.doubleToInt((this.sd - w) / 2), ystart + Clazz.doubleToInt((this.sd - h) / 2) + h);
}, "java.awt.Graphics,~N,~N,java.awt.Color,~S");
Clazz.defineMethod(c$, "drawRingIcon", 
function(g, xstart, ystart, n){
var m = Clazz.doubleToInt(this.sd / 4);
var ph = false;
var xp =  Clazz.newIntArray (9, 0);
var yp =  Clazz.newIntArray (9, 0);
var xcenter = xstart + Clazz.doubleToInt(this.sd / 2);
var ycenter = ystart + Clazz.doubleToInt(this.sd / 2);
var rc = Clazz.doubleToInt(this.sd / 2) - Clazz.doubleToInt(m / 2);
if (n == 1) {
n = 6;
ph = true;
}for (var i = 0; i <= n; i++) {
var uhol = 6.283185307179586 / n * (i - .5);
xp[i] = Clazz.doubleToInt(xcenter + rc * Math.sin(uhol));
yp[i] = Clazz.doubleToInt(ycenter + rc * Math.cos(uhol));
}
g.drawPolygon(xp, yp, n + 1);
if (ph) {
for (var i = 0; i <= n; i++) {
var uhol = 6.283185307179586 / n * (i - .5);
xp[i] = Clazz.doubleToInt(xcenter + (rc - 3) * Math.sin(uhol));
yp[i] = Clazz.doubleToInt(ycenter + (rc - 3) * Math.cos(uhol));
}
g.drawLine(xp[0], yp[0], xp[1], yp[1]);
g.drawLine(xp[2], yp[2], xp[3], yp[3]);
g.drawLine(xp[4], yp[4], xp[5], yp[5]);
}}, "java.awt.Graphics,~N,~N,~N");
Clazz.defineMethod(c$, "info", 
function(text){
this.infoText = text;
}, "~S");
Clazz.defineMethod(c$, "mouseDown", 
function(e, x, y){
var status = true;
if (this.depict) return true;
this.xold = x - this.sd;
this.yold = y - 2 * this.sd;
this.info("");
this.mouseShift = e.isShiftDown();
this.movePossible = false;
if (x < this.sd || y < this.sd * 2) {
var xbutton = 0;
for (var i = 1; i <= 12; i++) if (x < i * this.sd) {
xbutton = i;
break;
}
var ybutton = 0;
for (var i = 1; i <= jme.JME.ACTIONA + 2; i++) if (y < i * this.sd) {
ybutton = i;
break;
}
if (xbutton == 0 || ybutton == 0) return true;
var action = ybutton * 100 + xbutton;
if (!this.application && action == 111) return true;
if (!this.query && action == 107) return true;
if (!this.stereo && action == 201) return true;
if (!this.multipart && action == 103) return true;
if (!(this.number || this.autonumber) && action == 105) return true;
if (!this.reaction && action == 109) return true;
this.menuAction(action);
} else if (y > this.dimension.height - this.sd - 1) {
return true;
} else {
this.movePossible = true;
x -= this.sd;
y -= 2 * this.sd;
if (this.doAction()) {
return false;
}if (this.nmols == 0 || this.newMolecule == true) {
if (this.$action <= 201) return true;
this.doNewMoleculeAction(x, y);
status = false;
}this.mol.valenceState();
this.repaint();
}return status;
}, "java.awt.event.MouseEvent,~N,~N");
Clazz.defineMethod(c$, "doAction", 
function(){
if (this.mol.touchedAtom > 0) {
this.doMouseAtomAction();
} else if (this.mol.touchedBond > 0) {
this.doMouseBondAction();
} else {
return false;
}this.mol.valenceState();
this.repaint();
return true;
});
Clazz.defineMethod(c$, "doNewMoleculeAction", 
function(x, y){
this.nmols++;
this.actualMolecule = this.nmols;
this.mols[this.nmols] =  new jme.JMEmol(this);
this.mol = this.mols[this.nmols];
this.newMolecule = false;
this.smol = null;
if (this.$action >= 202 && this.$action <= 204 || this.$action == 205) {
this.mol.createAtom();
this.mol.nbonds = 0;
this.mol.nv[1] = 0;
this.mol.x[1] = x;
this.mol.y[1] = y;
this.mol.touchedAtom = 1;
this.mol.touched_org = 1;
this.lastAction = 1;
this.mol.addBond();
if (this.$action == 205) {
this.mol.x[2] = x + 21.65;
this.mol.y[2] = y - 12.5;
this.mol.chain[0] = 1;
this.mol.chain[1] = 2;
this.mol.nchain = 1;
}} else if (this.$action >= 206 && this.$action <= 229) {
this.mol.xorg = x;
this.mol.yorg = y;
this.lastAction = 2;
this.mol.addRing();
} else if (this.$action > 300) {
this.mol.createAtom();
this.mol.an[1] = this.active_an;
this.mol.nbonds = 0;
this.mol.nv[1] = 0;
this.mol.x[1] = x;
this.mol.y[1] = y;
this.mol.touchedAtom = 1;
if (this.active_an == 18) {
var xx = this.atomicSymbol.getText();
if (xx.length < 1) xx = "X";
this.mol.setAtom(1, xx);
}} else if (this.$action == 230) {
this.readMolecule(this.template);
} else if (this.$action >= 233 && this.$action < 260) {
this.mol.createAtom();
this.mol.nbonds = 0;
this.mol.nv[1] = 0;
this.mol.x[1] = x;
this.mol.y[1] = y;
this.mol.touchedAtom = 1;
this.mol.addGroup(true);
} else {
System.err.println("error -report fall through bug !");
}}, "~N,~N");
Clazz.defineMethod(c$, "doMouseBondAction", 
function(){
if (this.$action == 104) {
this.mol.save();
this.mol.deleteBond(this.mol.touchedBond);
this.mol.touchedBond = 0;
} else if (this.$action == 106) {
this.mol.save();
this.mol.deleteGroup(this.mol.touchedBond);
this.mol.touchedBond = 0;
} else if (this.$action == 201) {
this.mol.stereoBond(this.mol.touchedBond);
} else if (this.$action == 202 || this.$action == 205) {
if (this.mol.nasv[this.mol.touchedBond] == 1 && this.mol.stereob[this.mol.touchedBond] == 0) this.mol.nasv[this.mol.touchedBond] = 2;
 else this.mol.nasv[this.mol.touchedBond] = 1;
this.mol.stereob[this.mol.touchedBond] = 0;
} else if (this.$action == 203) {
this.mol.nasv[this.mol.touchedBond] = 2;
this.mol.stereob[this.mol.touchedBond] = 0;
} else if (this.$action == 204) {
this.mol.nasv[this.mol.touchedBond] = 3;
this.mol.stereob[this.mol.touchedBond] = 0;
} else if (this.$action >= 206 && this.$action <= 229) {
this.mol.save();
this.lastAction = 2;
this.mol.addRing();
} else if (this.$action == 107) {
if (!this.queryBox.isBondQuery()) return;
var bondQuery = this.queryBox.getSmarts();
this.mol.nasv[this.mol.touchedBond] = 9;
this.mol.btag[this.mol.touchedBond] = bondQuery;
} else if (this.$action == 105) {
this.info("Only atoms may be marked !");
}});
Clazz.defineMethod(c$, "doMouseAtomAction", 
function(){
if (this.$action == 104) {
this.mol.save();
this.mol.deleteAtom(this.mol.touchedAtom);
this.mol.touchedAtom = 0;
} else if (this.$action == 106) {
return true;
} else if (this.$action == 108) {
this.mol.changeCharge(this.mol.touchedAtom, 0);
} else if (this.$action == 157) {
this.mol.changeCharge(this.mol.touchedAtom, 1);
} else if (this.$action == 158) {
this.mol.changeCharge(this.mol.touchedAtom, -1);
} else if (this.$action == 202 || this.$action == 203 || this.$action == 204 || this.$action == 201 || this.$action == 205) {
this.mol.save();
this.lastAction = 1;
this.mol.addBond();
this.mol.touched_org = this.mol.touchedAtom;
if (this.$action == 205) {
this.mol.nchain = 1;
this.mol.chain[1] = this.mol.natoms;
this.mol.chain[0] = this.mol.touchedAtom;
this.mol.touchedBond = 0;
}} else if (this.$action >= 206 && this.$action <= 229) {
this.mol.save();
this.lastAction = 2;
this.mol.addRing();
} else if (this.$action == 230) {
this.mol.save();
this.lastAction = 3;
} else if (this.$action >= 233 && this.$action < 260) {
this.mol.save();
this.mol.addGroup(false);
this.lastAction = 3;
} else if (this.$action == 107) {
if (this.queryBox.isBondQuery()) return true;
this.mol.setAtom(this.mol.touchedAtom, this.queryBox.getSmarts());
} else if (this.$action == 105) {
this.mol.mark();
} else if (this.$action > 300) {
if (this.active_an != this.mol.an[this.mol.touchedAtom] || this.active_an == 18) {
this.mol.save();
this.mol.an[this.mol.touchedAtom] = this.active_an;
this.mol.q[this.mol.touchedAtom] = 0;
this.mol.nh[this.mol.touchedAtom] = 0;
if (this.active_an == 18) {
var xx = this.atomicSymbol.getText();
if (xx.length < 1) xx = "X";
this.mol.setAtom(this.mol.touchedAtom, xx);
}}}return false;
});
Clazz.defineMethod(c$, "mouseUp", 
function(e, x, y){
if (this.depict) return true;
if (this.lastAction == 1) {
if (this.$action == 205) this.mol.checkChain();
 else this.mol.checkBond();
this.mol.findBondCenters();
} else if (this.lastAction == 5) {
this.mol.findBondCenters();
}if (this.lastAction > 0) {
this.mol.valenceState();
this.mol.cleanPolarBonds();
this.repaint();
this.lastAction = 0;
this.afterClear = false;
}return true;
}, "java.awt.event.MouseEvent,~N,~N");
Clazz.defineMethod(c$, "mouseDrag", 
function(e, x, y){
if (this.depict) return true;
if (!this.movePossible) return true;
x -= this.sd;
y -= this.sd * 2;
var movex = (x - this.xold);
var movey = (y - this.yold);
if (this.lastAction == 2 || this.lastAction == 3 || this.lastAction == 9) return true;
 else if (this.lastAction == 1) {
this.mol.rubberBanding(x, y);
} else if (e.isShiftDown() || e.isMetaDown()) {
this.mol.rotate(movex);
this.lastAction = 5;
} else if (this.mol.touchedAtom == 0 && this.mol.touchedBond == 0) {
this.mol.move(movex, movey);
this.lastAction = 5;
}this.repaint();
this.xold = x;
this.yold = y;
return true;
}, "java.awt.event.MouseEvent,~N,~N");
Clazz.defineMethod(c$, "mouseMove", 
function(e, x, y){
if (this.depict) return true;
x -= this.sd;
y -= this.sd * 2;
this.myFrame.requestFocusInWindow();
var repaintFlag = false;
var newActual = 0;
touchLoop : for (var m = 1; m <= this.nmols; m++) {
var a = 0;
var b = 0;
a = this.mols[m].testAtomTouch(x, y);
if (a == 0) b = this.mols[m].testBondTouch(x, y);
if (a > 0) {
this.mols[m].touchedAtom = a;
this.mols[m].touchedBond = 0;
newActual = m;
repaintFlag = true;
break touchLoop;
} else if (b > 0) {
this.mols[m].touchedAtom = 0;
this.mols[m].touchedBond = b;
newActual = m;
repaintFlag = true;
break touchLoop;
} else {
if (this.mols[m].touchedAtom > 0 || this.mols[m].touchedBond > 0) {
this.mols[m].touchedAtom = 0;
this.mols[m].touchedBond = 0;
repaintFlag = true;
}}}
if (repaintFlag) {
for (var m = this.actualMolecule + 1; m <= this.nmols; m++) {
this.mols[m].touchedAtom = 0;
this.mols[m].touchedBond = 0;
}
this.repaint();
}if (newActual != 0 && newActual != this.actualMolecule) {
this.actualMolecule = newActual;
this.mol = this.mols[this.actualMolecule];
}return true;
}, "java.awt.event.MouseEvent,~N,~N");
Clazz.defineMethod(c$, "keyDown", 
function(e, key){
if (this.depict) return true;
this.info("");
var pressed = 0;
var alt = e.getModifiers() == 8;
var ctrl = e.getModifiers() == 2;
var c = String.fromCharCode(key);
switch ((c).charCodeAt(0)) {
case 67:
pressed = 301;
break;
case 78:
pressed = 401;
break;
case 79:
pressed = 501;
break;
case 83:
pressed = 601;
break;
case 80:
pressed = 1101;
break;
case 70:
pressed = 701;
break;
case 76:
pressed = 801;
break;
case 66:
pressed = 901;
break;
case 73:
pressed = 1001;
break;
case 88:
this.info(this.atomicSymbol.getText());
pressed = 1201;
this.active_an = 18;
break;
case 72:
this.info("H");
pressed = 1300;
break;
case 82:
this.info("R");
pressed = 1301;
break;
case 84:
if (this.$action == 701) {
pressed = 236;
this.info("-CF3");
} else if (this.$action == 801) {
pressed = 237;
this.info("-CCl3");
} else {
pressed = 233;
this.info("-tBu");
}break;
case 89:
pressed = 234;
this.info("-NO2");
break;
case 90:
if (ctrl) {
pressed = 110;
this.info("");
} else {
pressed = 239;
this.info("-SO3H");
}break;
case 65:
pressed = 235;
this.info("-COOH");
break;
case 69:
pressed = 238;
this.info("-C#CH");
break;
case 85:
pressed = 110;
break;
case 81:
pressed = 242;
this.info("-C#N");
break;
case 27:
pressed = 202;
break;
case 45:
if (this.$action == 701) {
pressed = 254;
this.info("-F");
} else if (this.$action == 801) {
pressed = 255;
this.info("-Cl");
} else if (this.$action == 901) {
pressed = 256;
this.info("-Br");
} else if (this.$action == 1001) {
pressed = 257;
this.info("-I");
} else if (this.$action == 501) {
pressed = 259;
this.info("-OH");
} else if (this.$action == 401) {
pressed = 258;
this.info("-NH2");
} else pressed = 202;
break;
case 61:
if (this.$action == 501) {
pressed = 250;
this.info("=O");
} else pressed = 203;
break;
case 35:
pressed = 204;
break;
case 48:
if (this.$action == 105) this.updateMark(0);
 else {
if (!alt) {
pressed = 221;
this.info("-Furyl");
} else {
pressed = 223;
this.info("-3-Furyl");
}}break;
case 49:
if (this.$action == 105) this.updateMark(1);
 else if (this.$action == 1301) {
this.info("-R1");
pressed = 1302;
} else {
var action_old = this.$action;
this.menuAction(202);
this.doAction();
this.$action = action_old;
return true;
}break;
case 50:
if (this.$action == 105) {
this.updateMark(2);
} else if (this.$action == 1301) {
this.info("-R2");
pressed = 1303;
} else {
var action_old = this.$action;
this.menuAction(203);
this.doAction();
this.$action = action_old;
return true;
}break;
case 51:
if (this.$action == 105) {
this.updateMark(3);
} else if (this.$action == 1301) {
this.info("-R3");
pressed = 1304;
} else {
var action_old = this.$action;
this.menuAction(204);
this.doAction();
this.$action = action_old;
return true;
}break;
case 52:
if (this.$action == 105) this.updateMark(4);
 else pressed = 207;
break;
case 53:
if (this.$action == 105) this.updateMark(5);
 else pressed = 208;
break;
case 54:
if (this.$action == 105) this.updateMark(6);
 else pressed = 210;
break;
case 55:
if (this.$action == 105) this.updateMark(7);
 else pressed = 211;
break;
case 56:
if (this.$action == 105) this.updateMark(8);
 else pressed = 212;
break;
case 57:
if (this.$action == 105) this.updateMark(9);
 else {
this.info("9 ring");
pressed = 229;
}break;
case 100:
case 68:
case 8:
case 127:
pressed = 104;
break;
case 32:
pressed = 205;
break;
case 1002:
pressed = 151;
break;
case 1003:
pressed = 152;
break;
}
this.menuAction(pressed);
return true;
}, "java.awt.event.KeyEvent,~N");
Clazz.defineMethod(c$, "updateMark", 
function(n){
if (this.autonumber) {
if (n == 0) {
this.currentMark = -1;
this.info("click marked atom to delete mark");
this.repaint();
}return;
}if (this.markUsed) this.currentMark = n;
 else {
if (this.currentMark > -1 && this.currentMark < 10) this.currentMark = this.currentMark * 10 + n;
 else this.currentMark = n;
}this.markUsed = false;
if (this.currentMark == 0) {
this.currentMark = -1;
this.info("click marked atom to delete mark");
} else this.info(this.currentMark + " ");
this.repaint();
}, "~N");
Clazz.overrideMethod(c$, "mouseDragged", 
function(e){
this.mouseDrag(e, e.getX(), e.getY());
}, "java.awt.event.MouseEvent");
Clazz.overrideMethod(c$, "mouseMoved", 
function(e){
this.mouseMove(e, e.getX(), e.getY());
}, "java.awt.event.MouseEvent");
Clazz.overrideMethod(c$, "keyTyped", 
function(e){
}, "java.awt.event.KeyEvent");
Clazz.overrideMethod(c$, "keyPressed", 
function(e){
this.keyDown(e, e.getKeyCode());
}, "java.awt.event.KeyEvent");
Clazz.overrideMethod(c$, "keyReleased", 
function(e){
}, "java.awt.event.KeyEvent");
Clazz.overrideMethod(c$, "mouseClicked", 
function(e){
}, "java.awt.event.MouseEvent");
Clazz.overrideMethod(c$, "mousePressed", 
function(e){
this.mouseDown(e, e.getX(), e.getY());
}, "java.awt.event.MouseEvent");
Clazz.overrideMethod(c$, "mouseReleased", 
function(e){
this.mouseUp(e, e.getX(), e.getY());
}, "java.awt.event.MouseEvent");
Clazz.overrideMethod(c$, "mouseEntered", 
function(e){
}, "java.awt.event.MouseEvent");
Clazz.overrideMethod(c$, "mouseExited", 
function(e){
}, "java.awt.event.MouseEvent");
c$.bgColor = java.awt.Color.lightGray;
c$.brightColor = jme.JME.bgColor.brighter();
c$.color =  new Array(23);
c$.zlabel =  new Array(23);
c$.ACTIONA = 10;
var c$ = Clazz.decorateAsClass(function(){
this.smilesText = null;
this.jme = null;
Clazz.instantialize(this, arguments);}, jme, "MultiBox", javax.swing.JFrame, java.awt.event.KeyListener);
Clazz.makeConstructor(c$, 
function(box, jme){
Clazz.superConstructor(this, jme.MultiBox);
this.jme = jme;
this.setFont(jme.fontSmall);
this.setBackground(jme.JME.bgColor);
this.setResizable(false);
this.addKeyListener(this);
if (box == 1) this.createSmilesBox(jme.Smiles());
 else if (box == 2) this.createAtomxBox();
 else this.createAboutBox();
this.pack();
this.setVisible(true);
}, "~N,jme.JME");
Clazz.defineMethod(c$, "createAboutBox", 
function(){
this.setTitle("about JSME");
this.setLayout( new java.awt.GridLayout(0, 1, 0, 0));
this.setFont(this.jme.fontSmall);
this.setBackground(jme.JME.bgColor);
this.add( new javax.swing.JLabel("JSME Molecular Editor v2023.01", 0));
this.add( new javax.swing.JLabel("Peter Ertl, Bruno BienFait. and Robert Hanson", 0));
var p =  new javax.swing.JPanel();
var b =  new javax.swing.JButton("Close");
b.addActionListener(((Clazz.isClassDefined("jme.MultiBox$1") ? 0 : jme.MultiBox.$MultiBox$1$ ()), Clazz.innerTypeInstance(jme.MultiBox$1, this, null)));
p.add(b);
this.add(p);
this.setLocation(this.jme.aboutBoxPoint);
});
Clazz.defineMethod(c$, "createSmilesBox", 
function(smiles){
this.setTitle("SMILES");
this.setLayout( new java.awt.BorderLayout(2, 0));
this.smilesText =  new javax.swing.JTextField(smiles + "     ");
if (!this.jme.runsmi) this.smilesText.setEditable(false);
this.add("Center", this.smilesText);
var p =  new javax.swing.JPanel();
var b =  new javax.swing.JButton("Close");
b.addActionListener(((Clazz.isClassDefined("jme.MultiBox$2") ? 0 : jme.MultiBox.$MultiBox$2$ ()), Clazz.innerTypeInstance(jme.MultiBox$2, this, null)));
p.add(b);
if (this.jme.runsmi) {
b =  new javax.swing.JButton("Submit");
p.add(b);
}this.add("South", p);
this.smilesText.setText(this.smilesText.getText().trim());
this.setResizable(true);
this.setLocation(this.jme.smilesBoxPoint);
}, "~S");
Clazz.defineMethod(c$, "setSmiles", 
function(smiles){
var d = this.getSize();
var l = this.jme.fontSmallMet.stringWidth(smiles) + 30;
if (l < 150) l = 150;
this.setSize(l, d.height);
this.validate();
this.smilesText.setText(smiles);
}, "~S");
Clazz.defineMethod(c$, "createAtomxBox", 
function(){
this.setTitle("nonstandard atom");
this.setLayout( new java.awt.BorderLayout(2, 0));
var p =  new javax.swing.JPanel();
p.add( new javax.swing.JLabel("atomic SMILES", 0));
this.add("North", p);
var as = "H";
if (this.jme.atomicSymbol != null) as = this.jme.atomicSymbol.getText();
this.jme.atomicSymbol =  new javax.swing.JTextField(as, 8);
this.add("Center", this.jme.atomicSymbol);
p =  new javax.swing.JPanel();
var b =  new javax.swing.JButton("Close ");
b.addActionListener(((Clazz.isClassDefined("jme.MultiBox$3") ? 0 : jme.MultiBox.$MultiBox$3$ ()), Clazz.innerTypeInstance(jme.MultiBox$3, this, null)));
p.add(b);
this.add("South", p);
this.setLocation(this.jme.atomxBoxPoint);
});
Clazz.defineMethod(c$, "keyDown", 
function(e, key){
if (this.jme.atomicSymbol == null) return false;
if (this.jme.$action != 1201) {
this.jme.$action = 1201;
this.jme.active_an = 18;
}return false;
}, "java.awt.event.KeyEvent,~N");
Clazz.overrideMethod(c$, "keyTyped", 
function(e){
}, "java.awt.event.KeyEvent");
Clazz.overrideMethod(c$, "keyPressed", 
function(e){
this.keyDown(e, e.getKeyCode());
}, "java.awt.event.KeyEvent");
Clazz.overrideMethod(c$, "keyReleased", 
function(e){
}, "java.awt.event.KeyEvent");
c$.$MultiBox$1$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(jme, "MultiBox$1", null, java.awt.event.ActionListener);
Clazz.overrideMethod(c$, "actionPerformed", 
function(e){
this.b$["jme.MultiBox"].jme.aboutBoxPoint = this.b$["jme.MultiBox"].jme.aboutBox.getLocationOnScreen();
this.b$["jme.MultiBox"].jme.aboutBox.setVisible(false);
}, "java.awt.event.ActionEvent");
/*eoif5*/})();
};
c$.$MultiBox$2$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(jme, "MultiBox$2", null, java.awt.event.ActionListener);
Clazz.overrideMethod(c$, "actionPerformed", 
function(e){
this.b$["jme.MultiBox"].jme.smilesBoxPoint = this.b$["jme.MultiBox"].jme.smilesBox.getLocationOnScreen();
this.b$["jme.MultiBox"].jme.smilesBox.setVisible(false);
}, "java.awt.event.ActionEvent");
/*eoif5*/})();
};
c$.$MultiBox$3$=function(){
/*if5*/;(function(){
var c$ = Clazz.declareAnonymous(jme, "MultiBox$3", null, java.awt.event.ActionListener);
Clazz.overrideMethod(c$, "actionPerformed", 
function(e){
this.b$["jme.MultiBox"].jme.atomxBoxPoint = this.b$["jme.MultiBox"].jme.atomxBox.getLocationOnScreen();
this.b$["jme.MultiBox"].jme.atomxBox.setVisible(false);
}, "java.awt.event.ActionEvent");
/*eoif5*/})();
};
var c$ = Clazz.decorateAsClass(function(){
this.text = null;
this.bgc = null;
this.$isBondQuery = false;
this.jme = null;
Clazz.instantialize(this, arguments);}, jme, "QueryBox", javax.swing.JFrame);
Clazz.prepareFields (c$, function(){
this.bgc = jme.JME.bgColor;
});
Clazz.makeConstructor(c$, 
function(jme){
Clazz.superConstructor(this, jme.QueryBox, ["Atom/Bond Query"]);
this.jme = jme;
this.setLayout( new java.awt.GridLayout(0, 1));
this.setFont(jme.fontSmall);
this.setBackground(this.bgc);
var p1 =  new javax.swing.JPanel();
p1.setLayout( new java.awt.FlowLayout(0, 3, 1));
p1.add( new javax.swing.JLabel("Atom type :"));
var first = true;
if (first) {
jme.any =  new javax.swing.JButton("Any");
jme.anyec =  new javax.swing.JButton("Any except C");
jme.halogen =  new javax.swing.JButton("Halogen");
}p1.add(jme.any);
p1.add(jme.anyec);
p1.add(jme.halogen);
this.add(p1);
var p2 =  new javax.swing.JPanel();
p2.setLayout( new java.awt.FlowLayout(0, 3, 1));
p2.add( new javax.swing.JLabel("Or select one or more from the list :", 2));
this.add(p2);
var p3 =  new javax.swing.JPanel();
p3.setLayout( new java.awt.FlowLayout(0, 3, 1));
if (first) {
jme.c =  new javax.swing.JButton("C");
jme.n =  new javax.swing.JButton("N");
jme.o =  new javax.swing.JButton("O");
jme.s =  new javax.swing.JButton("S");
jme.p =  new javax.swing.JButton("P");
jme.f =  new javax.swing.JButton("F");
jme.cl =  new javax.swing.JButton("Cl");
jme.br =  new javax.swing.JButton("Br");
jme.i =  new javax.swing.JButton("I");
}p3.add(jme.c);
p3.add(jme.n);
p3.add(jme.o);
p3.add(jme.s);
p3.add(jme.p);
p3.add(jme.f);
p3.add(jme.cl);
p3.add(jme.br);
p3.add(jme.i);
this.add(p3);
var p4 =  new javax.swing.JPanel();
p4.setLayout( new java.awt.FlowLayout(0, 3, 1));
if (first) {
jme.choiceh =  new javax.swing.JComboBox();
jme.choiceh.addItem("Any");
jme.choiceh.addItem("0");
jme.choiceh.addItem("1");
jme.choiceh.addItem("2");
jme.choiceh.addItem("3");
}p4.add( new javax.swing.JLabel("Number of hydrogens :  "));
p4.add(jme.choiceh);
this.add(p4);
var p5 =  new javax.swing.JPanel();
p5.setLayout( new java.awt.FlowLayout(0, 3, 1));
if (first) {
jme.choiced =  new javax.swing.JComboBox();
jme.choiced.addItem("Any");
jme.choiced.addItem("0");
jme.choiced.addItem("1");
jme.choiced.addItem("2");
jme.choiced.addItem("3");
jme.choiced.addItem("4");
jme.choiced.addItem("5");
jme.choiced.addItem("6");
}p5.add( new javax.swing.JLabel("Number of connections :", 2));
p5.add(jme.choiced);
p5.add( new javax.swing.JLabel(" (H's don't count.)", 2));
this.add(p5);
var p6 =  new javax.swing.JPanel();
p6.setLayout( new java.awt.FlowLayout(0, 3, 1));
p6.add( new javax.swing.JLabel("Atom is :"));
if (first) jme.aromatic =  new javax.swing.JButton("Aromatic");
p6.add(jme.aromatic);
if (first) jme.nonaromatic =  new javax.swing.JButton("Nonaromatic");
p6.add(jme.nonaromatic);
if (first) jme.ring =  new javax.swing.JButton("Ring");
p6.add(jme.ring);
if (first) jme.nonring =  new javax.swing.JButton("Nonring");
p6.add(jme.nonring);
this.add(p6);
var p9 =  new javax.swing.JPanel();
p9.setBackground(this.getBackground().darker());
p9.setLayout( new java.awt.FlowLayout(0, 3, 1));
p9.add( new javax.swing.JLabel("Bond is :"));
if (first) jme.anyBond =  new javax.swing.JButton("Any");
p9.add(jme.anyBond);
if (first) jme.aromaticBond =  new javax.swing.JButton("Aromatic");
p9.add(jme.aromaticBond);
if (first) jme.ringBond =  new javax.swing.JButton("Ring");
p9.add(jme.ringBond);
if (first) jme.nonringBond =  new javax.swing.JButton("Nonring");
p9.add(jme.nonringBond);
this.add(p9);
var p8 =  new javax.swing.JPanel();
p8.setLayout( new java.awt.FlowLayout(1, 3, 1));
if (first) this.text =  new javax.swing.JTextField("*", 20);
p8.add(this.text);
p8.add( new javax.swing.JButton("Reset"));
p8.add( new javax.swing.JButton("Close"));
this.add(p8);
this.setResizable(false);
if (first) {
this.resetAtomList();
this.resetAtomType();
this.resetBondType();
jme.aromatic.setBackground(this.bgc);
jme.nonaromatic.setBackground(this.bgc);
jme.ring.setBackground(this.bgc);
jme.nonring.setBackground(this.bgc);
jme.choiceh.setBackground(this.bgc);
jme.choiced.setBackground(this.bgc);
this.changeColor(jme.any);
}this.pack();
this.setLocation(jme.point);
this.setVisible(true);
}, "jme.JME");
Clazz.overrideMethod(c$, "action", 
function(e, arg){
if (arg.equals("Close")) {
this.jme.point = this.getLocationOnScreen();
this.setVisible(false);
} else if (arg.equals("Reset")) {
this.resetAll();
this.changeColor(this.jme.any);
this.doSmarts();
} else if (Clazz.instanceOf(e.target,"javax.swing.JButton")) {
this.resetBondType();
if (e.target === this.jme.any) {
this.resetAtomList();
this.resetAtomType();
} else if (e.target === this.jme.anyec) {
this.resetAtomList();
this.resetAtomType();
} else if (e.target === this.jme.halogen) {
this.resetAtomList();
this.resetAtomType();
} else if (e.target === this.jme.ring) {
this.jme.nonring.setBackground(this.bgc);
} else if (e.target === this.jme.nonring) {
this.jme.ring.setBackground(this.bgc);
this.jme.aromatic.setBackground(this.bgc);
} else if (e.target === this.jme.aromatic) {
this.jme.nonaromatic.setBackground(this.bgc);
this.jme.nonring.setBackground(this.bgc);
} else if (e.target === this.jme.nonaromatic) {
this.jme.aromatic.setBackground(this.bgc);
} else if (e.target === this.jme.anyBond || e.target === this.jme.aromaticBond || e.target === this.jme.ringBond || e.target === this.jme.nonringBond) {
this.resetAll();
this.$isBondQuery = true;
} else {
this.resetAtomType();
}this.changeColor((e.target));
this.doSmarts();
} else if (Clazz.instanceOf(e.target,"javax.swing.JComboBox")) {
this.resetBondType();
var choice = (e.target);
if (choice.getSelectedIndex() == 0) choice.setBackground(this.bgc);
 else choice.setBackground(java.awt.Color.orange);
this.doSmarts();
}if (this.jme.$action != 107) {
this.jme.$action = 107;
this.jme.repaint();
}return true;
}, "java.awt.Event,~O");
Clazz.defineMethod(c$, "resetAll", 
function(){
this.resetAtomList();
this.resetAtomType();
this.jme.choiceh.setSelectedIndex(0);
this.jme.choiced.setSelectedIndex(0);
this.jme.aromatic.setBackground(this.bgc);
this.jme.nonaromatic.setBackground(this.bgc);
this.jme.ring.setBackground(this.bgc);
this.jme.nonring.setBackground(this.bgc);
this.jme.choiceh.setBackground(this.bgc);
this.jme.choiced.setBackground(this.bgc);
this.resetBondType();
});
Clazz.defineMethod(c$, "resetAtomList", 
function(){
this.jme.c.setBackground(this.bgc);
this.jme.n.setBackground(this.bgc);
this.jme.o.setBackground(this.bgc);
this.jme.s.setBackground(this.bgc);
this.jme.p.setBackground(this.bgc);
this.jme.f.setBackground(this.bgc);
this.jme.cl.setBackground(this.bgc);
this.jme.br.setBackground(this.bgc);
this.jme.i.setBackground(this.bgc);
});
Clazz.defineMethod(c$, "resetAtomType", 
function(){
this.jme.any.setBackground(this.bgc);
this.jme.anyec.setBackground(this.bgc);
this.jme.halogen.setBackground(this.bgc);
});
Clazz.defineMethod(c$, "resetBondType", 
function(){
this.jme.anyBond.setBackground(this.bgc);
this.jme.aromaticBond.setBackground(this.bgc);
this.jme.ringBond.setBackground(this.bgc);
this.jme.nonringBond.setBackground(this.bgc);
this.$isBondQuery = false;
});
Clazz.defineMethod(c$, "changeColor", 
function(b){
if (b.getBackground() === this.bgc) b.setBackground(java.awt.Color.orange);
 else b.setBackground(this.bgc);
}, "javax.swing.JButton");
Clazz.defineMethod(c$, "doSmarts", 
function(){
var smarts = "";
var showaA = false;
if (this.jme.any.getBackground() !== this.bgc) {
smarts = "*";
showaA = true;
} else if (this.jme.anyec.getBackground() !== this.bgc) {
smarts = "!#6";
showaA = true;
} else if (this.jme.halogen.getBackground() !== this.bgc) {
this.jme.f.setBackground(java.awt.Color.orange);
this.jme.cl.setBackground(java.awt.Color.orange);
this.jme.br.setBackground(java.awt.Color.orange);
this.jme.i.setBackground(java.awt.Color.orange);
smarts = "F,Cl,Br,I";
} else {
var ar = this.jme.aromatic.getBackground() !== this.bgc;
var nar = this.jme.nonaromatic.getBackground() !== this.bgc;
if (this.jme.c.getBackground() !== this.bgc) {
if (ar) smarts += "c,";
 else if (nar) smarts += "C,";
 else smarts += "#6,";
}if (this.jme.n.getBackground() !== this.bgc) {
if (ar) smarts += "n,";
 else if (nar) smarts += "N,";
 else smarts += "#7,";
}if (this.jme.o.getBackground() !== this.bgc) {
if (ar) smarts += "o,";
 else if (nar) smarts += "O,";
 else smarts += "#8,";
}if (this.jme.s.getBackground() !== this.bgc) {
if (ar) smarts += "s,";
 else if (nar) smarts += "S,";
 else smarts += "#16,";
}if (this.jme.p.getBackground() !== this.bgc) {
if (ar) smarts += "p,";
 else if (nar) smarts += "P,";
 else smarts += "#15,";
}if (this.jme.f.getBackground() !== this.bgc) smarts += "F,";
if (this.jme.cl.getBackground() !== this.bgc) smarts += "Cl,";
if (this.jme.br.getBackground() !== this.bgc) smarts += "Br,";
if (this.jme.i.getBackground() !== this.bgc) smarts += "I,";
if (smarts.endsWith(",")) smarts = smarts.substring(0, smarts.length - 1);
if (smarts.length < 1 && !this.$isBondQuery) {
if (ar) smarts = "a";
 else if (nar) smarts = "A";
 else {
this.jme.any.setBackground(java.awt.Color.orange);
smarts = "*";
}}}var ap = "";
if (showaA && this.jme.aromatic.getBackground() !== this.bgc) ap += ";a";
if (showaA && this.jme.nonaromatic.getBackground() !== this.bgc) ap += ";A";
if (this.jme.ring.getBackground() !== this.bgc) ap += ";R";
if (this.jme.nonring.getBackground() !== this.bgc) ap += ";!R";
if (this.jme.any.getBackground() !== this.bgc && ap.length > 0) smarts = ap.substring(1, ap.length);
 else smarts += ap;
var nh = this.jme.choiceh.getSelectedIndex();
if (nh > 0) {
nh--;
smarts += ";H" + nh;
}var nd = this.jme.choiced.getSelectedIndex();
if (nd > 0) {
nd--;
smarts += ";D" + nd;
}if (this.jme.anyBond.getBackground() !== this.bgc) smarts = "~";
if (this.jme.aromaticBond.getBackground() !== this.bgc) smarts = ":";
if (this.jme.ringBond.getBackground() !== this.bgc) smarts = "@";
if (this.jme.nonringBond.getBackground() !== this.bgc) smarts = "!@";
this.text.setText(smarts);
});
Clazz.defineMethod(c$, "isBondQuery", 
function(){
return this.$isBondQuery;
});
Clazz.defineMethod(c$, "getSmarts", 
function(){
return this.text.getText();
});
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
