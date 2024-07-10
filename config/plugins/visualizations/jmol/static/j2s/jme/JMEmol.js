Clazz.declarePackage("jme");
Clazz.load(null, "jme.JMEmol", ["java.util.ArrayList", "$.Date", "$.Hashtable", "$.StringTokenizer", "JU.SB", "jme.AtomDisplayLabel", "$.JME", "$.JMEUtil", "J.api.JmolAdapter", "JV.PropertyManager"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.jme = null;
this.natoms = 0;
this.nbonds = 0;
this.an = null;
this.q = null;
this.x = null;
this.y = null;
this.v = null;
this.abg = null;
this.atag = null;
this.label = null;
this.nh = null;
this.nv = null;
this.va = null;
this.vb = null;
this.nasv = null;
this.stereob = null;
this.xb = null;
this.yb = null;
this.btag = null;
this.$mark = null;
this.chain = null;
this.nmarked = 0;
this.maxMark = 0;
this.doColoring = 0;
this.a = null;
this.btype = null;
this.touchedAtom = 0;
this.touchedBond = 0;
this.touched_org = 0;
this.xorg = 0;
this.yorg = 0;
this.linearAdding = false;
this.nchain = 0;
this.stopChain = false;
this.needRecentering = false;
this.minx = 0;
this.maxx = 0;
this.miny = 0;
this.maxy = 0;
Clazz.instantialize(this, arguments);}, jme, "JMEmol", null);
Clazz.prepareFields (c$, function(){
this.an =  Clazz.newIntArray (20, 0);
this.q =  Clazz.newIntArray (20, 0);
this.x =  Clazz.newDoubleArray (20, 0);
this.y =  Clazz.newDoubleArray (20, 0);
this.v =  Clazz.newIntArray (20, 7, 0);
this.abg =  Clazz.newIntArray (20, 0);
this.atag =  new Array(20);
this.label =  new Array(20);
this.nh =  Clazz.newIntArray (20, 0);
this.nv =  Clazz.newIntArray (20, 0);
this.va =  Clazz.newIntArray (20, 0);
this.vb =  Clazz.newIntArray (20, 0);
this.nasv =  Clazz.newIntArray (20, 0);
this.stereob =  Clazz.newIntArray (20, 0);
this.xb =  Clazz.newIntArray (20, 0);
this.yb =  Clazz.newIntArray (20, 0);
this.btag =  new Array(20);
this.$mark =  Clazz.newIntArray (10, 2, 0);
this.chain =  Clazz.newIntArray (101, 0);
});
Clazz.makeConstructor(c$, 
function(jme){
this.jme = jme;
}, "jme.JME");
Clazz.makeConstructor(c$, 
function(m){
this.jme = m.jme;
this.natoms = m.natoms;
this.nbonds = m.nbonds;
this.nmarked = m.nmarked;
this.an =  Clazz.newIntArray (this.natoms + 1, 0);
System.arraycopy(m.an, 0, this.an, 0, this.natoms + 1);
this.q =  Clazz.newIntArray (this.natoms + 1, 0);
System.arraycopy(m.q, 0, this.q, 0, this.natoms + 1);
this.nh =  Clazz.newIntArray (this.natoms + 1, 0);
System.arraycopy(m.nh, 0, this.nh, 0, this.natoms + 1);
this.abg =  Clazz.newIntArray (this.natoms + 1, 0);
System.arraycopy(m.abg, 0, this.abg, 0, this.natoms + 1);
this.atag =  new Array(this.natoms + 1);
System.arraycopy(m.atag, 0, this.atag, 0, this.natoms + 1);
this.x =  Clazz.newDoubleArray (this.natoms + 1, 0);
System.arraycopy(m.x, 0, this.x, 0, this.natoms + 1);
this.y =  Clazz.newDoubleArray (this.natoms + 1, 0);
System.arraycopy(m.y, 0, this.y, 0, this.natoms + 1);
this.label =  new Array(this.natoms + 1);
System.arraycopy(m.label, 0, this.label, 0, this.natoms + 1);
this.va =  Clazz.newIntArray (this.nbonds + 1, 0);
System.arraycopy(m.va, 0, this.va, 0, this.nbonds + 1);
this.vb =  Clazz.newIntArray (this.nbonds + 1, 0);
System.arraycopy(m.vb, 0, this.vb, 0, this.nbonds + 1);
this.nasv =  Clazz.newIntArray (this.nbonds + 1, 0);
System.arraycopy(m.nasv, 0, this.nasv, 0, this.nbonds + 1);
this.btag =  new Array(this.nbonds + 1);
System.arraycopy(m.btag, 0, this.btag, 0, this.nbonds + 1);
this.stereob =  Clazz.newIntArray (this.nbonds + 1, 0);
System.arraycopy(m.stereob, 0, this.stereob, 0, this.nbonds + 1);
this.$mark =  Clazz.newIntArray (this.nmarked + 1, 2, 0);
for (var i = 1; i <= this.nmarked; i++) {
this.$mark[i][0] = m.$mark[i][0];
this.$mark[i][1] = m.$mark[i][1];
}
this.doColoring = m.doColoring;
}, "jme.JMEmol");
Clazz.makeConstructor(c$, 
function(jme, mols, nmols){
this.construct (jme);
for (var i = 1; i <= nmols; i++) {
this.natoms += mols[i].natoms;
this.nbonds += mols[i].nbonds;
this.nmarked += mols[i].nmarked;
}
this.an =  Clazz.newIntArray (this.natoms + 1, 0);
this.q =  Clazz.newIntArray (this.natoms + 1, 0);
this.nh =  Clazz.newIntArray (this.natoms + 1, 0);
this.abg =  Clazz.newIntArray (this.natoms + 1, 0);
this.atag =  new Array(this.natoms + 1);
this.x =  Clazz.newDoubleArray (this.natoms + 1, 0);
this.y =  Clazz.newDoubleArray (this.natoms + 1, 0);
this.label =  new Array(this.natoms + 1);
this.va =  Clazz.newIntArray (this.nbonds + 1, 0);
this.vb =  Clazz.newIntArray (this.nbonds + 1, 0);
this.nasv =  Clazz.newIntArray (this.nbonds + 1, 0);
this.btag =  new Array(this.nbonds + 1);
this.stereob =  Clazz.newIntArray (this.nbonds + 1, 0);
this.$mark =  Clazz.newIntArray (this.nmarked + 1, 2, 0);
var na = 0;
var nb = 0;
var nm = 0;
var nadd = 0;
for (var i = 1; i <= nmols; i++) {
for (var j = 1; j <= mols[i].natoms; j++) {
na++;
this.an[na] = mols[i].an[j];
this.x[na] = mols[i].x[j];
this.y[na] = mols[i].y[j];
this.q[na] = mols[i].q[j];
this.nh[na] = mols[i].nh[j];
this.abg[na] = mols[i].abg[j];
this.atag[na] = mols[i].atag[j];
this.label[na] = mols[i].label[j];
}
for (var j = 1; j <= mols[i].nbonds; j++) {
nb++;
this.nasv[nb] = mols[i].nasv[j];
this.stereob[nb] = mols[i].stereob[j];
this.va[nb] = mols[i].va[j] + nadd;
this.vb[nb] = mols[i].vb[j] + nadd;
this.btag[nb] = mols[i].btag[j];
}
for (var j = 1; j <= mols[i].nmarked; j++) {
nm++;
this.$mark[nm][0] = mols[i].$mark[j][0] + nadd;
this.$mark[nm][1] = mols[i].$mark[j][1];
}
nadd = na;
}
this.complete();
this.center();
}, "jme.JME,~A,~N");
Clazz.makeConstructor(c$, 
function(jme, m, part){
this.construct (jme);
var newn =  Clazz.newIntArray (m.natoms + 1, 0);
for (var i = 1; i <= m.natoms; i++) {
if (m.a[i] != part) continue;
this.createAtom();
this.an[this.natoms] = m.an[i];
this.x[this.natoms] = m.x[i];
this.y[this.natoms] = m.y[i];
this.q[this.natoms] = m.q[i];
this.nh[this.natoms] = m.nh[i];
this.abg[this.natoms] = m.abg[i];
this.atag[this.natoms] = m.atag[i];
this.label[this.natoms] = m.label[i];
newn[i] = this.natoms;
}
for (var i = 1; i <= m.nbonds; i++) {
var atom1 = m.va[i];
var atom2 = m.vb[i];
if (m.a[atom1] != part && m.a[atom2] != part) continue;
if (m.a[atom1] != part || m.a[atom2] != part) {
System.err.println("MOL multipart inconsistency - report bug !");
continue;
}this.createBond();
this.nasv[this.nbonds] = m.nasv[i];
this.stereob[this.nbonds] = m.stereob[i];
this.va[this.nbonds] = newn[atom1];
this.vb[this.nbonds] = newn[atom2];
this.btag[this.nbonds] = m.btag[i];
}
for (var i = 1; i <= m.nmarked; i++) {
var atom = m.$mark[i][0];
if (atom != part) continue;
this.nmarked++;
this.$mark[this.nmarked][0] = newn[atom];
this.$mark[this.nmarked][1] = m.$mark[i][1];
}
this.doColoring = m.doColoring;
this.complete();
this.center();
}, "jme.JME,jme.JMEmol,~N");
Clazz.makeConstructor(c$, 
function(jme, molecule, hasCoordinates){
this.construct (jme);
if (molecule.startsWith("\"")) molecule = molecule.substring(1, molecule.length);
if (molecule.endsWith("\"")) molecule = molecule.substring(0, molecule.length - 1);
if (molecule.length < 1) {
this.natoms = 0;
return;
}try {
var st =  new java.util.StringTokenizer(molecule);
var natomsx = Integer.$valueOf(st.nextToken()).intValue();
var nbondsx = Integer.$valueOf(st.nextToken()).intValue();
for (var i = 1; i <= natomsx; i++) {
var symbol = st.nextToken();
this.createAtom(symbol);
if (hasCoordinates) {
this.x[i] = Double.$valueOf(st.nextToken()).doubleValue();
this.y[i] = -Double.$valueOf(st.nextToken()).doubleValue();
}}
for (var i = 1; i <= nbondsx; i++) {
this.createBond();
this.va[i] = Integer.$valueOf(st.nextToken()).intValue();
this.vb[i] = Integer.$valueOf(st.nextToken()).intValue();
this.nasv[i] = Integer.$valueOf(st.nextToken()).intValue();
if (this.nasv[i] == -1) {
this.nasv[i] = 1;
this.stereob[i] = 1;
} else if (this.nasv[i] == -2) {
this.nasv[i] = 1;
this.stereob[i] = 2;
} else if (this.nasv[i] == -5) {
this.nasv[i] = 2;
this.stereob[i] = 10;
} else if (this.nasv[i] == 11 || this.nasv[i] == 12 || this.nasv[i] == 13 || this.nasv[i] == 14) {
this.stereob[i] = this.nasv[i];
this.nasv[i] = 9;
}}
this.fillFields();
if (hasCoordinates) {
this.scaling();
this.center();
}} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.err.println("read mol exception - " + e.getMessage());
this.natoms = 0;
return;
} else {
throw e;
}
}
this.deleteHydrogens();
this.complete();
}, "jme.JME,~S,~B");
Clazz.makeConstructor(c$, 
function(jme, atomIterator, bondIterator){
this.construct (jme);
this.init();
var atomMap =  new java.util.Hashtable();
while (atomIterator.hasNext()) {
this.createAtom();
atomMap.put(atomIterator.getUniqueID(), Integer.$valueOf(this.natoms));
this.x[this.natoms] = atomIterator.getXYZ().x;
this.y[this.natoms] = -atomIterator.getXYZ().y;
this.q[this.natoms] = atomIterator.getFormalCharge();
this.setAtom(this.natoms, J.api.JmolAdapter.getElementSymbol(atomIterator.getElement()));
}
while (bondIterator.hasNext()) {
this.createBond();
var i = this.nbonds;
this.va[i] = atomMap.get(bondIterator.getAtomUniqueID1()).intValue();
this.vb[i] = atomMap.get(bondIterator.getAtomUniqueID2()).intValue();
var bo = bondIterator.getEncodedOrder();
switch (bo) {
case 1025:
this.nasv[i] = 1;
this.stereob[i] = 1;
break;
case 1041:
this.nasv[i] = 1;
this.stereob[i] = 2;
break;
case 1:
case 513:
this.nasv[i] = 1;
break;
case 2:
case 514:
this.nasv[i] = 2;
break;
case 3:
this.nasv[i] = 3;
break;
case 515:
case 1057:
default:
if ((bo & 0x07) != 0) this.nasv[i] = (bo & 0x07);
break;
}
}
this.fillFields();
this.scaling();
this.center();
this.complete();
this.deleteHydrogens();
this.complete();
}, "jme.JME,J.api.JmolAdapterAtomIterator,J.api.JmolAdapterBondIterator");
Clazz.makeConstructor(c$, 
function(jme, molFile){
this.construct (jme);
if (molFile == null) return;
var line = "";
var separator = jme.JMEmol.findSeparator(molFile);
var st =  new java.util.StringTokenizer(molFile, separator, true);
for (var i = 1; i <= 4; i++) {
line = jme.JMEmol.nextData(st, separator);
}
var natomsx = Integer.$valueOf(line.substring(0, 3).trim()).intValue();
var nbondsx = Integer.$valueOf(line.substring(3, 6).trim()).intValue();
for (var i = 1; i <= natomsx; i++) {
this.createAtom();
line = jme.JMEmol.nextData(st, separator);
this.x[i] = Double.$valueOf(line.substring(0, 10).trim()).doubleValue();
this.y[i] = -Double.$valueOf(line.substring(10, 20).trim()).doubleValue();
var endsymbol = 34;
if (line.length < 34) endsymbol = line.length;
var symbol = line.substring(31, endsymbol).trim();
this.setAtom(i, symbol);
if (line.length >= 62) {
var s = line.substring(60, 63).trim();
if (s.length > 0) {
var mark = Integer.$valueOf(s).intValue();
if (mark > 0) {
this.touchedAtom = i;
jme.currentMark = mark;
this.mark();
this.touchedAtom = 0;
}}}}
for (var i = 1; i <= nbondsx; i++) {
this.createBond();
line = jme.JMEmol.nextData(st, separator);
this.va[i] = Integer.$valueOf(line.substring(0, 3).trim()).intValue();
this.vb[i] = Integer.$valueOf(line.substring(3, 6).trim()).intValue();
var nasvx = Integer.$valueOf(line.substring(6, 9).trim()).intValue();
if (nasvx == 1) this.nasv[i] = 1;
 else if (nasvx == 2) this.nasv[i] = 2;
 else if (nasvx == 3) this.nasv[i] = 3;
 else this.nasv[i] = 9;
var stereo = 0;
if (line.length > 11) stereo = Integer.$valueOf(line.substring(9, 12).trim()).intValue();
if (nasvx == 1 && stereo == 1) {
this.nasv[i] = 1;
this.stereob[i] = 1;
}if (nasvx == 1 && stereo == 6) {
this.nasv[i] = 1;
this.stereob[i] = 2;
}}
this.fillFields();
this.scaling();
this.center();
this.complete();
while (st.hasMoreTokens()) {
if ((line = st.nextToken()) == null) break;
if (line.startsWith("M  END")) break;
if (line.startsWith("M  CHG")) {
var stq =  new java.util.StringTokenizer(line);
stq.nextToken();
stq.nextToken();
var ndata = Integer.$valueOf(stq.nextToken()).intValue();
for (var i = 1; i <= ndata; i++) {
var a = Integer.$valueOf(stq.nextToken()).intValue();
this.q[a] = Integer.$valueOf(stq.nextToken()).intValue();
}
}if (line.startsWith("M  APO")) {
var stq =  new java.util.StringTokenizer(line);
stq.nextToken();
stq.nextToken();
var ndata = Integer.$valueOf(stq.nextToken()).intValue();
for (var i = 1; i <= ndata; i++) {
var a = Integer.$valueOf(stq.nextToken()).intValue();
var nr = Integer.$valueOf(stq.nextToken()).intValue();
this.touchedAtom = a;
this.addBond();
this.setAtom(this.natoms, "R" + nr);
this.touchedAtom = 0;
}
}}
this.deleteHydrogens();
this.complete();
}, "jme.JME,~S");
Clazz.defineMethod(c$, "init", 
function(){
this.natoms = 0;
this.nbonds = 0;
this.nmarked = 0;
});
c$.nextData = Clazz.defineMethod(c$, "nextData", 
function(st, separator){
while (st.hasMoreTokens()) {
var s = st.nextToken();
if (s.equals(separator)) return " ";
if (!st.nextToken().equals(separator)) {
System.err.println("mol file line separator problem!");
}while (true) {
var c = s.charAt(s.length - 1);
if (c == '|' || c == '\n' || c == '\r') {
s = s.substring(0, s.length - 1);
if (s.length == 0) return " ";
} else break;
}
return s;
}
return null;
}, "java.util.StringTokenizer,~S");
c$.findSeparator = Clazz.defineMethod(c$, "findSeparator", 
function(molFile){
var st =  new java.util.StringTokenizer(molFile, "\n", true);
if (st.countTokens() > 4) return "\n";
st =  new java.util.StringTokenizer(molFile, "|", true);
if (st.countTokens() > 4) return "|";
System.err.println("Cannot process mol file, use | as line separator !");
return null;
}, "~S");
Clazz.defineMethod(c$, "getAtomCount", 
function(){
return this.natoms;
});
Clazz.defineMethod(c$, "getBondCount", 
function(){
return this.nbonds;
});
Clazz.defineMethod(c$, "getX", 
function(i){
return this.x[i] * 1.4 / 25;
}, "~N");
Clazz.defineMethod(c$, "getY", 
function(i){
return this.y[i] * 1.4 / 25;
}, "~N");
Clazz.defineMethod(c$, "setAtomProperties", 
function(xx, yy, ahc, aq){
this.x[this.natoms] = xx;
this.y[this.natoms] = yy;
this.setAtomHydrogenCount(this.natoms, ahc);
this.setAtomFormalCharge(this.natoms, aq);
}, "~N,~N,~N,~N");
Clazz.defineMethod(c$, "getHydrogenCount", 
function(i){
return this.nh[i];
}, "~N");
Clazz.defineMethod(c$, "getCharge", 
function(i){
return this.q[i];
}, "~N");
Clazz.defineMethod(c$, "getBondProperties", 
function(i){
var bd =  Clazz.newIntArray (4, 0);
bd[0] = this.va[i];
bd[1] = this.vb[i];
bd[2] = this.nasv[i];
bd[3] = this.stereob[i];
return bd;
}, "~N");
Clazz.defineMethod(c$, "setBondProperties", 
function(bp0, bp1, bp2, bp3){
this.va[this.nbonds] = bp0;
this.vb[this.nbonds] = bp1;
this.nasv[this.nbonds] = bp2;
this.stereob[this.nbonds] = bp3;
}, "~N,~N,~N,~N");
Clazz.defineMethod(c$, "completeMolecule", 
function(){
this.fillFields();
this.scaling();
this.center();
this.complete();
});
Clazz.defineMethod(c$, "complete", 
function(){
this.fillFields();
var storage = this.nasv.length;
this.xb =  Clazz.newIntArray (storage, 0);
this.yb =  Clazz.newIntArray (storage, 0);
this.findBondCenters();
this.valenceState();
});
Clazz.defineMethod(c$, "scaling", 
function(){
var dx;
var dy;
var sumlen = 0.;
var scale = 0.;
for (var i = 1; i <= this.nbonds; i++) {
dx = this.x[this.va[i]] - this.x[this.vb[i]];
dy = this.y[this.va[i]] - this.y[this.vb[i]];
sumlen += Math.sqrt(dx * dx + dy * dy);
}
if (this.nbonds > 0) {
sumlen = sumlen / this.nbonds;
scale = 25 / sumlen;
} else if (this.natoms > 1) {
scale = 75.0 / Math.sqrt((this.x[1] - this.x[2]) * (this.x[1] - this.x[2]) + (this.y[1] - this.y[2]) * (this.y[1] - this.y[2]));
}for (var i = 1; i <= this.natoms; i++) {
this.x[i] *= scale;
this.y[i] *= scale;
}
});
Clazz.defineMethod(c$, "center", 
function(){
var center =  Clazz.newDoubleArray (4, 0);
var xpix = 0;
var ypix = 0;
if (this.jme != null && this.jme.dimension != null && this.jme.dimension.width > 0) {
xpix = this.jme.dimension.width - this.jme.sd;
ypix = this.jme.dimension.height - this.jme.sd * 3;
}if (xpix <= 0 || ypix <= 0) {
this.needRecentering = true;
return;
}this.centerPoint(center);
var shiftx = Clazz.doubleToInt(xpix / 2) - Math.round(center[0]);
var shifty = Clazz.doubleToInt(ypix / 2) - Math.round(center[1]);
if (!this.jme.nocenter) for (var i = 1; i <= this.natoms; i++) {
this.x[i] += shiftx;
this.y[i] += shifty;
}
this.findBondCenters();
});
Clazz.defineMethod(c$, "testAtomTouch", 
function(xx, yy){
var i;
var atom;
var min;
var dx;
var dy;
var rx;
atom = 0;
min = 51;
for (i = 1; i <= this.natoms; i++) {
dx = xx - this.x[i];
dy = yy - this.y[i];
rx = dx * dx + dy * dy;
if (rx < 50) if (rx < min) {
min = rx;
atom = i;
}}
return atom;
}, "~N,~N");
Clazz.defineMethod(c$, "testBondTouch", 
function(xx, yy){
var i;
var bond;
var min;
var dx;
var dy;
var rx;
bond = 0;
min = 51;
for (i = 1; i <= this.nbonds; i++) {
dx = xx - this.xb[i];
dy = yy - this.yb[i];
rx = dx * dx + dy * dy;
if (rx < 50) if (rx < min) {
min = rx;
bond = i;
}}
return bond;
}, "~N,~N");
Clazz.defineMethod(c$, "reset", 
function(){
this.save();
this.natoms = 0;
this.nbonds = 0;
this.nmarked = 0;
});
Clazz.defineMethod(c$, "draw", 
function(g){
var atom1;
var atom2;
var xa;
var ya;
var xb;
var yb;
var dx;
var dy;
var dd;
var sina = 1.;
var cosa = 1.;
var sirka2s;
var sirka2c;
var sirka2 = 2.;
var sirka3 = 3.;
if (this.needRecentering) {
this.center();
this.jme.alignMolecules(1, this.jme.nmols, 0);
this.needRecentering = false;
}if (this.jme.depictScale != 1.) {
sirka2 *= this.jme.depictScale;
sirka3 *= this.jme.depictScale;
var xs = 1.0;
if (this.jme.depictScale < 0.7) xs = 1.2;
var fs = Clazz.doubleToInt(this.jme.fontSize * this.jme.depictScale * xs);
this.jme.$font =  new java.awt.Font("Helvetica", 0, fs);
this.jme.fontMet = g.getFontMetrics(this.jme.$font);
}if (this.jme.depictBorder) {
g.setColor(java.awt.Color.black);
g.drawRect(0, 0, this.jme.dimension.width - 1, this.jme.dimension.height - 1);
}if (this.natoms == 0) return;
if (this.doColoring == -1) {
var cs = Math.round(sirka2 * 12);
for (var i = 1; i <= this.natoms; i++) {
if (this.abg[i] > 0 && this.abg[i] < 7) {
g.setColor(this.jme.psColor[this.abg[i]]);
g.fillOval(Clazz.doubleToInt(this.x[i] - cs / 2.), Clazz.doubleToInt(this.y[i] - cs / 2.), cs, cs);
}}
for (var i = 1; i <= this.nbonds; i++) {
atom1 = this.va[i];
atom2 = this.vb[i];
if (this.abg[atom1] == 0) continue;
if (this.abg[atom1] != this.abg[atom2]) continue;
g.setColor(this.jme.psColor[this.abg[atom1]]);
dx = this.x[atom2] - this.x[atom1];
dy = this.y[atom2] - this.y[atom1];
dd = Math.sqrt(dx * dx + dy * dy);
if (dd < 1.) dd = 1.;
sina = dy / dd;
cosa = dx / dd;
sirka2s = (sirka3 * 3) * sina;
sirka2c = (sirka3 * 3) * cosa;
var xr =  Clazz.newIntArray (4, 0);
var yr =  Clazz.newIntArray (4, 0);
xr[0] = Clazz.doubleToInt(this.x[atom1] + sirka2s);
yr[0] = Clazz.doubleToInt(this.y[atom1] - sirka2c);
xr[1] = Clazz.doubleToInt(this.x[atom2] + sirka2s);
yr[1] = Clazz.doubleToInt(this.y[atom2] - sirka2c);
xr[2] = Clazz.doubleToInt(this.x[atom2] - sirka2s);
yr[2] = Clazz.doubleToInt(this.y[atom2] + sirka2c);
xr[3] = Clazz.doubleToInt(this.x[atom1] - sirka2s);
yr[3] = Clazz.doubleToInt(this.y[atom1] + sirka2c);
g.fillPolygon(xr, yr, 4);
}
}var neighborXSum = jme.JMEUtil.createDArray(this.natoms + 1);
var neighborCount = jme.JMEUtil.createArray(this.natoms + 1);
for (var i = 1; i <= this.nbonds; i++) {
atom1 = this.va[i];
atom2 = this.vb[i];
neighborXSum[atom1] += this.x[atom2];
neighborXSum[atom2] += this.x[atom1];
neighborCount[atom1]++;
neighborCount[atom2]++;
g.setColor(java.awt.Color.black);
if (this.doColoring == 1) {
if (this.abg[atom1] != 0 && this.abg[atom1] == this.abg[atom2]) g.setColor(this.jme.psColor[this.abg[atom1]]);
}if (this.stereob[i] == 3 || this.stereob[i] == 4) {
var d = atom1;
atom1 = atom2;
atom2 = d;
}xa = this.x[atom1];
ya = this.y[atom1];
xb = this.x[atom2];
yb = this.y[atom2];
if (this.nasv[i] != 1 || this.stereob[i] != 0) {
dx = xb - xa;
dy = yb - ya;
dd = Math.sqrt(dx * dx + dy * dy);
if (dd < 1.) dd = 1.;
sina = dy / dd;
cosa = dx / dd;
}switch (this.nasv[i]) {
case 2:
if (this.stereob[i] >= 10) g.setColor(java.awt.Color.magenta);
sirka2s = sirka2 * sina;
sirka2c = sirka2 * cosa;
g.drawLine(Math.round(xa + sirka2s), Math.round(ya - sirka2c), Math.round(xb + sirka2s), Math.round(yb - sirka2c));
g.drawLine(Math.round(xa - sirka2s), Math.round(ya + sirka2c), Math.round(xb - sirka2s), Math.round(yb + sirka2c));
g.setColor(java.awt.Color.black);
break;
case 3:
var ixa = Math.round(xa);
var iya = Math.round(ya);
var ixb = Math.round(xb);
var iyb = Math.round(yb);
g.drawLine(ixa, iya, ixb, iyb);
var sirka3s = Math.round(sirka3 * sina);
var sirka3c = Math.round(sirka3 * cosa);
g.drawLine(ixa + sirka3s, iya - sirka3c, ixb + sirka3s, iyb - sirka3c);
g.drawLine(ixa - sirka3s, iya + sirka3c, ixb - sirka3s, iyb + sirka3c);
break;
case 9:
case 0:
for (var k = 0; k < 10; k++) {
var xax = xa - (xa - xb) / 10. * k;
var yax = ya - (ya - yb) / 10. * k;
g.drawLine(Math.round(xax), Math.round(yax), Math.round(xax), Math.round(yax));
}
g.setFont(this.jme.$font);
var h = jme.JMEUtil.stringHeight(this.jme.fontMet);
var o = this.btag[i];
var z = "?";
if (o != null) z = o;
var w = this.jme.fontMet.stringWidth(z);
var xstart = Math.round((xa + xb) / 2. - w / 2.);
var ystart = Math.round((ya + yb) / 2. + h / 2 - 1);
g.setColor(java.awt.Color.magenta);
g.drawString(z, xstart, ystart);
g.setColor(java.awt.Color.black);
break;
default:
if (this.stereob[i] == 1 || this.stereob[i] == 3) {
sirka2s = sirka3 * sina;
sirka2c = sirka3 * cosa;
var px =  Clazz.newIntArray (3, 0);
var py =  Clazz.newIntArray (3, 0);
px[0] = Math.round(xb + sirka2s);
py[0] = Math.round(yb - sirka2c);
px[1] = Math.round(xa);
py[1] = Math.round(ya);
px[2] = Math.round(xb - sirka2s);
py[2] = Math.round(yb + sirka2c);
g.fillPolygon(px, py, 3);
} else if (this.stereob[i] == 2 || this.stereob[i] == 4) {
sirka2s = sirka3 * sina;
sirka2c = sirka3 * cosa;
for (var k = 0; k < 10; k++) {
var xax = xa - (xa - xb) / 10. * k;
var yax = ya - (ya - yb) / 10. * k;
var sc = k / 10.;
g.drawLine(Math.round(xax + sirka2s * sc), Math.round(yax - sirka2c * sc), Math.round(xax - sirka2s * sc), Math.round(yax + sirka2c * sc));
}
} else g.drawLine(Math.round(xa), Math.round(ya), Math.round(xb), Math.round(yb));
break;
}
if (this.jme.doTags) {
if (this.btag[i] != null && this.btag[i].length > 0) {
g.setFont(this.jme.$font);
var h = this.jme.fontMet.getAscent();
var w = this.jme.fontMet.stringWidth(this.btag[i]);
var xstart = Math.round((xa + xb) / 2. - w / 2.);
var ystart = Math.round((ya + yb) / 2. + Clazz.doubleToInt(h / 2) - 1);
g.setColor(java.awt.Color.red);
g.drawString(this.btag[i], xstart, ystart);
g.setColor(java.awt.Color.black);
}}}
g.setFont(this.jme.$font);
var h = this.jme.fontMet.getAscent();
var al =  new Array(this.natoms + 1);
for (var i = 1; i <= this.natoms; i++) {
var n = neighborCount[i];
var diff = neighborXSum[i] / neighborCount[i] - this.x[i];
var alignment;
if (n > 2 || n == 0 || n == 2 && Math.abs(diff) < 8) {
alignment = 1;
} else if (n == 1 && Math.abs(diff) < 2) {
alignment = 0;
} else {
alignment = (diff < 0 ? 0 : 2);
}al[i] =  new jme.AtomDisplayLabel(this.x[i], this.y[i], this.getAtomLabel(i), this.an[i], this.nv[i], this.sumBondOrders(i), this.nh[i], this.q[i], 0, -1, alignment, this.jme.fontMet, h, this.jme.showHydrogens);
if (!al[i].noLabelAtom) {
g.setColor(this.jme.canvasBg);
if (this.doColoring == -1 && this.abg[i] != 0) g.setColor(this.jme.psColor[this.abg[i]]);
al[i].fillRect(g);
if (this.doColoring == 1) {
if (this.abg[i] != 0) g.setColor(this.jme.psColor[this.abg[i]]);
 else g.setColor(java.awt.Color.black);
} else {
g.setColor(jme.JME.color[this.an[i]]);
}if (this.jme.bwMode) g.setColor(java.awt.Color.black);
al[i].draw(g);
}}
for (var k = 1; k <= this.nmarked; k++) {
var atom = this.$mark[k][0];
var w = this.jme.fontMet.stringWidth(al[atom].str);
var xstart = Math.round(this.x[atom] - w / 2.);
var ystart = Math.round(this.y[atom] + Clazz.doubleToInt(h / 2) - 1);
g.setColor(java.awt.Color.magenta);
g.drawString(" " + this.$mark[k][1], xstart + w, ystart);
}
if (this.jme.doTags) {
for (var i = 1; i <= this.natoms; i++) {
if (this.atag[i] == null || this.atag[i].equals("")) continue;
var w = this.jme.fontMet.stringWidth(al[i].str);
var xstart = Math.round(this.x[i] - w / 2.);
var ystart = Math.round(this.y[i] + Clazz.doubleToInt(h / 2) - 1);
g.setColor(java.awt.Color.red);
g.drawString(" " + this.atag[i], xstart + w, ystart);
}
}if ((this.touchedAtom > 0 || this.touchedBond > 0) && !this.jme.webme) {
g.setColor(this.jme.$action == 104 ? java.awt.Color.red : java.awt.Color.blue);
if (this.touchedAtom > 0 && this.jme.$action != 106) {
al[this.touchedAtom].drawRect(g);
}if (this.touchedBond > 0) {
atom1 = this.va[this.touchedBond];
atom2 = this.vb[this.touchedBond];
dx = this.x[atom2] - this.x[atom1];
dy = this.y[atom2] - this.y[atom1];
dd = Math.sqrt(dx * dx + dy * dy);
if (dd < 1.) dd = 1.;
sina = dy / dd;
cosa = dx / dd;
sirka2s = (sirka3 + 1) * sina;
sirka2c = (sirka3 + 1) * cosa;
var px =  Clazz.newIntArray (5, 0);
var py =  Clazz.newIntArray (5, 0);
px[0] = Math.round(this.x[atom1] + sirka2s);
px[1] = Math.round(this.x[atom2] + sirka2s);
py[0] = Math.round(this.y[atom1] - sirka2c);
py[1] = Math.round(this.y[atom2] - sirka2c);
px[3] = Math.round(this.x[atom1] - sirka2s);
px[2] = Math.round(this.x[atom2] - sirka2s);
py[3] = Math.round(this.y[atom1] + sirka2c);
py[2] = Math.round(this.y[atom2] + sirka2c);
px[4] = px[0];
py[4] = py[0];
if (this.jme.$action != 106) g.drawPolygon(px, py, 5);
markGroup : if (this.jme.$action == 106) {
if (!this.isRotatableBond(this.va[this.touchedBond], this.vb[this.touchedBond])) break markGroup;
var nsub = 0;
for (var i = 1; i <= this.natoms; i++) if (this.a[i] > 0) nsub++;

if (nsub > Clazz.doubleToInt(this.natoms / 2)) {
for (var i = 1; i <= this.natoms; i++) if (this.a[i] > 0) this.a[i] = 0;
 else this.a[i] = 1;

}g.setColor(java.awt.Color.red);
for (var i = 1; i <= this.natoms; i++) if (this.a[i] > 0) {
var w = this.jme.fontMet.stringWidth(al[i].str);
g.drawRect(Math.round(this.x[i] - w / 2. - 1), Math.round(this.y[i] - h / 2. - 1), w + 2, h + 2);
}
}}}if (this.jme.webme) {
this.jme.apointx =  Clazz.newIntArray (this.natoms, 0);
this.jme.apointy =  Clazz.newIntArray (this.natoms, 0);
this.jme.bpointx =  Clazz.newIntArray (this.nbonds, 0);
this.jme.bpointy =  Clazz.newIntArray (this.nbonds, 0);
for (var i = 1; i <= this.natoms; i++) {
this.jme.apointx[i - 1] = Math.round(this.x[i]);
this.jme.apointy[i - 1] = Math.round(this.y[i]);
}
for (var i = 1; i <= this.nbonds; i++) {
this.jme.bpointx[i - 1] = Math.round((this.x[this.va[i]] + this.x[this.vb[i]]) / 2.);
this.jme.bpointy[i - 1] = Math.round((this.y[this.va[i]] + this.y[this.vb[i]]) / 2.);
}
}}, "java.awt.Graphics");
Clazz.defineMethod(c$, "move", 
function(movex, movey){
for (var i = 1; i <= this.natoms; i++) {
this.x[i] += movex;
this.y[i] += movey;
}
var center =  Clazz.newDoubleArray (4, 0);
this.centerPoint(center);
var centerx = center[0];
var centery = center[1];
if (centerx > 0 && centerx < this.jme.dimension.width - this.jme.sd && centery > 0 && centery < this.jme.dimension.height - this.jme.sd * 3) return;
for (var i = 1; i <= this.natoms; i++) {
this.x[i] -= movex;
this.y[i] -= movey;
}
}, "~N,~N");
Clazz.defineMethod(c$, "rotate", 
function(movex){
var center =  Clazz.newDoubleArray (4, 0);
this.centerPoint(center);
var centerx = center[0];
var centery = center[1];
var sinu = Math.sin(movex * 3.141592653589793 / 180.);
var cosu = Math.cos(movex * 3.141592653589793 / 180.);
for (var i = 1; i <= this.natoms; i++) {
var xx = this.x[i] * cosu + this.y[i] * sinu;
var yy = -this.x[i] * sinu + this.y[i] * cosu;
this.x[i] = xx;
this.y[i] = yy;
}
this.centerPoint(center);
for (var i = 1; i <= this.natoms; i++) {
this.x[i] += centerx - center[0];
this.y[i] += centery - center[1];
}
}, "~N");
Clazz.defineMethod(c$, "centerPoint", 
function(center){
this.getMinMax();
center[0] = (this.minx + (this.maxx - this.minx) / 2.);
center[1] = (this.miny + (this.maxy - this.miny) / 2.);
center[2] = this.maxx - this.minx;
center[3] = this.maxy - this.miny;
if (center[2] < 25) center[2] = 25;
if (center[3] < 25) center[3] = 25;
}, "~A");
Clazz.defineMethod(c$, "getMinMax", 
function(){
this.minx = this.miny = 1.7976931348623157E308;
this.maxx = this.maxy = -1.7976931348623157E308;
for (var i = 1; i <= this.natoms; i++) {
if (this.x[i] < this.minx) this.minx = this.x[i];
if (this.x[i] > this.maxx) this.maxx = this.x[i];
if (this.y[i] < this.miny) this.miny = this.y[i];
if (this.y[i] > this.maxy) this.maxy = this.y[i];
}
});
Clazz.defineMethod(c$, "shiftToXY", 
function(marginPixelsX, marginPixelsY){
if (this.natoms == 0) return  new java.awt.Dimension();
this.getMinMax();
marginPixelsX /= this.jme.depictScale;
marginPixelsY /= this.jme.depictScale;
this.needRecentering = false;
for (var i = 1; i <= this.natoms; i++) {
this.x[i] = this.x[i] - this.minx + marginPixelsX;
this.y[i] = this.y[i] - this.miny + marginPixelsY;
}
return  new java.awt.Dimension(Clazz.doubleToInt((marginPixelsX * 2 + (this.maxx - this.minx)) * this.jme.depictScale), Clazz.doubleToInt((marginPixelsY * 2 + (this.maxy - this.miny)) * this.jme.depictScale));
}, "~N,~N");
Clazz.defineMethod(c$, "rubberBanding", 
function(xnew, ynew){
var atom;
var dx;
var dy;
var rx;
var sina;
var cosa;
this.touchedAtom = 0;
this.x[0] = xnew;
this.y[0] = ynew;
atom = this.checkTouch(0);
if (atom > 0 && this.jme.$action != 205) {
this.touchedAtom = atom;
if (atom != this.touched_org) {
this.x[this.natoms] = this.x[atom];
this.y[this.natoms] = this.y[atom];
} else {
this.x[this.natoms] = this.xorg;
this.y[this.natoms] = this.yorg;
}} else {
if (this.jme.$action == 205) {
this.touchedBond = 0;
var last = this.chain[this.nchain];
var parent = this.chain[this.nchain - 1];
dx = this.x[last] - this.x[parent];
dy = this.y[last] - this.y[parent];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 1.0) rx = 1.0;
sina = dy / rx;
cosa = dx / rx;
var vv = rx / 2. / Math.tan(0.5235987755982988);
var xx = xnew - this.x[parent];
var yy = ynew - this.y[parent];
var xm = -rx / 2. + xx * cosa + yy * sina;
var ym = yy * cosa - xx * sina;
if (xm < 0.) {
if (this.nchain > 1) {
this.deleteAtom(this.natoms);
this.nchain--;
this.stopChain = false;
} else if (this.natoms == 2) {
if (this.y[2] - this.y[1] < 0 && ynew - this.y[1] > 0) this.y[2] = this.y[1] + rx / 2.;
 else if (this.y[2] - this.y[1] > 0 && ynew - this.y[1] < 0) this.y[2] = this.y[1] - rx / 2.;
if (this.x[2] - this.x[1] < 0 && xnew - this.x[1] > 0) this.x[2] = this.x[1] + rx * .866;
 else if (this.x[2] - this.x[1] > 0 && xnew - this.x[1] < 0) this.x[2] = this.x[1] - rx * .866;
} else {
if (this.nv[this.chain[0]] == 2) {
var ref = this.v[this.chain[0]][1];
if (ref == this.chain[1]) ref = this.v[this.chain[0]][2];
dx = this.x[this.chain[0]] - this.x[ref];
dy = this.y[this.chain[0]] - this.y[ref];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 1.0) rx = 1.0;
sina = dy / rx;
cosa = dx / rx;
xx = xnew - this.x[ref];
yy = ynew - this.y[ref];
var ymm = yy * cosa - xx * sina;
xx = this.x[this.chain[1]] - this.x[ref];
yy = this.y[this.chain[1]] - this.y[ref];
var yc1 = yy * cosa - xx * sina;
if (ymm > 0. && yc1 < 0. || ymm < 0. && yc1 > 0.) {
var bd = this.nbonds;
this.touchedAtom = this.chain[0];
this.addBond();
this.deleteBond(bd);
if (this.checkTouch(this.natoms) > 0) this.stopChain = true;
}}}} else {
if (this.stopChain) return;
var th = -1.0;
if (xm < rx * 1.5) th = (rx * 1.5 - xm) * vv / (rx * 1.5);
if (Math.abs(ym) > th) {
this.nchain++;
if (this.nchain > 100) {
this.jme.info("You are too focused on chains, enough of it for now !");
this.nchain--;
return;
}this.touchedAtom = this.natoms;
this.addBond(Math.round(ym));
this.chain[this.nchain] = this.natoms;
if (this.checkTouch(this.natoms) > 0) this.stopChain = true;
}}this.touchedAtom = 0;
var n = this.nchain;
this.jme.info(n + "");
} else {
dx = xnew - this.x[this.touched_org];
dy = ynew - this.y[this.touched_org];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 1.0) rx = 1.0;
sina = dy / rx;
cosa = dx / rx;
this.x[this.natoms] = this.x[this.touched_org] + 25 * cosa;
this.y[this.natoms] = this.y[this.touched_org] + 25 * sina;
}}}, "~N,~N");
Clazz.defineMethod(c$, "checkChain", 
function(){
if (this.stopChain) {
var n = this.checkTouch(this.natoms);
if (this.nv[n] < 6) {
this.createBond();
var parent = this.chain[this.nchain - 1];
this.va[this.nbonds] = n;
this.vb[this.nbonds] = parent;
this.v[n][++this.nv[n]] = parent;
this.v[parent][++this.nv[parent]] = n;
}this.deleteAtom(this.natoms);
}this.stopChain = false;
});
Clazz.defineMethod(c$, "checkTouch", 
function(atom){
var dx;
var dy;
var rx;
var min = 51;
var touch = 0;
for (var i = 1; i < this.natoms; i++) {
if (atom == i) continue;
dx = this.x[atom] - this.x[i];
dy = this.y[atom] - this.y[i];
rx = dx * dx + dy * dy;
if (rx < 50) if (rx < min) {
min = rx;
touch = i;
}}
return touch;
}, "~N");
Clazz.defineMethod(c$, "avoidTouch", 
function(from){
if (from == 0) from = this.natoms;
for (var i = this.natoms; i > this.natoms - from; i--) {
var n = this.checkTouch(i);
if (n == 0) continue;
this.x[i] += 6;
this.y[i] += 6;
}
}, "~N");
Clazz.defineMethod(c$, "deleteAtom", 
function(delatom){
var i;
var j;
var k;
var atom1;
var atom2;
j = 0;
for (i = 1; i <= this.nbonds; i++) {
atom1 = this.va[i];
atom2 = this.vb[i];
if (atom1 != delatom && atom2 != delatom) {
j++;
this.va[j] = atom1;
if (atom1 > delatom) this.va[j]--;
this.vb[j] = atom2;
if (atom2 > delatom) this.vb[j]--;
this.nasv[j] = this.nasv[i];
this.stereob[j] = this.stereob[i];
this.xb[j] = this.xb[i];
this.yb[j] = this.yb[i];
this.btag[j] = this.btag[i];
}}
this.nbonds = j;
for (i = delatom; i < this.natoms; i++) {
this.an[i] = this.an[i + 1];
this.q[i] = this.q[i + 1];
this.x[i] = this.x[i + 1];
this.y[i] = this.y[i + 1];
this.nh[i] = this.nh[i + 1];
this.abg[i] = this.abg[i + 1];
this.atag[i] = this.atag[i + 1];
this.nv[i] = this.nv[i + 1];
this.label[i] = this.label[i + 1];
for (j = 1; j <= this.nv[i]; j++) this.v[i][j] = this.v[i + 1][j];

}
this.natoms--;
if (this.natoms == 0) {
this.jme.clear();
return;
}for (i = 1; i <= this.natoms; i++) {
k = 0;
for (j = 1; j <= this.nv[i]; j++) {
atom1 = this.v[i][j];
if (atom1 == delatom) {
this.nh[i]++;
continue;
}if (atom1 > delatom) atom1--;
this.v[i][++k] = atom1;
}
this.nv[i] = k;
}
iloop : for (i = 1; i <= this.nmarked; i++) if (this.$mark[i][0] == delatom) {
for (j = i; j < this.nmarked; j++) {
this.$mark[j][0] = this.$mark[j + 1][0];
this.$mark[j][1] = this.$mark[j + 1][1];
}
this.nmarked--;
break iloop;
}
for (i = 1; i <= this.nmarked; i++) if (this.$mark[i][0] > delatom) this.$mark[i][0]--;

}, "~N");
Clazz.defineMethod(c$, "deleteBond", 
function(delbond){
var i;
var k;
var atom1;
var atom2;
atom1 = this.va[delbond];
atom2 = this.vb[delbond];
for (i = delbond; i < this.nbonds; i++) {
this.va[i] = this.va[i + 1];
this.vb[i] = this.vb[i + 1];
this.nasv[i] = this.nasv[i + 1];
this.stereob[i] = this.stereob[i + 1];
this.xb[i] = this.xb[i + 1];
this.yb[i] = this.yb[i + 1];
this.btag[i] = this.btag[i + 1];
}
this.nbonds--;
k = 0;
for (i = 1; i <= this.nv[atom1]; i++) if (this.v[atom1][i] != atom2) this.v[atom1][++k] = this.v[atom1][i];

this.nv[atom1] = k;
k = 0;
for (i = 1; i <= this.nv[atom2]; i++) if (this.v[atom2][i] != atom1) this.v[atom2][++k] = this.v[atom2][i];

this.nv[atom2] = k;
if (atom1 < atom2) {
k = atom1;
atom1 = atom2;
atom2 = k;
}if (this.nv[atom1] == 0) this.deleteAtom(atom1);
if (this.nv[atom2] == 0) this.deleteAtom(atom2);
}, "~N");
Clazz.defineMethod(c$, "deleteGroup", 
function(bond){
if (this.jme.webme) {
if (!this.isRotatableBond(this.va[this.touchedBond], this.vb[this.touchedBond])) return;
var nsub = 0;
for (var i = 1; i <= this.natoms; i++) if (this.a[i] > 0) nsub++;

if (nsub > Clazz.doubleToInt(this.natoms / 2)) {
for (var i = 1; i <= this.natoms; i++) if (this.a[i] > 0) this.a[i] = 0;
 else this.a[i] = 1;

}}if (this.a[this.va[bond]] > 0 && this.a[this.vb[bond]] > 0) {
this.jme.info("Removal of substituent not possible.");
return;
}while (true) {
var atd = 0;
for (var i = this.natoms; i >= 1; i--) if (this.a[i] > 0 && i > atd) {
atd = i;
}
if (atd == 0) break;
this.deleteAtom(atd);
this.a[atd] = 0;
}
}, "~N");
Clazz.defineMethod(c$, "backCations", 
function(atom){
for (var i = 1; i <= this.nv[atom]; i++) {
var j = this.v[atom][i];
if (this.q[j] > 0) this.q[j]--;
}
}, "~N");
Clazz.defineMethod(c$, "backCations", 
function(atom1, atom2){
if (this.q[atom1] > 0) this.q[atom1]--;
if (this.q[atom2] > 0) this.q[atom2]--;
}, "~N,~N");
Clazz.defineMethod(c$, "flipGroup", 
function(atom){
if (this.nv[atom] < 2) return;
}, "~N");
Clazz.defineMethod(c$, "stereoBond", 
function(bond){
if (this.nasv[bond] == 1) {
var atom1 = this.va[bond];
var atom2 = this.vb[bond];
if (this.nv[atom1] < 2 && this.nv[atom2] < 2) {
this.stereob[bond] = 0;
this.jme.info("Stereomarking meaningless on this bond !");
return;
}if (this.jme.webme) {
if (!this.jme.revertStereo) {
if (this.stereob[bond] == 1) this.stereob[bond] = 3;
 else if (this.stereob[bond] == 3) this.stereob[bond] = 1;
 else {
if (this.nv[atom2] <= this.nv[atom1]) this.stereob[bond] = 1;
 else this.stereob[bond] = 3;
}} else {
if (this.stereob[bond] == 2) this.stereob[bond] = 4;
 else if (this.stereob[bond] == 4) this.stereob[bond] = 2;
 else {
if (this.nv[atom2] <= this.nv[atom1]) this.stereob[bond] = 2;
 else this.stereob[bond] = 4;
}}} else {
switch (this.stereob[bond]) {
case 0:
if (this.nv[atom2] <= this.nv[atom1]) this.stereob[bond] = 1;
 else this.stereob[bond] = 3;
break;
case 1:
this.stereob[bond] = 2;
break;
case 2:
if (this.nv[atom2] > 2) this.stereob[bond] = 3;
 else this.stereob[bond] = 1;
break;
case 3:
this.stereob[bond] = 4;
break;
case 4:
if (this.nv[atom1] > 2) this.stereob[bond] = 1;
 else this.stereob[bond] = 3;
break;
}
}} else if (this.nasv[bond] == 2) {
if (this.stereob[bond] == 10) this.stereob[bond] = 0;
 else this.stereob[bond] = 10;
} else {
this.jme.info("Stereomarking allowed only on single and double bonds!");
}}, "~N");
Clazz.defineMethod(c$, "getStereoAtom", 
function(bond){
switch (this.stereob[bond]) {
case 1:
case 2:
return this.va[bond];
case 3:
case 4:
return this.vb[bond];
}
return 0;
}, "~N");
Clazz.defineMethod(c$, "addBond", 
function(){
this.addBond(0);
});
Clazz.defineMethod(c$, "addBond", 
function(up){
var i;
var atom1;
var atom3;
var dx;
var dy;
var rx;
var sina;
var cosa;
var xx;
var yy;
this.createAtom();
switch (this.nv[this.touchedAtom]) {
case 0:
this.x[this.natoms] = this.x[this.touchedAtom] + this.rbond() * .866;
this.y[this.natoms] = this.y[this.touchedAtom] + this.rbond() * .5;
break;
case 1:
atom1 = this.v[this.touchedAtom][1];
atom3 = 0;
if (this.nv[atom1] == 2) {
if (this.v[atom1][1] == this.touchedAtom) atom3 = this.v[atom1][2];
 else atom3 = this.v[atom1][1];
}dx = this.x[this.touchedAtom] - this.x[atom1];
dy = this.y[this.touchedAtom] - this.y[atom1];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sina = dy / rx;
cosa = dx / rx;
xx = rx + this.rbond() * Math.cos(1.0471975511965976);
yy = this.rbond() * Math.sin(1.0471975511965976);
i = this.bondIdentity(this.touchedAtom, atom1);
if ((this.nasv[i] == 3) || this.jme.$action == 204 || (!this.isSingle(i) && (this.jme.$action == 203 || this.jme.$action == 204)) || this.linearAdding) {
xx = rx + this.rbond();
yy = 0.;
}if (atom3 > 0) if (((this.y[atom3] - this.y[atom1]) * cosa - (this.x[atom3] - this.x[atom1]) * sina) > 0.) yy = -yy;
if (up > 0 && yy < 0.) yy = -yy;
 else if (up < 0 && yy > 0.) yy = -yy;
this.x[this.natoms] = this.x[atom1] + xx * cosa - yy * sina;
this.y[this.natoms] = this.y[atom1] + yy * cosa + xx * sina;
break;
case 2:
var newPoint =  Clazz.newDoubleArray (2, 0);
this.addPoint(this.touchedAtom, this.rbond(), newPoint);
this.x[this.natoms] = newPoint[0];
this.y[this.natoms] = newPoint[1];
break;
case 3:
case 4:
case 5:
for (i = 1; i <= this.nv[this.touchedAtom]; i++) {
atom1 = this.v[this.touchedAtom][i];
dx = this.x[this.touchedAtom] - this.x[atom1];
dy = this.y[this.touchedAtom] - this.y[atom1];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
this.x[this.natoms] = this.x[this.touchedAtom] + this.rbond() * dx / rx;
this.y[this.natoms] = this.y[this.touchedAtom] + this.rbond() * dy / rx;
if (this.checkTouch(this.natoms) == 0 || i == this.nv[this.touchedAtom]) break;
}
break;
default:
this.natoms--;
this.jme.info("Are you trying to draw an hedgehog ?");
this.jme.lastAction = 9;
return;
}
this.completeBond();
this.xorg = this.x[this.natoms];
this.yorg = this.y[this.natoms];
}, "~N");
Clazz.defineMethod(c$, "rbond", 
function(){
return 25 * this.jme.depictScale;
});
Clazz.defineMethod(c$, "completeBond", 
function(){
this.nv[this.natoms] = 1;
this.nv[this.touchedAtom]++;
this.createBond();
this.nasv[this.nbonds] = 1;
if (this.jme.$action == 203) this.nasv[this.nbonds] = 2;
if (this.jme.$action == 204) this.nasv[this.nbonds] = 3;
this.va[this.nbonds] = this.touchedAtom;
this.vb[this.nbonds] = this.natoms;
if (this.jme.$action == 201) this.stereoBond(this.nbonds);
this.v[this.natoms][1] = this.touchedAtom;
this.v[this.touchedAtom][this.nv[this.touchedAtom]] = this.natoms;
this.xb[this.nbonds] = Math.round((this.x[this.touchedAtom] + this.x[this.natoms]) / 2.);
this.yb[this.nbonds] = Math.round((this.y[this.touchedAtom] + this.y[this.natoms]) / 2.);
});
Clazz.defineMethod(c$, "checkBond", 
function(){
var i;
var atom;
var atom1;
var atom2;
atom = this.checkTouch(this.natoms);
if (atom == 0) return;
this.natoms--;
for (i = 1; i < this.nbonds; i++) {
atom1 = this.va[i];
atom2 = this.vb[i];
if ((atom1 == atom && atom2 == this.touched_org) || (atom1 == this.touched_org && atom2 == atom)) {
this.nbonds--;
this.nv[this.touched_org]--;
if (this.nasv[i] < 3) {
this.nasv[i]++;
this.stereob[i] = 0;
} else this.jme.info("Maximum allowed bond order is 3 !");
return;
}}
if (this.nv[atom] == 6) {
this.nbonds--;
this.nv[this.touched_org]--;
this.jme.info("Not possible connection !");
return;
}this.vb[this.nbonds] = atom;
this.v[atom][++this.nv[atom]] = this.touched_org;
this.v[this.touched_org][this.nv[this.touched_org]] = atom;
this.xb[this.nbonds] = Math.round((this.x[this.touched_org] + this.x[atom]) / 2.);
this.yb[this.nbonds] = Math.round((this.y[this.touched_org] + this.y[atom]) / 2.);
});
Clazz.defineMethod(c$, "addGroup", 
function(emptyCanvas){
this.touched_org = this.touchedAtom;
var nadded = 0;
if (this.jme.$action == 233 || this.jme.$action == 237 || this.jme.$action == 236 || this.jme.$action == 239 || this.jme.$action == 251 || this.jme.$action == 252) {
this.addBond();
this.touchedAtom = this.natoms;
this.linearAdding = true;
this.addBond();
this.linearAdding = false;
this.touchedAtom = this.natoms - 1;
this.addBond();
this.touchedAtom = this.natoms - 2;
this.addBond();
if (this.jme.$action == 237) {
this.an[this.natoms] = 10;
this.an[this.natoms - 1] = 10;
this.an[this.natoms - 2] = 10;
}if (this.jme.$action == 236) {
this.an[this.natoms] = 9;
this.an[this.natoms - 1] = 9;
this.an[this.natoms - 2] = 9;
}if (this.jme.$action == 239) {
this.an[this.natoms] = 5;
this.an[this.natoms - 1] = 5;
this.an[this.natoms - 2] = 5;
this.an[this.natoms - 3] = 8;
this.nasv[this.nbonds] = 2;
this.nasv[this.nbonds - 1] = 2;
}if (this.jme.$action == 252) {
this.an[this.natoms] = 5;
this.an[this.natoms - 1] = 5;
this.an[this.natoms - 2] = 4;
this.an[this.natoms - 3] = 8;
this.nasv[this.nbonds] = 2;
this.nasv[this.nbonds - 1] = 2;
}if (this.jme.$action == 251) {
this.an[this.natoms] = 5;
this.an[this.natoms - 1] = 5;
this.an[this.natoms - 2] = 5;
this.an[this.natoms - 3] = 7;
this.nasv[this.nbonds] = 2;
}nadded = 4;
} else if (this.jme.$action == 244) {
this.addBond();
this.an[this.natoms] = 4;
this.touchedAtom = this.natoms;
this.addBond();
this.an[this.natoms] = 8;
this.touchedAtom = this.natoms;
this.linearAdding = true;
this.addBond();
this.linearAdding = false;
this.touchedAtom = this.natoms - 1;
this.addBond();
this.an[this.natoms] = 5;
this.nasv[this.nbonds] = 2;
this.touchedAtom = this.natoms - 2;
this.addBond();
this.an[this.natoms] = 5;
this.nasv[this.nbonds] = 2;
nadded = 5;
} else if (this.jme.$action == 234) {
this.addBond();
this.an[this.natoms] = 4;
this.touchedAtom = this.natoms;
this.addBond();
this.an[this.natoms] = 5;
this.nasv[this.nbonds] = 2;
this.touchedAtom = this.natoms - 1;
this.addBond();
this.an[this.natoms] = 5;
this.nasv[this.nbonds] = 2;
nadded = 3;
} else if (this.jme.$action == 235) {
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.an[this.natoms] = 5;
this.touchedAtom = this.natoms - 1;
this.addBond();
this.an[this.natoms] = 5;
this.nasv[this.nbonds] = 2;
nadded = 3;
} else if (this.jme.$action == 240) {
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.an[this.natoms] = 5;
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms - 2;
this.addBond();
this.an[this.natoms] = 5;
this.nasv[this.nbonds] = 2;
nadded = 4;
} else if (this.jme.$action == 241) {
this.addBond();
this.an[this.natoms] = 5;
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms - 1;
this.addBond();
this.nasv[this.nbonds] = 2;
this.an[this.natoms] = 5;
nadded = 4;
} else if (this.jme.$action == 243) {
this.addBond();
this.an[this.natoms] = 4;
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms - 1;
this.addBond();
nadded = 3;
} else if (this.jme.$action == 238) {
this.addBond();
this.touchedAtom = this.natoms;
this.linearAdding = true;
this.addBond();
this.nasv[this.nbonds] = 3;
this.linearAdding = false;
nadded = 2;
} else if (this.jme.$action == 249) {
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.nasv[this.nbonds] = 2;
this.an[this.natoms] = 5;
nadded = 2;
} else if (this.jme.$action == 250) {
this.addBond();
this.nasv[this.nbonds] = 2;
this.an[this.natoms] = 5;
nadded = 1;
} else if (this.jme.$action == 245) {
this.addBond();
this.touchedAtom = this.natoms;
this.linearAdding = true;
this.addBond();
this.touchedAtom = this.natoms;
this.nasv[this.nbonds] = 3;
this.addBond();
this.linearAdding = false;
nadded = 3;
} else if (this.jme.$action == 242) {
this.addBond();
this.touchedAtom = this.natoms;
this.linearAdding = true;
this.addBond();
this.nasv[this.nbonds] = 3;
this.an[this.natoms] = 4;
this.linearAdding = false;
nadded = 2;
} else if (this.jme.$action == 254) {
this.addBond();
this.an[this.natoms] = 9;
nadded = 1;
} else if (this.jme.$action == 255) {
this.addBond();
this.an[this.natoms] = 10;
nadded = 1;
} else if (this.jme.$action == 256) {
this.addBond();
this.an[this.natoms] = 11;
nadded = 1;
} else if (this.jme.$action == 257) {
this.addBond();
this.an[this.natoms] = 12;
nadded = 1;
} else if (this.jme.$action == 258) {
this.addBond();
this.an[this.natoms] = 4;
nadded = 1;
} else if (this.jme.$action == 259) {
this.addBond();
this.an[this.natoms] = 5;
nadded = 1;
} else if (this.jme.$action == 246) {
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
nadded = 2;
} else if (this.jme.$action == 247) {
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
nadded = 3;
} else if (this.jme.$action == 248) {
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
this.touchedAtom = this.natoms;
this.addBond();
nadded = 4;
} else if (this.jme.$action == 253) {
this.addGroupTemplate(emptyCanvas);
nadded = 4;
}this.avoidTouch(nadded);
this.touchedAtom = this.touched_org;
if (emptyCanvas) this.touchedAtom = 0;
}, "~B");
Clazz.defineMethod(c$, "addRing", 
function(){
var atom1;
var atom2;
var atom3;
var revert;
var dx;
var dy;
var rx;
var sina;
var cosa;
var xx;
var yy;
var diel;
var rc;
var uhol;
var xstart;
var ystart;
var returnTouch = -1;
var nmembered = 6;
switch (this.jme.$action) {
case 206:
nmembered = 3;
break;
case 207:
nmembered = 4;
break;
case 208:
case 221:
case 223:
nmembered = 5;
break;
case 210:
case 209:
nmembered = 6;
break;
case 211:
nmembered = 7;
break;
case 212:
nmembered = 8;
break;
case 229:
nmembered = 9;
break;
}
diel = 6.283185307179586 / nmembered;
rc = Math.sqrt(this.rbond() * this.rbond() / 2. / (1. - Math.cos(diel)));
if (this.touchedAtom > 0) {
if (this.nv[this.touchedAtom] < 2) {
this.addRingToBond(nmembered, diel, rc);
} else {
if (!this.jme.mouseShift) {
returnTouch = this.touchedAtom;
this.addBond();
this.touchedAtom = this.natoms;
this.addRingToBond(nmembered, diel, rc);
} else {
if (this.jme.$action == 209 || this.jme.$action == 221 || this.jme.$action == 223) {
this.jme.info("ERROR - cannot add aromatic spiro ring !");
this.jme.lastAction = 9;
return;
}for (var i = 1; i <= this.nv[this.touchedAtom]; i++) {
var bo = this.nasv[this.bondIdentity(this.touchedAtom, this.v[this.touchedAtom][i])];
if (i > 2 || bo != 1) {
this.jme.info("ERROR - spiro ring not possible here !");
this.jme.lastAction = 9;
return;
}}
var newPoint =  Clazz.newDoubleArray (2, 0);
this.addPoint(this.touchedAtom, rc, newPoint);
dx = this.x[this.touchedAtom] - newPoint[0];
dy = this.y[this.touchedAtom] - newPoint[1];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sina = dy / rx;
cosa = dx / rx;
for (var i = 1; i <= nmembered; i++) {
this.createAtom();
uhol = diel * i + 1.5707963267948966;
this.x[this.natoms] = newPoint[0] + rc * (Math.sin(uhol) * cosa - Math.cos(uhol) * sina);
this.y[this.natoms] = newPoint[1] + rc * (Math.cos(uhol) * cosa + Math.sin(uhol) * sina);
}
}}} else if (this.touchedBond > 0) {
atom1 = this.va[this.touchedBond];
atom2 = this.vb[this.touchedBond];
atom3 = 0;
if (this.nv[atom1] == 2) {
if (this.v[atom1][1] != atom2) atom3 = this.v[atom1][1];
 else atom3 = this.v[atom1][2];
} else if (this.nv[atom2] == 2) {
if (this.v[atom2][1] != atom1) atom3 = this.v[atom2][1];
 else atom3 = this.v[atom2][2];
revert = atom1;
atom1 = atom2;
atom2 = revert;
}if (atom3 == 0) if (this.v[atom1][1] != atom2) atom3 = this.v[atom1][1];
 else atom3 = this.v[atom1][2];
dx = this.x[atom2] - this.x[atom1];
dy = this.y[atom2] - this.y[atom1];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sina = dy / rx;
cosa = dx / rx;
xx = rx / 2.;
yy = rc * Math.sin((3.141592653589793 - diel) * .5);
revert = 1;
if (((this.y[atom3] - this.y[atom1]) * cosa - (this.x[atom3] - this.x[atom1]) * sina) > 0.) {
yy = -yy;
revert = 0;
}xstart = this.x[atom1] + xx * cosa - yy * sina;
ystart = this.y[atom1] + yy * cosa + xx * sina;
for (var i = 1; i <= nmembered; i++) {
this.createAtom();
uhol = diel * (i + .5) + 3.141592653589793 * revert;
this.x[this.natoms] = xstart + rc * (Math.sin(uhol) * cosa - Math.cos(uhol) * sina);
this.y[this.natoms] = ystart + rc * (Math.cos(uhol) * cosa + Math.sin(uhol) * sina);
if (revert == 1) {
if (i == nmembered) {
this.x[this.natoms] = this.x[atom1];
this.y[this.natoms] = this.y[atom1];
}if (i == nmembered - 1) {
this.x[this.natoms] = this.x[atom2];
this.y[this.natoms] = this.y[atom2];
}} else {
if (i == nmembered - 1) {
this.x[this.natoms] = this.x[atom1];
this.y[this.natoms] = this.y[atom1];
}if (i == nmembered) {
this.x[this.natoms] = this.x[atom2];
this.y[this.natoms] = this.y[atom2];
}}}
} else {
var helpv = 0.5;
if (nmembered == 6) helpv = 0.;
for (var i = 1; i <= nmembered; i++) {
this.createAtom();
uhol = diel * (i - helpv);
this.x[this.natoms] = this.xorg + rc * Math.sin(uhol);
this.y[this.natoms] = this.yorg + rc * Math.cos(uhol);
}
}this.completeRing(nmembered);
this.checkRing(nmembered);
if (returnTouch > -1) this.touchedAtom = returnTouch;
});
Clazz.defineMethod(c$, "addRingToBond", 
function(nmembered, diel, rc){
var sina;
var cosa;
var dx;
var dy;
var rx;
var uhol;
var atom1 = 0;
if (this.nv[this.touchedAtom] == 0) {
sina = 0.;
cosa = 1.;
} else {
atom1 = this.v[this.touchedAtom][1];
dx = this.x[this.touchedAtom] - this.x[atom1];
dy = this.y[this.touchedAtom] - this.y[atom1];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sina = dy / rx;
cosa = dx / rx;
}var xstart = this.x[this.touchedAtom] + rc * cosa;
var ystart = this.y[this.touchedAtom] + rc * sina;
for (var i = 1; i <= nmembered; i++) {
this.createAtom();
uhol = diel * i - 1.5707963267948966;
this.x[this.natoms] = xstart + rc * (Math.sin(uhol) * cosa - Math.cos(uhol) * sina);
this.y[this.natoms] = ystart + rc * (Math.cos(uhol) * cosa + Math.sin(uhol) * sina);
}
}, "~N,~N,~N");
Clazz.defineMethod(c$, "completeRing", 
function(nmembered){
var i;
var atom = 0;
var atom3;
for (i = 1; i <= nmembered; i++) {
this.createBond();
this.nasv[this.nbonds] = 1;
atom = this.natoms - nmembered + i;
this.nv[atom] = 2;
this.va[this.nbonds] = atom;
this.vb[this.nbonds] = atom + 1;
}
this.vb[this.nbonds] = this.natoms - nmembered + 1;
if (this.jme.$action == 209) {
this.nasv[this.nbonds - 4] = 2;
this.nasv[this.nbonds - 2] = 2;
this.nasv[this.nbonds - 0] = 2;
if (this.touchedBond > 0) {
if (this.isSingle(this.touchedBond)) {
atom3 = 0;
if (this.nv[this.va[this.touchedBond]] > 1) {
atom3 = this.v[this.va[this.touchedBond]][1];
atom = this.va[this.touchedBond];
if (atom3 == this.vb[this.touchedBond]) atom3 = this.v[this.va[this.touchedBond]][2];
}if (atom3 == 0 && this.nv[this.vb[this.touchedBond]] > 1) {
atom3 = this.v[this.vb[this.touchedBond]][1];
atom = this.vb[this.touchedBond];
if (atom3 == this.vb[this.touchedBond]) atom3 = this.v[this.vb[this.touchedBond]][2];
}if (atom3 > 0) for (i = 1; i <= this.nbonds; i++) if ((this.va[i] == atom3 && this.vb[i] == atom) || (this.va[i] == atom && this.vb[i] == atom3)) {
if (!this.isSingle(i)) {
this.nasv[this.nbonds - 4] = 1;
this.nasv[this.nbonds - 2] = 1;
this.nasv[this.nbonds - 0] = 1;
this.nasv[this.nbonds - 5] = 2;
this.nasv[this.nbonds - 3] = 2;
this.nasv[this.nbonds - 1] = 3;
}break;
}
} else {
this.nasv[this.nbonds - 4] = 1;
this.nasv[this.nbonds - 2] = 1;
this.nasv[this.nbonds - 0] = 1;
this.nasv[this.nbonds - 5] = 2;
this.nasv[this.nbonds - 3] = 2;
this.nasv[this.nbonds - 1] = 2;
}}} else if (this.jme.$action == 221 || this.jme.$action == 223) {
if (this.touchedBond > 0) {
if (this.nasv[this.touchedBond] == 1) {
var isConjugated = false;
for (i = 1; i <= this.nv[this.va[this.touchedBond]]; i++) {
var ax = this.v[this.va[this.touchedBond]][i];
if (this.nasv[this.bondIdentity(this.va[this.touchedBond], ax)] > 1) {
isConjugated = true;
break;
}}
for (i = 1; i <= this.nv[this.vb[this.touchedBond]]; i++) {
var ax = this.v[this.vb[this.touchedBond]][i];
if (this.nasv[this.bondIdentity(this.vb[this.touchedBond], ax)] > 1) {
isConjugated = true;
break;
}}
if (!isConjugated) this.nasv[this.touchedBond] = 2;
}this.nasv[this.nbonds - 4] = 2;
this.an[this.natoms - 2] = 5;
} else if (this.touchedAtom > 0) {
if (this.jme.$action == 221) {
this.nasv[this.nbonds - 4] = 1;
this.nasv[this.nbonds - 2] = 1;
this.nasv[this.nbonds - 1] = 1;
this.nasv[this.nbonds - 3] = 2;
this.nasv[this.nbonds - 0] = 2;
this.an[this.natoms - 1] = 5;
} else {
this.nasv[this.nbonds - 3] = 1;
this.nasv[this.nbonds - 2] = 1;
this.nasv[this.nbonds - 0] = 1;
this.nasv[this.nbonds - 4] = 2;
this.nasv[this.nbonds - 1] = 2;
this.an[this.natoms - 2] = 5;
}} else {
this.nasv[this.nbonds - 3] = 1;
this.nasv[this.nbonds - 2] = 1;
this.nasv[this.nbonds - 0] = 1;
this.nasv[this.nbonds - 4] = 2;
this.nasv[this.nbonds - 1] = 2;
this.an[this.natoms - 2] = 5;
}}}, "~N");
Clazz.defineMethod(c$, "checkRing", 
function(nmembered){
var i;
var j;
var k;
var atom;
var atom1;
var atom2;
var ratom;
var rbond;
var noldbonds;
var noldatoms;
var parent =  Clazz.newIntArray (this.natoms + 1, 0);
var dx;
var dy;
var rx;
var min;
for (i = 1; i <= nmembered; i++) {
ratom = this.natoms - nmembered + i;
rbond = this.nbonds - nmembered + i;
this.v[ratom][1] = ratom - 1;
this.v[ratom][2] = ratom + 1;
atom1 = this.va[rbond];
atom2 = this.vb[rbond];
this.xb[rbond] = Math.round((this.x[atom1] + this.x[atom2]) / 2.);
this.yb[rbond] = Math.round((this.y[atom1] + this.y[atom2]) / 2.);
}
this.v[this.natoms - nmembered + 1][1] = this.natoms;
this.v[this.natoms][2] = this.natoms - nmembered + 1;
for (i = this.natoms - nmembered + 1; i <= this.natoms; i++) {
parent[i] = 0;
min = 51;
atom = 0;
for (j = 1; j <= this.natoms - nmembered; j++) {
dx = this.x[i] - this.x[j];
dy = this.y[i] - this.y[j];
rx = dx * dx + dy * dy;
if (rx < 50) if (rx < min) {
min = rx;
atom = j;
}}
if (atom > 0) if (this.touchedAtom == 0 || atom == this.touchedAtom) parent[i] = atom;
}
noldbonds = this.nbonds - nmembered;
bloop : for (i = noldbonds + 1; i <= noldbonds + nmembered; i++) {
atom1 = this.va[i];
atom2 = this.vb[i];
if (parent[atom1] > 0 && parent[atom2] > 0) {
for (k = 1; k <= noldbonds; k++) {
if ((this.va[k] == parent[atom1] && this.vb[k] == parent[atom2]) || (this.vb[k] == parent[atom1] && this.va[k] == parent[atom2])) continue bloop;
}
this.createBond();
this.nasv[this.nbonds] = this.nasv[i];
this.va[this.nbonds] = parent[atom1];
this.v[parent[atom1]][++this.nv[parent[atom1]]] = parent[atom2];
this.vb[this.nbonds] = parent[atom2];
this.v[parent[atom2]][++this.nv[parent[atom2]]] = parent[atom1];
this.xb[this.nbonds] = Math.round((this.x[this.va[this.nbonds]] + this.x[this.vb[this.nbonds]]) / 2.);
this.yb[this.nbonds] = Math.round((this.y[this.va[this.nbonds]] + this.y[this.vb[this.nbonds]]) / 2.);
} else if (parent[atom1] > 0) {
this.createBond();
this.nasv[this.nbonds] = this.nasv[i];
this.va[this.nbonds] = parent[atom1];
this.v[parent[atom1]][++this.nv[parent[atom1]]] = atom2;
this.vb[this.nbonds] = atom2;
this.v[atom2][++this.nv[atom2]] = parent[atom1];
this.xb[this.nbonds] = Math.round((this.x[this.va[this.nbonds]] + this.x[this.vb[this.nbonds]]) / 2.);
this.yb[this.nbonds] = Math.round((this.y[this.va[this.nbonds]] + this.y[this.vb[this.nbonds]]) / 2.);
} else if (parent[atom2] > 0) {
this.createBond();
this.nasv[this.nbonds] = this.nasv[i];
this.va[this.nbonds] = parent[atom2];
this.v[parent[atom2]][++this.nv[parent[atom2]]] = atom1;
this.vb[this.nbonds] = atom1;
this.v[atom1][++this.nv[atom1]] = parent[atom2];
this.xb[this.nbonds] = Math.round((this.x[this.va[this.nbonds]] + this.x[this.vb[this.nbonds]]) / 2.);
this.yb[this.nbonds] = Math.round((this.y[this.va[this.nbonds]] + this.y[this.vb[this.nbonds]]) / 2.);
}}
noldatoms = this.natoms - nmembered;
for (i = this.natoms; i > noldatoms; i--) {
if (parent[i] > 0) {
this.deleteAtom(i);
if (this.an[parent[i]] == 3) {
var sum = 0;
for (j = 1; j <= this.nv[parent[i]]; j++) {
var a2 = this.v[parent[i]][j];
for (k = 1; k <= this.nbonds; k++) {
if ((this.va[k] == parent[i] && this.vb[k] == a2) || (this.va[k] == a2 && this.vb[k] == parent[i])) sum += this.nasv[k];
}
}
if (sum > 4) {
for (k = noldbonds + 1; k <= noldbonds + nmembered; k++) this.nasv[k] = 1;

}}}}
if (this.touchedAtom > 0) this.avoidTouch(nmembered);
}, "~N");
Clazz.defineMethod(c$, "addPoint", 
function(touchedAtom, rbond, newPoint){
var dx;
var dy;
var rx;
var sina;
var cosa;
var xx;
var yy;
var xpoint;
var ypoint;
var atom1 = this.v[touchedAtom][1];
var atom2 = this.v[touchedAtom][2];
dx = this.x[atom2] - this.x[atom1];
dy = -(this.y[atom2] - this.y[atom1]);
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sina = dy / rx;
cosa = dx / rx;
var vzd = Math.abs((this.y[touchedAtom] - this.y[atom1]) * cosa + (this.x[touchedAtom] - this.x[atom1]) * sina);
if (vzd < 1.0) {
dx = this.x[touchedAtom] - this.x[atom1];
dy = this.y[touchedAtom] - this.y[atom1];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
xx = rx;
yy = rbond;
sina = dy / rx;
cosa = dx / rx;
newPoint[0] = this.x[atom1] + xx * cosa - yy * sina;
newPoint[1] = this.y[atom1] + yy * cosa + xx * sina;
} else {
xpoint = (this.x[atom1] + this.x[atom2]) / 2.;
ypoint = (this.y[atom1] + this.y[atom2]) / 2.;
dx = this.x[touchedAtom] - xpoint;
dy = this.y[touchedAtom] - ypoint;
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
newPoint[0] = this.x[touchedAtom] + rbond * dx / rx;
newPoint[1] = this.y[touchedAtom] + rbond * dy / rx;
}}, "~N,~N,~A");
Clazz.defineMethod(c$, "addGroupTemplate", 
function(emptyCanvas){
var mark1 = 0;
var tmol = this.jme.tmol;
for (var k = 1; k <= tmol.nmarked; k++) {
var atom = tmol.$mark[k][0];
if (tmol.$mark[k][1] == 1) mark1 = atom;
}
var nn = this.natoms;
var source = this.touchedAtom;
this.addBond();
var x1 = this.x[this.natoms];
var y1 = this.y[this.natoms];
this.deleteAtom(this.natoms);
var dx1 = this.x[source] - x1;
var dy1 = this.y[source] - y1;
var r = Math.sqrt(dx1 * dx1 + dy1 * dy1);
var sina = dy1 / r;
var cosa = dx1 / r;
for (var i = 1; i <= tmol.natoms; i++) {
this.createAtom();
this.an[this.natoms] = tmol.an[i];
this.q[this.natoms] = tmol.q[i];
this.nh[this.natoms] = tmol.nh[i];
this.x[this.natoms] = tmol.x[i];
this.y[this.natoms] = tmol.y[i];
}
for (var i = 1; i <= tmol.nbonds; i++) {
this.createBond();
this.va[this.nbonds] = tmol.va[i] + nn;
this.vb[this.nbonds] = tmol.vb[i] + nn;
this.nasv[this.nbonds] = tmol.nasv[i];
}
this.complete();
this.touchedAtom = mark1 + nn;
this.addBond();
var x2 = this.x[this.natoms];
var y2 = this.y[this.natoms];
this.deleteAtom(this.natoms);
var dx2 = this.x[mark1 + nn] - x2;
var dy2 = this.y[mark1 + nn] - y2;
r = Math.sqrt(dx2 * dx2 + dy2 * dy2);
var sinb = dy2 / r;
var cosb = dx2 / r;
for (var i = nn + 1; i <= this.natoms; i++) {
this.x[i] -= x2;
this.y[i] -= y2;
var xx = this.x[i] * cosb + this.y[i] * sinb;
var yy = this.y[i] * cosb - this.x[i] * sinb;
this.x[i] = xx;
this.y[i] = yy;
xx = -this.x[i] * cosa + this.y[i] * sina;
yy = -this.y[i] * cosa - this.x[i] * sina;
this.x[i] = xx;
this.y[i] = yy;
this.x[i] += this.x[source];
this.y[i] += this.y[source];
}
this.createBond();
this.va[this.nbonds] = source;
this.vb[this.nbonds] = mark1 + nn;
this.complete();
if (emptyCanvas) {
this.deleteAtom(source);
this.center();
}}, "~B");
Clazz.defineMethod(c$, "createAtom", 
function(){
this.natoms++;
if (this.natoms > this.an.length - 1) {
var storage = this.an.length + 10;
var n_an =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.an, 0, n_an, 0, this.an.length);
this.an = n_an;
var n_q =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.q, 0, n_q, 0, this.q.length);
this.q = n_q;
var n_nh =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.nh, 0, n_nh, 0, this.nh.length);
this.nh = n_nh;
var n_abg =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.abg, 0, n_abg, 0, this.abg.length);
this.abg = n_abg;
var n_atag =  new Array(storage);
System.arraycopy(this.atag, 0, n_atag, 0, this.atag.length);
this.atag = n_atag;
var n_label =  new Array(storage);
System.arraycopy(this.label, 0, n_label, 0, this.label.length);
this.label = n_label;
var n_x =  Clazz.newDoubleArray (storage, 0);
System.arraycopy(this.x, 0, n_x, 0, this.x.length);
this.x = n_x;
var n_y =  Clazz.newDoubleArray (storage, 0);
System.arraycopy(this.y, 0, n_y, 0, this.y.length);
this.y = n_y;
var n_v =  Clazz.newIntArray (storage, 7, 0);
System.arraycopy(this.v, 0, n_v, 0, this.v.length);
this.v = n_v;
var n_nv =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.nv, 0, n_nv, 0, this.nv.length);
this.nv = n_nv;
}this.an[this.natoms] = 3;
this.q[this.natoms] = 0;
this.abg[this.natoms] = 0;
this.atag[this.natoms] = null;
this.nh[this.natoms] = 0;
});
Clazz.defineMethod(c$, "createAtom", 
function(symbol){
this.createAtom();
this.setAtom(this.natoms, symbol);
}, "~S");
Clazz.defineMethod(c$, "setAtom", 
function(atom, symbol){
if (symbol.startsWith("[") && symbol.endsWith("]")) {
symbol = symbol.substring(1, symbol.length - 1);
this.an[atom] = 18;
this.label[atom] = symbol;
this.nh[atom] = 0;
return;
}if (symbol.length < 1) System.err.println("Error - null atom !");
var isQuery = false;
if (symbol.indexOf(",") > -1) isQuery = true;
if (symbol.indexOf(";") > -1) isQuery = true;
if (symbol.indexOf("#") > -1) isQuery = true;
if (symbol.indexOf("!") > -1) isQuery = true;
var dpos = symbol.indexOf(":");
var hpos = symbol.indexOf("H");
var qpos = Math.max(symbol.indexOf("+"), symbol.indexOf("-"));
if (dpos > -1) {
var smark = symbol.substring(dpos + 1);
try {
this.jme.currentMark = Integer.parseInt(smark);
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
this.jme.currentMark = 0;
} else {
throw e;
}
}
this.touchedAtom = atom;
this.mark();
symbol = symbol.substring(0, dpos);
this.touchedAtom = 0;
}atomProcessing : {
if (isQuery) {
this.label[atom] = symbol;
this.an[atom] = 18;
this.nh[atom] = 0;
break atomProcessing;
}var as = symbol;
if (hpos > 0) as = symbol.substring(0, hpos);
 else if (qpos > 0) as = symbol.substring(0, qpos);
this.an[atom] = jme.JMEmol.checkAtomicSymbol(as);
if (this.an[atom] == 18) this.label[atom] = as;
symbol += " ";
var nhs = 0;
if (hpos > 0) {
nhs = 1;
var c = symbol.charAt(++hpos);
if (c >= '0' && c <= '9') nhs = c.charCodeAt(0) - 48;
}if (this.an[atom] == 18) {
this.nh[atom] = nhs;
}var charge = 0;
if (qpos > 0) {
var c = symbol.charAt(qpos++);
if (c == '+') charge = 1;
 else if (c == '-') charge = -1;
if (charge != 0) {
c = symbol.charAt(qpos++);
if (c >= '0' && c <= '9') c = String.fromCharCode(c.charCodeAt(0)* (c.charCodeAt(0) - 48));
 else {
while (c == '+') {
charge++;
c = symbol.charAt(qpos++);
}
while (c == '-') {
charge--;
c = symbol.charAt(qpos++);
}
}}}this.q[atom] = charge;
}}, "~N,~S");
Clazz.defineMethod(c$, "setAtomHydrogenCount", 
function(atom, nh){
if (this.an[atom] == 18) {
this.label[atom] += "H";
if (nh > 1) this.label[atom] += nh;
}}, "~N,~N");
Clazz.defineMethod(c$, "setAtomFormalCharge", 
function(atom, nq){
this.q[atom] = nq;
}, "~N,~N");
Clazz.defineMethod(c$, "setAtomColors", 
function(s, bg){
this.doColoring = 1;
if (bg) this.doColoring = -1;
var st =  new java.util.StringTokenizer(s, ",");
var atom;
var color;
try {
while (st.hasMoreTokens()) {
atom = Integer.$valueOf(st.nextToken()).intValue();
color = Integer.$valueOf(st.nextToken()).intValue();
this.setAtomColoring(atom, color);
}
} catch (e) {
if (Clazz.exceptionOf(e, Exception)){
System.err.println("Error in atom coloring");
e.printStackTrace();
} else {
throw e;
}
}
}, "~S,~B");
Clazz.defineMethod(c$, "setAtomColoring", 
function(atom, n){
if (n < 0 || n > 6) n = 0;
this.abg[atom] = n;
}, "~N,~N");
Clazz.defineMethod(c$, "createBond", 
function(){
this.nbonds++;
if (this.nbonds > this.nasv.length - 1) {
var storage = this.nasv.length + 10;
var n_va =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.va, 0, n_va, 0, this.va.length);
this.va = n_va;
var n_vb =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.vb, 0, n_vb, 0, this.vb.length);
this.vb = n_vb;
var n_nasv =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.nasv, 0, n_nasv, 0, this.nasv.length);
this.nasv = n_nasv;
var n_stereob =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.stereob, 0, n_stereob, 0, this.stereob.length);
this.stereob = n_stereob;
var n_xb =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.xb, 0, n_xb, 0, this.xb.length);
this.xb = n_xb;
var n_yb =  Clazz.newIntArray (storage, 0);
System.arraycopy(this.yb, 0, n_yb, 0, this.yb.length);
this.yb = n_yb;
var n_btag =  new Array(storage);
System.arraycopy(this.btag, 0, n_btag, 0, this.btag.length);
this.btag = n_btag;
}this.nasv[this.nbonds] = 1;
this.stereob[this.nbonds] = 0;
this.btag[this.nbonds] = null;
});
Clazz.defineMethod(c$, "findBondCenters", 
function(){
for (var i = 1; i <= this.nbonds; i++) {
var atom1 = this.va[i];
var atom2 = this.vb[i];
this.xb[i] = Math.round((this.x[atom1] + this.x[atom2]) / 2.);
this.yb[i] = Math.round((this.y[atom1] + this.y[atom2]) / 2.);
}
});
Clazz.defineMethod(c$, "save", 
function(){
this.jme.smol =  new jme.JMEmol(this);
this.jme.smol.complete();
this.jme.saved = this.jme.actualMolecule;
});
Clazz.defineMethod(c$, "isRotatableBond", 
function(a1, a2){
var i;
var j;
var poradie = 1;
this.a =  Clazz.newIntArray (this.natoms + 1, 0);
for (i = 1; i <= this.natoms; i++) this.a[i] = 0;

this.a[a1] = poradie;
for (i = 1; i <= this.nv[a1]; i++) if (this.v[a1][i] != a2) this.a[this.v[a1][i]] = ++poradie;

var ok = false;
while (true) {
for (i = 1; i <= this.natoms; i++) {
ok = false;
if (this.a[i] > 0 && i != a1) for (j = 1; j <= this.nv[i]; j++) {
if (this.a[this.v[i][j]] == 0) {
this.a[this.v[i][j]] = ++poradie;
ok = true;
}}
if (ok) break;
}
if (!ok) break;
}
return (this.a[a2] == 0);
}, "~N,~N");
Clazz.defineMethod(c$, "findRingBonds", 
function(isRingBond){
for (var i = 1; i <= this.nbonds; i++) if (this.isRotatableBond(this.va[i], this.vb[i])) isRingBond[i] = false;
 else isRingBond[i] = true;

}, "~A");
Clazz.defineMethod(c$, "isInRing", 
function(atom, isRingBond){
for (var i = 1; i <= this.nv[atom]; i++) {
if (isRingBond[this.bondIdentity(atom, this.v[atom][i])]) return true;
}
return false;
}, "~N,~A");
Clazz.defineMethod(c$, "findAromatic", 
function(isAromatic, isRingBond){
this.btype =  Clazz.newIntArray (this.nbonds + 1, 0);
var pa =  Clazz.newBooleanArray(this.natoms + 1, false);
for (var i = 1; i <= this.natoms; i++) {
pa[i] = false;
isAromatic[i] = false;
if (!this.isInRing(i, isRingBond)) continue;
if (this.nv[i] + this.nh[i] > 3) continue;
switch (this.an[i]) {
case 3:
case 4:
case 7:
case 5:
case 8:
case 13:
pa[i] = true;
break;
case 18:
pa[i] = true;
break;
}
}
for (var b = 1; b <= this.nbonds; b++) {
if (this.isSingle(b)) this.btype[b] = 1;
 else if (this.isDouble(b)) this.btype[b] = 2;
 else if (this.nasv[b] == 3) this.btype[b] = 3;
 else System.err.println("problems in findAromatic " + this.nasv[b]);
}
bondloop : for (var b = 1; b <= this.nbonds; b++) {
if (!isRingBond[b]) continue;
var atom1 = this.va[b];
var atom2 = this.vb[b];
if (!pa[atom1] || !pa[atom2]) continue;
var a =  Clazz.newBooleanArray(this.natoms + 1, false);
for (var i = 1; i <= this.nv[atom1]; i++) {
var atom = this.v[atom1][i];
if (atom != atom2 && pa[atom]) a[atom] = true;
}
var ok = false;
while (true) {
for (var i = 1; i <= this.natoms; i++) {
ok = false;
if (a[i] && pa[i] && i != atom1) {
for (var j = 1; j <= this.nv[i]; j++) {
var atom = this.v[i][j];
if (atom == atom2) {
isAromatic[atom1] = true;
isAromatic[atom2] = true;
this.btype[b] = 5;
continue bondloop;
}if (!a[atom] && pa[atom]) {
a[atom] = true;
ok = true;
}}
}if (ok) break;
}
if (!ok) break;
}
}
}, "~A,~A");
Clazz.defineMethod(c$, "canonize", 
function(){
var ok;
var a =  Clazz.newIntArray (this.natoms + 1, 0);
var aold =  Clazz.newIntArray (this.natoms + 1, 0);
var d =  Clazz.newLongArray (this.natoms + 1, 0);
var prime =  Clazz.newLongArray (this.natoms + 2, 0);
prime = jme.JMEmol.generatePrimes(this.natoms);
for (var i = 1; i <= this.natoms; i++) {
var xbo = 1;
for (var j = 1; j <= this.nbonds; j++) {
if (this.va[j] == i || this.vb[j] == i) xbo *= this.btype[j];
}
var xan = this.an[i];
if (xan == 18) {
var zlabel = this.label[i];
var c1 = (zlabel.charAt(0)).charCodeAt(0) - 65 + 1;
var c2 = 0;
if (zlabel.length > 1) c2 = (zlabel.charAt(1)).charCodeAt(0) - 97;
if (c1 < 0) c1 = 0;
if (c2 < 0) c2 = 0;
xan = c1 * 28 + c2;
}var qq = 0;
if (this.q[i] < -2) qq = 1;
 else if (this.q[i] == -2) qq = 2;
 else if (this.q[i] == -1) qq = 3;
 else if (this.q[i] == 1) qq = 4;
 else if (this.q[i] == 2) qq = 5;
 else if (this.q[i] > 2) qq = 6;
var xx = 1;
d[i] = xbo;
xx *= 126;
d[i] += this.nh[i] * xx;
xx *= 7;
d[i] += qq * xx;
xx *= 7;
d[i] += xan * xx;
xx *= 783;
d[i] += this.nv[i] * xx;
}
var breaklevel = 0;
while (true) {
if (this.canonsort(a, d)) break;
ok = false;
for (var i = 1; i <= this.natoms; i++) if (a[i] != aold[i]) {
aold[i] = a[i];
ok = true;
}
if (ok) {
for (var i = 1; i <= this.natoms; i++) {
d[i] = 1;
for (var j = 1; j <= this.nv[i]; j++) d[i] *= prime[a[this.v[i][j]]];

}
breaklevel = 0;
} else {
if (breaklevel > 0) {
for (var i = 1; i <= this.natoms; i++) d[i] = 1;

bd : for (var i = 1; i <= this.natoms - 1; i++) for (var j = i + 1; j <= this.natoms; j++) if (a[i] == a[j]) {
d[i] = 2;
break bd;
}

} else {
for (var i = 1; i <= this.natoms; i++) {
d[i] = 1;
for (var j = 1; j <= this.nv[i]; j++) {
var atom = this.v[i][j];
d[i] *= this.an[atom] * this.btype[this.bondIdentity(i, atom)];
}
}
breaklevel = 1;
}}this.canonsort(a, d);
for (var i = 1; i <= this.natoms; i++) d[i] = aold[i] * this.natoms + a[i];

}
for (var i = 1; i <= this.natoms; i++) aold[i] = a[i];

for (var s = 1; s <= this.natoms; s++) {
for (var i = 1; i <= this.natoms; i++) {
if (aold[i] == s) {
this.an[0] = this.an[i];
this.q[0] = this.q[i];
this.x[0] = this.x[i];
this.y[0] = this.y[i];
this.nv[0] = this.nv[i];
this.an[i] = this.an[s];
this.q[i] = this.q[s];
this.x[i] = this.x[s];
this.y[i] = this.y[s];
this.nv[i] = this.nv[s];
this.an[s] = this.an[0];
this.q[s] = this.q[0];
this.x[s] = this.x[0];
this.y[s] = this.y[0];
this.nv[s] = this.nv[0];
aold[i] = aold[s];
aold[s] = s;
this.label[0] = this.label[i];
this.label[i] = this.label[s];
this.label[s] = this.label[0];
this.abg[0] = this.abg[i];
this.abg[i] = this.abg[s];
this.abg[s] = this.abg[0];
this.atag[0] = this.atag[i];
this.atag[i] = this.atag[s];
this.atag[s] = this.atag[0];
this.nh[0] = this.nh[i];
this.nh[i] = this.nh[s];
this.nh[s] = this.nh[0];
break;
}}
}
for (var i = 1; i <= this.nmarked; i++) this.$mark[i][0] = a[this.$mark[i][0]];

for (var i = 1; i <= this.nbonds; i++) {
this.va[i] = a[this.va[i]];
this.vb[i] = a[this.vb[i]];
if (this.va[i] > this.vb[i]) {
var du = this.va[i];
this.va[i] = this.vb[i];
this.vb[i] = du;
if (this.stereob[i] == 1) this.stereob[i] = 3;
 else if (this.stereob[i] == 2) this.stereob[i] = 4;
 else if (this.stereob[i] == 3) this.stereob[i] = 1;
 else if (this.stereob[i] == 4) this.stereob[i] = 2;
}}
for (var i = 1; i < this.nbonds; i++) {
var minva = this.natoms;
var minvb = this.natoms;
var b = 0;
for (var j = i; j <= this.nbonds; j++) {
if (this.va[j] < minva) {
minva = this.va[j];
minvb = this.vb[j];
b = j;
} else if (this.va[j] == minva && this.vb[j] < minvb) {
minvb = this.vb[j];
b = j;
}}
var du;
du = this.va[i];
this.va[i] = this.va[b];
this.va[b] = du;
du = this.vb[i];
this.vb[i] = this.vb[b];
this.vb[b] = du;
du = this.nasv[i];
this.nasv[i] = this.nasv[b];
this.nasv[b] = du;
du = this.stereob[i];
this.stereob[i] = this.stereob[b];
this.stereob[b] = du;
var ds = this.btag[i];
this.btag[i] = this.btag[b];
this.btag[b] = ds;
}
this.complete();
});
Clazz.defineMethod(c$, "canonsort", 
function(a, d){
var min = 0;
var nth = 0;
var ndone = 0;
while (true) {
nth++;
for (var i = 1; i <= this.natoms; i++) if (d[i] > 0) {
min = d[i];
break;
}
for (var i = 1; i <= this.natoms; i++) if (d[i] > 0 && d[i] < min) min = d[i];

for (var i = 1; i <= this.natoms; i++) if (d[i] == min) {
a[i] = nth;
d[i] = 0;
ndone++;
}
if (ndone == this.natoms) break;
}
return (nth == this.natoms);
}, "~A,~A");
Clazz.defineMethod(c$, "cleanPolarBonds", 
function(){
for (var i = 1; i <= this.nbonds; i++) {
var atom1 = this.va[i];
var atom2 = this.vb[i];
if ((this.q[atom1] == 1 && this.q[atom2] == -1) || (this.q[atom1] == -1 && this.q[atom2] == 1)) {
if (this.nasv[i] == 1 || this.nasv[i] == 2) {
if (this.an[atom1] != 3 && this.an[atom2] != 3 && this.jme.polarnitro) continue;
if (this.an[atom1] == 1 || this.an[atom2] == 1) continue;
if (this.an[atom1] == 2 || this.an[atom2] == 2) continue;
if (this.an[atom1] == 9 || this.an[atom1] == 10 || this.an[atom1] == 11 || this.an[atom1] == 12 || this.an[atom2] == 9 || this.an[atom2] == 10 || this.an[atom2] == 11 || this.an[atom2] == 12) continue;
this.q[atom1] = 0;
this.q[atom2] = 0;
this.nasv[i]++;
this.valenceState();
}}if (this.q[atom1] == 1 && this.q[atom2] == 1) {
if (this.nasv[i] == 2) this.nasv[i] = 1;
 else if (this.nasv[i] == 3) this.nasv[i] = 2;
this.valenceState();
}if (this.nasv[i] == 4) this.nasv[i] = 1;
}
});
Clazz.defineMethod(c$, "fillFields", 
function(){
var storage = this.an.length;
this.v =  Clazz.newIntArray (storage, 7, 0);
this.nv =  Clazz.newIntArray (storage, 0);
for (var i = 1; i <= this.natoms; i++) this.nv[i] = 0;

for (var i = 1; i <= this.nbonds; i++) {
if (this.nv[this.va[i]] < 6) this.v[this.va[i]][++this.nv[this.va[i]]] = this.vb[i];
if (this.nv[this.vb[i]] < 6) this.v[this.vb[i]][++this.nv[this.vb[i]]] = this.va[i];
}
});
Clazz.defineMethod(c$, "checkMultipart", 
function(removeSmall){
var nparts = 0;
var ok = false;
this.a =  Clazz.newIntArray (this.natoms + 1, 0);
while (true) {
for (var j = 1; j <= this.natoms; j++) if (this.a[j] == 0) {
this.a[j] = ++nparts;
ok = true;
break;
}
if (!ok) break;
while (ok) {
ok = false;
for (var j = 1; j <= this.nbonds; j++) {
var atom1 = this.va[j];
var atom2 = this.vb[j];
if (this.a[atom1] > 0 && this.a[atom2] == 0) {
this.a[atom2] = nparts;
ok = true;
} else if (this.a[atom2] > 0 && this.a[atom1] == 0) {
this.a[atom1] = nparts;
ok = true;
}}
}
}
if (nparts < 2 || !removeSmall) return nparts;
var size =  Clazz.newIntArray (nparts + 1, 0);
for (var i = 1; i <= this.natoms; i++) size[this.a[i]]++;

var max = 0;
var largest = 1;
for (var i = 1; i <= nparts; i++) if (size[i] > max) {
max = size[i];
largest = i;
}
for (var i = this.natoms; i >= 1; i--) if (this.a[i] != largest) this.deleteAtom(i);

this.center();
this.jme.info("Smaller part(s) removed !");
return 1;
}, "~B");
Clazz.defineMethod(c$, "createSmiles", 
function(){
var con1 =  Clazz.newIntArray (this.natoms + 10, 0);
var con2 =  Clazz.newIntArray (this.natoms + 10, 0);
var branch =  Clazz.newIntArray (this.natoms + 1, 0);
var candidate =  Clazz.newIntArray (7, 0);
var parent =  Clazz.newIntArray (this.natoms + 1, 0);
var isAromatic =  Clazz.newBooleanArray(this.natoms + 1, false);
var isRingBond =  Clazz.newBooleanArray(this.nbonds + 1, false);
var nconnections = 0;
if (this.natoms == 0) return "";
this.checkMultipart(true);
var noQueryBonds = true;
for (var b = 1; b <= this.nbonds; b++) {
if (this.nasv[b] == 9) {
noQueryBonds = false;
break;
}}
if (this.jme.canonize && noQueryBonds) {
this.deleteHydrogens();
this.cleanPolarBonds();
this.findRingBonds(isRingBond);
this.findAromatic(isAromatic, isRingBond);
this.canonize();
this.valenceState();
this.findRingBonds(isRingBond);
this.findAromatic(isAromatic, isRingBond);
} else {
this.findRingBonds(isRingBond);
this.btype =  Clazz.newIntArray (this.nbonds + 1, 0);
for (var i = 1; i <= this.nbonds; i++) this.btype[i] = this.nasv[i];

}var atom = 1;
this.a =  Clazz.newIntArray (this.natoms + 1, 0);
var step = 1;
this.a[atom] = step;
var nbranch = 0;
while (true) {
var ncandidates = 0;
for (var i = 1; i <= this.nv[atom]; i++) {
var atomx = this.v[atom][i];
if (this.a[atomx] > 0) {
if (this.a[atomx] > this.a[atom]) continue;
if (atomx == parent[atom]) continue;
var newcon = true;
for (var k = 1; k <= nconnections; k++) if (con1[k] == atom && con2[k] == atomx || con1[k] == atomx && con2[k] == atom) {
newcon = false;
break;
}
if (newcon) {
nconnections++;
con1[nconnections] = atom;
con2[nconnections] = atomx;
}} else candidate[++ncandidates] = atomx;
}
if (ncandidates == 0) {
if (step == this.natoms) break;
atom = branch[nbranch--];
} else if (ncandidates == 1) {
parent[candidate[1]] = atom;
atom = candidate[1];
this.a[atom] = ++step;
} else {
branch[++nbranch] = atom;
var atomnew = 0;
for (var i = 1; i <= ncandidates; i++) {
var b = this.bondIdentity(candidate[i], atom);
if (isRingBond[b]) continue;
atomnew = candidate[i];
break;
}
if (atomnew == 0) {
for (var i = 1; i <= ncandidates; i++) {
var b = this.bondIdentity(candidate[i], atom);
if (this.btype[b] == 2 || this.btype[b] == 3) {
atomnew = candidate[i];
break;
}}
}if (atomnew == 0) atomnew = candidate[1];
parent[atomnew] = atom;
atom = atomnew;
this.a[atom] = ++step;
}}
parent =  Clazz.newIntArray (this.natoms + 1, 0);
var aa =  Clazz.newIntArray (this.natoms + 1, 0);
var leftBracket =  Clazz.newBooleanArray(this.natoms + 1, false);
var rightBracket =  Clazz.newBooleanArray(this.natoms + 1, false);
nbranch = 0;
step = 0;
var atomold = 0;
for (var i = 1; i <= this.natoms; i++) if (this.a[i] == 1) {
atom = i;
break;
}
loopTwo : while (true) {
if (atomold > 0) parent[atom] = atomold;
aa[++step] = atom;
this.a[atom] = 0;
var atomnew;
var ncandidates;
while (true) {
atomnew = 0;
ncandidates = 0;
var min = this.natoms + 1;
cs1 : for (var i = 1; i <= this.nv[atom]; i++) {
var atomx = this.v[atom][i];
for (var j = 1; j <= nconnections; j++) if (con1[j] == atomx && con2[j] == atom || con1[j] == atom && con2[j] == atomx) continue cs1;

if (this.a[atomx] > 0) {
ncandidates++;
if (this.a[atomx] < min) {
atomnew = atomx;
min = this.a[atomx];
}}}
if (atomnew == 0) {
if (nbranch == 0) break loopTwo;
rightBracket[atom] = true;
atom = branch[nbranch--];
} else break;
}
atomold = atom;
atom = atomnew;
if (ncandidates > 1) {
branch[++nbranch] = atomold;
leftBracket[atom] = true;
}}
var slashBond =  Clazz.newIntArray (this.nbonds + 1, 0);
var slimak =  Clazz.newIntArray (this.natoms + 1, 0);
if (this.jme.stereo) this.smilesStereo(aa, parent, slashBond, slimak, isRingBond, con1, con2, nconnections);
var queryMode = false;
var smiles =  new JU.SB();
var ax =  Clazz.newIntArray (this.natoms + 1, 0);
for (var i = 1; i <= this.natoms; i++) ax[aa[i]] = i;

for (var i = 1; i <= this.natoms; i++) {
atom = aa[i];
if (leftBracket[atom]) smiles.append("(");
if (parent[i] > 0) this.smilesAddBond(atom, parent[atom], smiles, slashBond, queryMode);
this.smilesAddAtom(atom, smiles, isAromatic[atom], slimak);
for (var j = 1; j <= nconnections; j++) {
if (con1[j] == atom || con2[j] == atom) {
var atom2 = con2[j];
if (atom2 == atom) atom2 = con1[j];
if (ax[atom] < ax[atom2]) this.smilesAddBond(con1[j], con2[j], smiles, slashBond, queryMode);
if (j > 9) smiles.append("%");
smiles.append( new Integer(j).toString());
}}
if (rightBracket[atom]) smiles.append(")");
}
return smiles.toString();
});
Clazz.defineMethod(c$, "smilesAddAtom", 
function(atom, smiles, isAromatic, slimak){
var z = "X";
var bracket = false;
if (this.q[atom] != 0) bracket = true;
if (slimak[atom] != 0) bracket = true;
var lmark = -1;
for (var i = 1; i <= this.nmarked; i++) if (this.$mark[i][0] == atom) {
lmark = this.$mark[i][1];
break;
}
if (lmark > -1) bracket = true;
if (this.jme.allHs) bracket = true;
if (this.jme.star && this.abg[atom] > 0) {
bracket = true;
lmark = 1;
}switch (this.an[atom]) {
case 2:
z = "B";
break;
case 3:
if (isAromatic) z = "c";
 else z = "C";
break;
case 4:
if (isAromatic) {
z = "n";
if (this.nh[atom] > 0) bracket = true;
} else z = "N";
break;
case 5:
if (isAromatic) z = "o";
 else z = "O";
break;
case 7:
if (isAromatic) {
z = "p";
if (this.nh[atom] > 0) bracket = true;
} else z = "P";
break;
case 8:
if (isAromatic) z = "s";
 else z = "S";
break;
case 13:
if (isAromatic) z = "se";
 else z = "Se";
bracket = true;
break;
case 6:
z = "Si";
bracket = true;
break;
case 9:
z = "F";
break;
case 10:
z = "Cl";
break;
case 11:
z = "Br";
break;
case 12:
z = "I";
break;
case 1:
z = "H";
bracket = true;
break;
case 19:
z = "R";
bracket = true;
break;
case 20:
z = "R1";
bracket = true;
break;
case 21:
z = "R2";
bracket = true;
break;
case 22:
z = "R3";
bracket = true;
break;
case 18:
bracket = true;
z = this.label[atom];
if (z.equals("*") || z.equals("a") || z.equals("A")) bracket = false;
break;
}
if (bracket) {
z = "[" + z;
if (slimak[atom] == 1) z += "@";
 else if (slimak[atom] == -1) z += "@@";
if (this.nh[atom] == 1) z += "H";
 else if (this.nh[atom] > 1) z += "H" + this.nh[atom];
if (this.q[atom] != 0) {
if (this.q[atom] > 0) z += "+";
 else z += "-";
if (Math.abs(this.q[atom]) > 1) z += Math.abs(this.q[atom]);
}if (lmark > -1) z += ":" + lmark;
z += "]";
}smiles.append(z);
}, "~N,JU.SB,~B,~A");
Clazz.defineMethod(c$, "smilesAddBond", 
function(atom1, atom2, smiles, slashBond, queryMode){
var b = this.bondIdentity(atom1, atom2);
if (this.btype[b] != 5 && this.isDouble(b)) smiles.append("=");
 else if (this.nasv[b] == 3) smiles.append("#");
 else if (this.nasv[b] == 9) {
var z = "?";
var o = this.btag[b];
if (o != null) z = o;
smiles.append(z);
} else if (this.btype[b] == 5 && queryMode) smiles.append(":");
 else if (slashBond[b] == 1) smiles.append("/");
 else if (slashBond[b] == -1) smiles.append("\\");
}, "~N,~N,JU.SB,~A,~B");
Clazz.defineMethod(c$, "smilesStereo", 
function(aa, parent, slashBond, slimak, isRingBond, con1, con2, nconnections){
var ax =  Clazz.newIntArray (this.natoms + 1, 0);
for (var i = 1; i <= this.natoms; i++) ax[aa[i]] = i;

var doneEZ =  Clazz.newBooleanArray(this.nbonds + 1, false);
for (var i = 1; i <= this.natoms; i++) {
var atom1 = aa[i];
var atom2 = parent[atom1];
var bi = this.bondIdentity(atom1, atom2);
if (bi == 0) continue;
this.stereoEZ(bi, ax, slashBond, isRingBond);
doneEZ[bi] = true;
}
for (var i = 1; i <= this.nbonds; i++) {
if (!doneEZ[i]) this.stereoEZ(i, ax, slashBond, isRingBond);
}
doneEZ = null;
iloop : for (var i = 1; i <= this.natoms; i++) {
if (this.nv[i] < 2 || this.nv[i] > 4) continue;
var nstereo = 0;
var doubleBonded = 0;
for (var j = 1; j <= this.nv[i]; j++) {
var bi = this.bondIdentity(i, this.v[i][j]);
if (this.btype[bi] == 5) continue iloop;
if (this.nasv[bi] == 1 && this.upDownBond(bi, i) != 0) nstereo++;
if (this.nasv[bi] == 2) doubleBonded = this.v[i][j];
}
if (nstereo == 0) continue;
if (doubleBonded > 0) this.stereoAllene(i, ax, slimak, parent, con1, con2, nconnections);
 else this.stereoC4(i, parent, ax, con1, con2, nconnections, slimak);
}
}, "~A,~A,~A,~A,~A,~A,~A,~N");
Clazz.defineMethod(c$, "stereoC4", 
function(atom, parent, ax, con1, con2, nconnections, slimak){
var ref =  Clazz.newIntArray (4, 0);
var refx =  Clazz.newIntArray (4, 0);
this.identifyNeighbors(atom, ax, parent, con1, con2, nconnections, ref);
var nup = 0;
var ndown = 0;
var up = 0;
var down = 0;
var marked = 0;
var nonmarked = 0;
for (var i = 0; i < 4; i++) {
if (ref[i] <= 0) continue;
var bi = this.bondIdentity(atom, ref[i]);
refx[i] = this.upDownBond(bi, atom);
if (refx[i] > 0) {
nup++;
up = ref[i];
marked = ref[i];
} else if (refx[i] < 0) {
ndown++;
down = ref[i];
marked = ref[i];
} else nonmarked = ref[i];
}
var nstereo = nup + ndown;
var ox;
var t =  Clazz.newIntArray (4, 0);
var stereoRef = 0;
if (this.nv[atom] == 3) {
if ((nup == 1 && ndown == 1) || (nstereo == 3 && nup > 0 && ndown > 0)) {
this.jme.info("Error in C3H stereospecification !");
return;
}var refAtom = ref[0];
if (nstereo == 1) refAtom = marked;
 else if (nstereo == 2) refAtom = nonmarked;
ox = this.C4order(atom, refAtom, ref);
t[0] = marked;
t[1] = -1;
t[2] = ox[2];
t[3] = ox[1];
if (nup > 0) stereoRef = 1;
 else stereoRef = -1;
} else if (this.nv[atom] == 4) {
if (nstereo == 1) {
ox = this.C4order(atom, marked, ref);
t[0] = ox[0];
t[1] = ox[3];
t[2] = ox[2];
t[3] = ox[1];
if (nup > 0) stereoRef = 1;
 else stereoRef = -1;
} else {
var refAtom = ref[0];
if (nonmarked > 1) refAtom = nonmarked;
if (nup == 1) refAtom = up;
 else if (ndown == 1) refAtom = down;
ox = this.C4order(atom, refAtom, ref);
var box =  Clazz.newIntArray (4, 0);
for (var i = 0; i < 4; i++) {
var bi = this.bondIdentity(atom, ox[i]);
box[i] = this.upDownBond(bi, atom);
}
if (nstereo == 4) {
if (nup == 0 || ndown == 0) {
this.jme.info("Error in C4 stereospecification !");
return;
} else if (nup == 1 || ndown == 1) {
t[0] = ox[0];
t[1] = ox[3];
t[2] = ox[2];
t[3] = ox[1];
stereoRef = box[0];
} else {
for (var i = 0; i < 4; i++) if (box[i] == -1) box[i] = 0;

nstereo = 2;
}} else if (nstereo == 3) {
if (nup == 3 || ndown == 3) {
t[0] = ox[0];
t[1] = ox[3];
t[2] = ox[2];
t[3] = ox[1];
if (nup > 0) stereoRef = -1;
 else stereoRef = 1;
} else {
var d = 0;
if (nup == 1) {
d = 1;
nup = 1;
} else {
d = -1;
ndown = -1;
}for (var i = 0; i < 4; i++) if (box[i] == d) box[i] = 0;

nstereo = 2;
}}if (nstereo == 2) {
if (nup == 1 && ndown == 1) {
if (ox[1] == down) {
ox[1] = ox[2];
ox[2] = ox[3];
} else if (ox[2] == down) {
ox[2] = ox[3];
}t[0] = up;
t[1] = down;
t[2] = ox[2];
t[3] = ox[1];
stereoRef = 1;
} else {
if ((box[0] == box[1]) || (box[1] == box[2])) {
this.jme.info("Error in C4 stereospecification ! 2/0r");
return;
}if (box[0] != 0) {
t[0] = ox[0];
t[1] = ox[2];
t[2] = ox[1];
t[3] = ox[3];
} else {
t[0] = ox[1];
t[1] = ox[3];
t[2] = ox[2];
t[3] = ox[0];
}if (nup > 1) stereoRef = 1;
 else stereoRef = -1;
}}}}this.stereoTransformation(t, ref);
if (t[2] == ref[2]) slimak[atom] = 1;
 else if (t[2] == ref[3]) slimak[atom] = -1;
 else this.jme.info("Error in stereoprocessing ! - t30");
slimak[atom] *= stereoRef;
}, "~N,~A,~A,~A,~A,~N,~A");
Clazz.defineMethod(c$, "identifyNeighbors", 
function(atom, ax, parent, con1, con2, nconnections, ref){
var nref = -1;
if (parent[atom] > 0) ref[++nref] = parent[atom];
for (var i = 1; i <= nconnections; i++) {
if (con1[i] == atom) ref[++nref] = con2[i];
if (con2[i] == atom) ref[++nref] = con1[i];
}
for (var i = nref + 1; i < this.nv[atom]; i++) {
var min = this.natoms + 1;
jloop : for (var j = 1; j <= this.nv[atom]; j++) {
var atomx = this.v[atom][j];
for (var k = 0; k < i; k++) if (atomx == ref[k]) continue jloop;

if (ax[atomx] < min) {
min = ax[atomx];
ref[i] = atomx;
}}
}
if (parent[atom] == 0 && this.nh[atom] > 0) {
ref[3] = ref[2];
ref[2] = ref[1];
ref[1] = ref[0];
ref[0] = -1;
System.out.println("stereowarning #7");
} else if (this.nh[atom] > 0) {
ref[3] = ref[2];
ref[2] = ref[1];
ref[1] = -1;
}}, "~N,~A,~A,~A,~A,~N,~A");
Clazz.defineMethod(c$, "C4order", 
function(center, ref0, ref){
var ox =  Clazz.newIntArray (4, 0);
var dx;
var dy;
var rx;
dx = this.x[ref0] - this.x[center];
dy = this.y[ref0] - this.y[center];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
var sin0 = dy / rx;
var cos0 = dx / rx;
var p =  Clazz.newIntArray (4, 0);
for (var i = 0; i < 4; i++) {
if (ref[i] == ref0 || ref[i] <= 0) continue;
if (p[1] == 0) {
p[1] = ref[i];
continue;
}if (p[2] == 0) {
p[2] = ref[i];
continue;
}if (p[3] == 0) {
p[3] = ref[i];
continue;
}}
var sin =  Clazz.newDoubleArray (4, 0);
var cos =  Clazz.newDoubleArray (4, 0);
for (var i = 1; i <= 3; i++) {
if (i == 3 && p[3] == 0) continue;
dx = (this.x[p[i]] - this.x[center]) * cos0 + (this.y[p[i]] - this.y[center]) * sin0;
dy = (this.y[p[i]] - this.y[center]) * cos0 - (this.x[p[i]] - this.x[center]) * sin0;
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sin[i] = dy / rx;
cos[i] = dx / rx;
}
var c12 = this.compareAngles(sin[1], cos[1], sin[2], cos[2]);
if (p[3] > 0) {
var c23 = this.compareAngles(sin[2], cos[2], sin[3], cos[3]);
var c13 = this.compareAngles(sin[1], cos[1], sin[3], cos[3]);
if (c12 > 0 && c23 > 0) {
ox[1] = p[1];
ox[2] = p[2];
ox[3] = p[3];
} else if (c13 > 0 && c23 < 0) {
ox[1] = p[1];
ox[2] = p[3];
ox[3] = p[2];
} else if (c12 < 0 && c13 > 0) {
ox[1] = p[2];
ox[2] = p[1];
ox[3] = p[3];
} else if (c23 > 0 && c13 < 0) {
ox[1] = p[2];
ox[2] = p[3];
ox[3] = p[1];
} else if (c13 < 0 && c12 > 0) {
ox[1] = p[3];
ox[2] = p[1];
ox[3] = p[2];
} else if (c23 < 0 && c12 < 0) {
ox[1] = p[3];
ox[2] = p[2];
ox[3] = p[1];
}} else {
if (c12 > 0) {
ox[1] = p[1];
ox[2] = p[2];
} else {
ox[1] = p[2];
ox[2] = p[1];
}}ox[0] = ref0;
return ox;
}, "~N,~N,~A");
Clazz.defineMethod(c$, "stereoTransformation", 
function(t, ref){
var d = 0;
if (ref[0] == t[1]) {
d = t[0];
t[0] = t[1];
t[1] = d;
d = t[2];
t[2] = t[3];
t[3] = d;
} else if (ref[0] == t[2]) {
d = t[2];
t[2] = t[0];
t[0] = d;
d = t[1];
t[1] = t[3];
t[3] = d;
} else if (ref[0] == t[3]) {
d = t[3];
t[3] = t[0];
t[0] = d;
d = t[1];
t[1] = t[2];
t[2] = d;
}if (ref[1] == t[2]) {
d = t[1];
t[1] = t[2];
t[2] = d;
d = t[2];
t[2] = t[3];
t[3] = d;
} else if (ref[1] == t[3]) {
d = t[1];
t[1] = t[3];
t[3] = d;
d = t[2];
t[2] = t[3];
t[3] = d;
}}, "~A,~A");
Clazz.defineMethod(c$, "stereoEZ", 
function(bond, ax, slashBond, isRingBond){
if (this.nasv[bond] != 2 || this.btype[bond] == 5) return;
if (!(this.stereob[bond] == 10 || (this.jme.autoez && !isRingBond[bond]))) return;
var atom1 = this.va[bond];
var atom2 = this.vb[bond];
if (this.nv[atom1] < 2 || this.nv[atom2] < 2 || this.nv[atom1] > 3 || this.nv[atom2] > 3) return;
if (ax[atom1] > ax[atom2]) {
var d = atom1;
atom1 = atom2;
atom2 = d;
}var ref1 = 0;
var ref11 = 0;
var ref12 = 0;
var ref1x = false;
for (var j = 1; j <= this.nv[atom1]; j++) {
var atomx = this.v[atom1][j];
if (atomx == atom2) continue;
if (ref11 == 0) ref11 = atomx;
 else ref12 = atomx;
}
if (ref12 > 0 && ax[ref11] > ax[ref12]) {
var d = ref11;
ref11 = ref12;
ref12 = d;
}var bi = this.bondIdentity(atom1, ref11);
if (slashBond[bi] != 0) {
ref1 = ref11;
} else if (this.nasv[bi] == 1 && this.btype[bi] != 5) ref1 = ref11;
if (ref1 == 0) {
bi = this.bondIdentity(atom1, ref12);
if (slashBond[bi] != 0) ref1 = ref12;
 else if (this.nasv[bi] == 1 && this.btype[bi] != 5) ref1 = ref12;
}if (ax[ref1] > ax[atom1]) ref1x = true;
var ref2 = 0;
var ref21 = 0;
var ref22 = 0;
for (var j = 1; j <= this.nv[atom2]; j++) {
var atomx = this.v[atom2][j];
if (atomx == atom1) continue;
if (ref21 == 0) ref21 = atomx;
 else ref22 = atomx;
}
if (ref22 > 0 && ax[ref21] < ax[ref22]) {
var d = ref21;
ref21 = ref22;
ref22 = d;
}bi = this.bondIdentity(atom2, ref21);
if (this.nasv[bi] == 1 && this.btype[bi] != 5 && slashBond[bi] == 0) ref2 = ref21;
if (ref2 == 0) {
bi = this.bondIdentity(atom2, ref22);
if (this.nasv[bi] == 1 && this.btype[bi] != 5) ref2 = ref22;
}if (ref1 == 0 || ref2 == 0) return;
var dx = this.x[atom2] - this.x[atom1];
var dy = this.y[atom2] - this.y[atom1];
var rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
var sina = dy / rx;
var cosa = dx / rx;
var y1 = (this.y[ref1] - this.y[atom1]) * cosa - (this.x[ref1] - this.x[atom1]) * sina;
var y2 = (this.y[ref2] - this.y[atom1]) * cosa - (this.x[ref2] - this.x[atom1]) * sina;
if (Math.abs(y1) < 2 || Math.abs(y2) < 2) {
this.jme.info("Not unique E/Z geometry !");
return;
}var b1 = this.bondIdentity(ref1, atom1);
var b2 = this.bondIdentity(ref2, atom2);
var newSlash = 1;
if (slashBond[b1] == 0) {
for (var j = 1; j <= this.nv[ref1]; j++) {
var atomx = this.v[ref1][j];
if (atomx == atom1) continue;
bi = this.bondIdentity(ref1, atomx);
if (slashBond[bi] != 0) {
if (ax[atomx] > ax[ref1]) newSlash = -slashBond[bi];
 else newSlash = slashBond[bi];
break;
}}
slashBond[b1] = newSlash;
}if (slashBond[b2] != 0) {
System.err.println("E/Z internal error !");
return;
}if ((y1 > 0 && y2 > 0) || (y1 < 0 && y2 < 0)) slashBond[b2] = -slashBond[b1];
 else slashBond[b2] = slashBond[b1];
if (ref1x) slashBond[b2] = -slashBond[b2];
}, "~N,~A,~A,~A");
Clazz.defineMethod(c$, "compareAngles", 
function(sina, cosa, sinb, cosb){
var qa = 0;
var qb = 0;
if (sina >= 0. && cosa >= 0.) qa = 1;
 else if (sina >= 0. && cosa < 0.) qa = 2;
 else if (sina < 0. && cosa < 0.) qa = 3;
 else if (sina < 0. && cosa >= 0.) qa = 4;
if (sinb >= 0. && cosb >= 0.) qb = 1;
 else if (sinb >= 0. && cosb < 0.) qb = 2;
 else if (sinb < 0. && cosb < 0.) qb = 3;
 else if (sinb < 0. && cosb >= 0.) qb = 4;
if (qa < qb) return 1;
 else if (qa > qb) return -1;
switch (qa) {
case 1:
case 4:
return (sina < sinb ? 1 : -1);
case 2:
case 3:
return (sina > sinb ? 1 : -1);
}
System.err.println("stereowarning #31");
return 0;
}, "~N,~N,~N,~N");
Clazz.defineMethod(c$, "upDownBond", 
function(bond, atom){
var sb = this.stereob[bond];
if (sb < 1 || sb > 4) return 0;
if (sb == 1 && this.va[bond] == atom) return 1;
if (sb == 2 && this.va[bond] == atom) return -1;
if (sb == 3 && this.vb[bond] == atom) return 1;
if (sb == 4 && this.vb[bond] == atom) return -1;
return 0;
}, "~N,~N");
Clazz.defineMethod(c$, "stereoAllene", 
function(i, ax, slimak, parent, con1, con2, nconnections){
var dx;
var dy;
var rx;
var sina;
var cosa;
var nal = 1;
var ala = i;
var al =  Clazz.newIntArray (this.natoms + 1, 0);
al[1] = i;
while (true) {
var ok = false;
for (var j = 1; j <= this.nv[ala]; j++) {
var atomx = this.v[ala][j];
if (atomx == al[1] || atomx == al[nal - 1]) continue;
var bi = this.bondIdentity(ala, atomx);
if (this.nasv[bi] == 2 && this.btype[bi] != 5) {
al[++nal] = atomx;
ala = atomx;
ok = true;
break;
}}
if (!ok) break;
}
if (nal % 2 == 0) return;
if (this.nv[al[nal]] < 2 || this.nv[al[nal]] > 3) return;
var start = al[1];
var center = al[Clazz.doubleToInt((nal + 1) / 2)];
var end = al[nal];
var ref11 = 0;
var ref12 = 0;
var ref21 = 0;
var ref22 = 0;
var ref1 = 0;
var ref2 = 0;
var ref1x = false;
var ref2x = false;
for (var j = 1; j <= this.nv[start]; j++) {
var atomx = this.v[start][j];
var bi = this.bondIdentity(start, atomx);
if (this.nasv[bi] != 1 || this.btype[bi] == 5) continue;
if (ref11 == 0) ref11 = atomx;
 else ref12 = atomx;
}
if (ax[ref12] > 0 && ax[ref11] > ax[ref12]) {
var d = ref11;
ref11 = ref12;
ref12 = d;
}ref1 = ref11;
if (ref1 == 0) {
ref1 = ref12;
ref1x = true;
}for (var j = 1; j <= this.nv[end]; j++) {
var atomx = this.v[end][j];
var bi = this.bondIdentity(end, atomx);
if (this.nasv[bi] != 1 || this.btype[bi] == 5) continue;
if (ref21 == 0) ref21 = atomx;
 else ref22 = atomx;
}
if (ax[ref22] > 0 && ax[ref21] > ax[ref22]) {
var d = ref21;
ref21 = ref22;
ref22 = d;
}ref2 = ref21;
if (ref2 == 0) {
ref2 = ref22;
ref2x = true;
}var ref11x = this.upDownBond(this.bondIdentity(start, ref11), start);
var ref12x = this.upDownBond(this.bondIdentity(start, ref12), start);
var ref21x = this.upDownBond(this.bondIdentity(end, ref21), end);
var ref22x = this.upDownBond(this.bondIdentity(end, ref22), end);
if (Math.abs(ref11x + ref12x) > 1 || ref21x != 0 || ref22x != 0) {
this.jme.info("Bad stereoinfo on allene !");
return;
}dx = this.x[al[nal - 1]] - this.x[end];
dy = this.y[al[nal - 1]] - this.y[end];
rx = Math.sqrt(dx * dx + dy * dy);
if (rx < 0.001) rx = 0.001;
sina = dy / rx;
cosa = dx / rx;
var y2 = (this.y[ref2] - this.y[al[nal - 1]]) * cosa - (this.x[ref2] - this.x[al[nal - 1]]) * sina;
if (y2 > 0) slimak[center] = 1;
 else slimak[center] = -1;
if (ref1x) slimak[center] *= -1;
if (ref2x) slimak[center] *= -1;
if (ref1 == ref11 && ref11x < 0) slimak[center] *= -1;
if (ref1 == ref12 && ref12x < 0) slimak[center] *= -1;
if (ax[ref1] > ax[ref2]) slimak[center] *= -1;
}, "~N,~A,~A,~A,~A,~A,~N");
Clazz.defineMethod(c$, "createJME", 
function(){
var s = "" + this.natoms + " " + this.nbonds;
var scale = 0.055999999999999994;
for (var i = 1; i <= this.natoms; i++) {
var z = this.getAtomLabel(i);
if (this.jme.jmeh && this.nh[i] > 0) {
z += "H";
if (this.nh[i] > 1) z += this.nh[i];
}if (this.q[i] != 0) {
if (this.q[i] > 0) z += "+";
 else z += "-";
if (Math.abs(this.q[i]) > 1) z += Math.abs(this.q[i]);
}var lmark = -1;
for (var j = 1; j <= this.nmarked; j++) if (this.$mark[j][0] == i) {
lmark = this.$mark[j][1];
break;
}
if (this.jme.star && this.abg[i] > 0) lmark = 1;
if (lmark > -1) z += ":" + lmark;
s += " " + z + " " + jme.JMEmol.fformat(this.x[i] * scale, 0, 2) + " " + jme.JMEmol.fformat(-this.y[i] * scale, 0, 2);
}
for (var i = 1; i <= this.nbonds; i++) {
var a1 = this.va[i];
var a2 = this.vb[i];
var nas = this.nasv[i];
if (this.stereob[i] == 1) nas = -1;
 else if (this.stereob[i] == 2) nas = -2;
 else if (this.stereob[i] == 3) {
nas = -1;
var d = a1;
a1 = a2;
a2 = d;
} else if (this.stereob[i] == 4) {
nas = -2;
var d = a1;
a1 = a2;
a2 = d;
} else if (this.stereob[i] == 10) {
nas = -5;
}if (this.nasv[i] == 9) nas = this.stereob[i];
s += " " + a1 + " " + a2 + " " + nas;
}
return s;
});
Clazz.defineMethod(c$, "createMolFile", 
function(title){
if (this.natoms == 0) return "";
var s = "";
s = title;
if (s.length > 79) s = s.substring(0, 76) + "...";
s += "\n";
s += JV.PropertyManager.getSDFDateLine("JME2023.01", true);
s += "JME " + "2023.01" + " " +  new java.util.Date() + "\n";
s += jme.JMEmol.iformat(this.natoms, 3) + jme.JMEmol.iformat(this.nbonds, 3);
s += "  0  0  0  0  0  0  0  0999 V2000\n";
var scale = 0.055999999999999994;
var ymax = -1.7976931348623157E308;
var xmin = 1.7976931348623157E308;
for (var i = 1; i <= this.natoms; i++) {
if (this.y[i] > ymax) ymax = this.y[i];
if (this.x[i] < xmin) xmin = this.x[i];
}
for (var i = 1; i <= this.natoms; i++) {
s += jme.JMEmol.fformat((this.x[i] - xmin) * scale, 10, 4) + jme.JMEmol.fformat((ymax - this.y[i]) * scale, 10, 4) + jme.JMEmol.fformat(0.0, 10, 4);
var z = this.getAtomLabel(i);
if (z.length == 1) z += "  ";
 else if (z.length == 2) z += " ";
 else if (z.length > 3) z = "Q  ";
s += " " + z;
var charge = 0;
if (this.q[i] > 0 && this.q[i] < 4) charge = 4 - this.q[i];
 else if (this.q[i] < 0 && this.q[i] > -4) charge = 4 - this.q[i];
z = " 0" + jme.JMEmol.iformat(charge, 3) + "  0  0  0  0  0  0  0";
var lmark = -1;
for (var j = 1; j <= this.nmarked; j++) if (this.$mark[j][0] == i) {
lmark = this.$mark[j][1];
break;
}
if (lmark > -1) z += jme.JMEmol.iformat(lmark, 3);
 else z += "  0";
s += z + "  0  0" + "\n";
}
for (var i = 1; i <= this.nbonds; i++) {
var nas = this.nasv[i];
if (this.isSingle(i)) nas = 1;
 else if (this.isDouble(i)) nas = 2;
var bonds = jme.JMEmol.iformat(this.va[i], 3) + jme.JMEmol.iformat(this.vb[i], 3);
var stereo = 0;
if (this.nasv[i] == 1 && this.stereob[i] == 1) stereo = 1;
 else if (this.nasv[i] == 1 && this.stereob[i] == 2) stereo = 6;
if (this.nasv[i] == 1 && this.stereob[i] == 3) {
stereo = 1;
bonds = jme.JMEmol.iformat(this.vb[i], 3) + jme.JMEmol.iformat(this.va[i], 3);
}if (this.nasv[i] == 1 && this.stereob[i] == 4) {
stereo = 6;
bonds = jme.JMEmol.iformat(this.vb[i], 3) + jme.JMEmol.iformat(this.va[i], 3);
}s += bonds + jme.JMEmol.iformat(nas, 3) + jme.JMEmol.iformat(stereo, 3) + "  0  0  0" + "\n";
}
for (var i = 1; i <= this.natoms; i++) if (this.q[i] != 0) {
s += "M  CHG  1" + jme.JMEmol.iformat(i, 4) + jme.JMEmol.iformat(this.q[i], 4) + "\n";
}
s += "M  END\n";
return s;
}, "~S");
Clazz.defineMethod(c$, "createExtendedMolFile", 
function(smiles){
var chiral = 0;
for (var i = 1; i <= this.nbonds; i++) if (this.stereob[i] != 0) {
chiral = 1;
break;
}
var mv30 = "M  V30 ";
var s = "";
s = smiles;
if (s.length > 79) s = s.substring(0, 76) + "...";
s += "\n";
s += JV.PropertyManager.getSDFDateLine("JME2023.01", true) + "JME " + "2023.01" + " " +  new java.util.Date() + "\n";
s += "  0  0  0  0  0  0  0  0  0  0999 V3000\n";
s += mv30 + "BEGIN CTAB" + "\n";
s += mv30 + "COUNTS " + this.natoms + " " + this.nbonds + " 0 0 " + chiral + "\n";
s += mv30 + "BEGIN ATOM" + "\n";
var scale = 0.055999999999999994;
var ymax = -1.7976931348623157E308;
var xmin = 1.7976931348623157E308;
for (var i = 1; i <= this.natoms; i++) {
if (this.y[i] > ymax) ymax = this.y[i];
if (this.x[i] < xmin) xmin = this.x[i];
}
for (var i = 1; i <= this.natoms; i++) {
s += mv30;
var z = this.getAtomLabel(i);
s += i + " " + z;
var m = 0;
var lmark = -1;
for (var j = 1; j <= this.nmarked; j++) if (this.$mark[j][0] == i) {
lmark = this.$mark[j][1];
break;
}
if (lmark > -1) m = lmark;
s += " " + jme.JMEmol.fformat((this.x[i] - xmin) * scale, 0, 4) + " " + jme.JMEmol.fformat((ymax - this.y[i]) * scale, 0, 4) + " " + jme.JMEmol.fformat(0.0, 0, 4) + " " + m;
if (this.q[i] != 0) s += " CHG=" + this.q[i];
s += "\n";
}
s += mv30 + "END ATOM" + "\n";
s += mv30 + "BEGIN BOND" + "\n";
for (var i = 1; i <= this.nbonds; i++) {
s += mv30 + i;
var nas = this.nasv[i];
if (this.isSingle(i)) nas = 1;
 else if (this.isDouble(i)) nas = 2;
var bonds = this.va[i] + " " + this.vb[i];
var stereo = 0;
if (this.nasv[i] == 1 && this.stereob[i] == 1) stereo = 1;
 else if (this.nasv[i] == 1 && this.stereob[i] == 2) stereo = 3;
if (this.nasv[i] == 1 && this.stereob[i] == 3) {
stereo = 1;
bonds = this.vb[i] + " " + this.va[i];
}if (this.nasv[i] == 1 && this.stereob[i] == 4) {
stereo = 3;
bonds = this.vb[i] + " " + this.va[i];
}s += " " + bonds + " " + nas;
if (stereo != 0) s += " CFG=" + stereo;
s += "\n";
}
s += mv30 + "END BOND" + "\n";
var abs =  new java.util.ArrayList();
var orlists =  new java.util.ArrayList();
var mixlists =  new java.util.ArrayList();
for (var i = 0; i < 10; i++) {
orlists.add(null);
mixlists.add(null);
}
for (var i = 1; i <= this.natoms; i++) {
if (this.atag[i] == null || this.atag[i].length == 0) continue;
if (this.atag[i].equals("abs")) abs.add( new Integer(i));
 else if (this.atag[i].startsWith("mix")) {
var n = Integer.parseInt(this.atag[i].substring(3));
var o = null;
if (mixlists.size() > n) o = mixlists.get(n);
var l = (o == null ?  new java.util.ArrayList() : o);
l.add( new Integer(i));
mixlists.set(n, l);
} else if (this.atag[i].startsWith("or")) {
var n = Integer.parseInt(this.atag[i].substring(2));
var o = null;
if (orlists.size() > n) o = orlists.get(n);
var l = (o == null ?  new java.util.ArrayList() : o);
l.add( new Integer(i));
orlists.set(n, l);
}}
s += this.addCollection("MDLV30/STEABS", abs, mv30);
if (orlists.size() > 0) for (var i = 1; i < orlists.size(); i++) s += this.addCollection("MDLV30/STEREL" + i, orlists.get(i), mv30);

if (mixlists.size() > 0) for (var i = 1; i < mixlists.size(); i++) s += this.addCollection("MDLV30/STERAC" + i, mixlists.get(i), mv30);

s += mv30 + "END CTAB" + "\n";
s += "M  END\n";
return s;
}, "~S");
Clazz.defineMethod(c$, "addCollection", 
function(name, list, mv30){
if (list == null || list.size() == 0) return "";
var s = "";
s += mv30 + "BEGIN COLLECTION" + "\n";
s += mv30 + name + " [ATOMS=(" + list.size();
for (var i = list.iterator(); i.hasNext(); ) s += " " + i.next();

s += ")]\n";
s += mv30 + "END COLLECTION" + "\n";
return s;
}, "~S,java.util.ArrayList,~S");
Clazz.defineMethod(c$, "getAtomLabel", 
function(i){
var z = jme.JME.zlabel[this.an[i]];
if (this.an[i] == 18) z = this.label[i];
return z;
}, "~N");
c$.iformat = Clazz.defineMethod(c$, "iformat", 
function(number, len){
var n =  new Integer(number);
var s = n.toString();
if (s.length > len) s = "?";
var space = "";
for (var i = 1; i <= len - s.length; i++) space += " ";

s = space + s;
return s;
}, "~N,~N");
c$.fformat = Clazz.defineMethod(c$, "fformat", 
function(number, len, dec){
if (dec == 0) return jme.JMEmol.iformat(Clazz.doubleToInt(number), len);
if (Math.abs(number) < 0.0009) number = 0.;
number = Math.round(number * Math.pow(10., dec)) / (Math.pow(10., dec));
var s =  new Double(number).toString();
var dotpos = s.indexOf('.');
if (dotpos < 0) {
s += ".";
dotpos = s.indexOf('.');
}var slen = s.length;
for (var i = 1; i <= dec - slen + dotpos + 1; i++) s += "0";

if (len == 0) return s;
if (s.length > len) s = "?";
var space = "";
for (var i = 1; i <= len - s.length; i++) space += " ";

s = space + s;
return s;
}, "~N,~N,~N");
c$.checkAtomicSymbol = Clazz.defineMethod(c$, "checkAtomicSymbol", 
function(s){
if (s.equals("C")) return 3;
 else if (s.equals("B")) return 2;
 else if (s.equals("N")) return 4;
 else if (s.equals("O")) return 5;
 else if (s.equals("P")) return 7;
 else if (s.equals("S")) return 8;
 else if (s.equals("F")) return 9;
 else if (s.equals("Cl")) return 10;
 else if (s.equals("Br")) return 11;
 else if (s.equals("I")) return 12;
 else if (s.equals("H")) return 1;
 else if (s.equals("Se")) return 13;
 else if (s.equals("Si")) return 6;
 else if (s.equals("R")) return 19;
 else if (s.equals("R1")) return 20;
 else if (s.equals("R2")) return 21;
 else if (s.equals("R3")) return 22;
 else return 18;
}, "~S");
Clazz.defineMethod(c$, "deleteHydrogens", 
function(){
if (this.jme.keepHydrogens) return;
iloop : for (var i = this.natoms; i >= 1; i--) {
var parent = this.v[i][1];
if (this.an[i] == 1 && this.nv[i] == 1 && this.q[i] == 0 && this.an[parent] != 1 && this.an[parent] < 18) {
for (var j = 1; j <= this.nmarked; j++) if (this.$mark[j][0] == i) continue iloop;

var bi = this.bondIdentity(i, parent);
if (this.nasv[bi] == 1) {
if (this.stereob[bi] == 0 || !this.jme.stereo) this.deleteAtom(i);
}}}
});
Clazz.defineMethod(c$, "bondIdentity", 
function(atom1, atom2){
for (var i = 1; i <= this.nbonds; i++) {
if (this.va[i] == atom1 && this.vb[i] == atom2) return i;
if (this.va[i] == atom2 && this.vb[i] == atom1) return i;
}
return 0;
}, "~N,~N");
Clazz.defineMethod(c$, "isSingle", 
function(bond){
return (this.nasv[bond] == 1);
}, "~N");
Clazz.defineMethod(c$, "isDouble", 
function(bond){
return (this.nasv[bond] == 2);
}, "~N");
Clazz.defineMethod(c$, "valenceState", 
function(){
for (var i = 1; i <= this.natoms; i++) {
this.atomValenceState(i);
}
});
Clazz.defineMethod(c$, "atomValenceState", 
function(i){
var sbo = this.sumBondOrders(i);
if (sbo == -1) {
this.nh[i] = 0;
return;
}switch (this.an[i]) {
case 1:
if (sbo == 2) this.q[i] = 1;
 else this.q[i] = 0;
this.nh[i] = 0;
break;
case 2:
if (sbo == 3 || sbo == 5) {
this.nh[i] = 0;
this.q[i] = 0;
} else if (sbo < 3) {
this.nh[i] = 3 - sbo - this.q[i];
} else if (sbo == 4) {
this.q[i] = -1;
this.nh[i] = 0;
} else if (sbo > 5) {
this.q[i] = sbo - 5;
this.nh[i] = 0;
}break;
case 3:
case 6:
if (sbo < 4) {
if (this.q[i] > 0) this.nh[i] = 2 - sbo + this.q[i];
 else if (this.q[i] < 0) this.nh[i] = 2 - sbo - this.q[i];
 else this.nh[i] = 4 - sbo;
} else {
this.q[i] = sbo - 4;
this.nh[i] = 4 - sbo + this.q[i];
}break;
case 4:
case 7:
if (sbo < 3) this.nh[i] = 3 - sbo + this.q[i];
 else if (sbo == 3) {
if (this.q[i] < 0) {
this.q[i] = 0;
this.nh[i] = 0;
} else if (this.q[i] > 0) this.nh[i] = this.q[i];
 else this.nh[i] = 3 - sbo;
} else if (sbo == 4) {
this.q[i] = 1;
this.nh[i] = 0;
} else if (sbo == 6) {
this.q[i] = -1;
this.nh[i] = 0;
} else {
this.q[i] = sbo - 5;
this.nh[i] = 0;
}break;
case 5:
if (sbo == 2) {
if (this.q[i] < 0) {
this.q[i] = 0;
this.nh[i] = 0;
} else if (this.q[i] > 0) this.nh[i] = this.q[i];
 else this.nh[i] = 2 - sbo;
}if (sbo > 2) this.q[i] = sbo - 2;
this.nh[i] = 2 - sbo + this.q[i];
break;
case 8:
case 13:
if (sbo < 2) this.nh[i] = 2 - sbo + this.q[i];
 else if (sbo == 2) {
if (this.q[i] < 0) {
this.q[i] = 0;
this.nh[i] = 0;
} else if (this.q[i] > 0) this.nh[i] = this.q[i];
 else this.nh[i] = 2 - sbo;
} else if (sbo == 3) {
if (this.nv[i] == 2) {
this.q[i] = 0;
this.nh[i] = 1;
} else {
this.q[i] = 1;
this.nh[i] = 0;
}} else if (sbo == 4) {
this.q[i] = 0;
this.nh[i] = 0;
} else if (sbo == 5) {
this.q[i] = 0;
this.nh[i] = 1;
} else {
this.q[i] = sbo - 6;
this.nh[i] = 0;
}break;
case 9:
case 10:
case 11:
case 12:
if (sbo >= 1) this.q[i] = sbo - 1;
this.nh[i] = 1 - sbo + this.q[i];
if (sbo > 2) {
this.q[i] = 0;
this.nh[i] = 0;
}break;
case 19:
case 18:
this.nh[i] = 0;
break;
}
if (this.nh[i] < 0) this.nh[i] = 0;
if (this.jme.relativeStereo && this.atag[i] != null && this.atag[i].length > 0) {
var ok = false;
for (var j = 1; j <= this.nv[i]; j++) {
var bond = this.bondIdentity(i, this.v[i][j]);
if (i == this.va[bond] && (this.stereob[bond] == 1 || this.stereob[bond] == 2)) {
ok = true;
break;
}if (i == this.vb[bond] && (this.stereob[bond] == 3 || this.stereob[bond] == 4)) {
ok = true;
break;
}}
if (!ok) this.atag[i] = "";
}}, "~N");
Clazz.defineMethod(c$, "changeCharge", 
function(atom, type){
var np = "Charge change not possible on ";
if (type == 1) {
this.q[atom]++;
return;
} else if (type == -1) {
this.q[atom]--;
return;
}var sbo = this.sumBondOrders(atom);
if (sbo == -1) {
if (type == 0) {
if (this.q[atom] == 0) this.q[atom] = 1;
 else if (this.q[atom] == 1) this.q[atom] = -1;
 else if (this.q[atom] == -1) this.q[atom] = 0;
}}switch (this.an[atom]) {
case 2:
if (sbo > 2) this.jme.info(np + "this boron !");
if (this.q[atom] == 0) this.q[atom] = 1;
 else if (this.q[atom] == 1) this.q[atom] = 0;
break;
case 3:
if (sbo > 3) this.jme.info(np + "this carbon !");
 else if (sbo < 4) {
if (this.q[atom] == 0) this.q[atom] = -1;
 else if (this.q[atom] == -1) this.q[atom] = 1;
 else if (this.q[atom] == 1) this.q[atom] = 0;
}break;
case 4:
case 7:
if (sbo > 3) this.jme.info(np + "multibonded N or P !");
 else if (sbo == 3 && this.q[atom] == 0) this.q[atom] = 1;
 else if (sbo == 3 && this.q[atom] == 1) this.q[atom] = 0;
 else if (sbo < 3 && this.q[atom] == 0) this.q[atom] = 1;
 else if (sbo < 3 && this.q[atom] == 1) this.q[atom] = -1;
 else if (sbo < 3 && this.q[atom] == -1) this.q[atom] = 0;
break;
case 5:
case 8:
case 13:
if (sbo > 2) this.jme.info(np + "multibonded O or S !");
 else if (sbo == 2 && this.q[atom] == 0) this.q[atom] = 1;
 else if (sbo == 2 && this.q[atom] == 1) this.q[atom] = 0;
 else if (sbo < 2 && this.q[atom] == 0) this.q[atom] = -1;
 else if (sbo < 2 && this.q[atom] == -1) this.q[atom] = 1;
 else if (sbo < 2 && this.q[atom] == 1) this.q[atom] = 0;
break;
case 9:
case 10:
case 11:
case 12:
if (sbo == 0 && this.q[atom] == 0) this.q[atom] = -1;
 else if (sbo == 0 && this.q[atom] == -1) this.q[atom] = 0;
 else this.jme.info(np + "the halogen !");
break;
case 18:
this.jme.info("Use X button to change charge on the X atom !");
break;
}
}, "~N,~N");
Clazz.defineMethod(c$, "sumBondOrders", 
function(atom){
var sbo = 0;
for (var i = 1; i <= this.nv[atom]; i++) {
var bond = this.bondIdentity(atom, this.v[atom][i]);
if (this.isSingle(bond)) sbo += 1;
 else if (this.isDouble(bond)) sbo += 2;
 else if (this.nasv[bond] == 3) sbo += 3;
 else if (this.nasv[bond] == 9) return -1;
}
return sbo;
}, "~N");
Clazz.defineMethod(c$, "mark", 
function(){
this.jme.markUsed = true;
if (this.jme.star) {
this.doColoring = -1;
if (this.abg[this.touchedAtom] == 0) this.abg[this.touchedAtom] = 4;
 else this.abg[this.touchedAtom] = 0;
return;
}for (var i = 1; i <= this.nmarked; i++) {
if (this.touchedAtom == this.$mark[i][0]) {
if (this.jme.currentMark == -1) {
for (var j = i; j < this.nmarked; j++) {
this.$mark[j][0] = this.$mark[j + 1][0];
this.$mark[j][1] = this.$mark[j + 1][1];
}
this.nmarked--;
} else {
var n = this.jme.currentMark;
if (this.jme.autonumber) {
if (!this.jme.mouseShift) this.maxMark++;
n = this.maxMark;
}this.$mark[i][1] = n;
}return;
}}
var storage = this.$mark.length;
if (++this.nmarked > storage - 1) {
var n_m =  Clazz.newIntArray (storage + 5, 2, 0);
System.arraycopy(this.$mark, 0, n_m, 0, this.$mark.length);
this.$mark = n_m;
}this.$mark[this.nmarked][0] = this.touchedAtom;
var n = this.jme.currentMark;
if (this.jme.autonumber) {
if (!this.jme.mouseShift) this.maxMark++;
n = this.maxMark;
}this.$mark[this.nmarked][1] = n;
});
Clazz.defineMethod(c$, "numberAtoms", 
function(){
this.nmarked = 0;
this.maxMark = 0;
this.createSmiles();
for (var i = 1; i <= this.natoms; i++) {
this.touchedAtom = i;
this.mark();
}
this.touchedAtom = 0;
});
Clazz.defineMethod(c$, "setLabel", 
function(n, s){
if (this.label == null || this.label.length < this.natoms + 1) this.label =  new Array(this.natoms + 1);
this.label[n] = s;
}, "~N,~S");
Clazz.defineMethod(c$, "reactionPart", 
function(){
var center =  Clazz.newDoubleArray (4, 0);
this.centerPoint(center);
var xpix = this.jme.dimension.width;
if (!this.jme.depict) xpix -= this.jme.sd;
if (center[0] < Clazz.doubleToInt(xpix / 2) - Clazz.doubleToInt(this.jme.arrowWidth / 2)) return 1;
 else if (center[0] > Clazz.doubleToInt(xpix / 2) + Clazz.doubleToInt(this.jme.arrowWidth / 2)) return 3;
 else return 2;
});
c$.generatePrimes = Clazz.defineMethod(c$, "generatePrimes", 
function(n){
var npn;
var pn =  Clazz.newLongArray (n + 2, 0);
var prime =  Clazz.newIntArray (100, 0);
var test = 5;
var index = 0;
var num = 0;
var check = true;
prime[0] = 3;
pn[1] = 2;
pn[2] = 3;
npn = 2;
if (n < 3) return pn;
while (test < (prime[num] * prime[num])) {
index = 0;
check = true;
while (check == true && index <= num && test >= (prime[index] * prime[index])) {
if (test % prime[index] == 0) check = false;
 else index++;
}
if (check == true) {
pn[++npn] = test;
if (npn >= n) return pn;
if (num < (prime.length - 1)) {
num++;
prime[num] = test;
}}test += 2;
}
System.err.println("ERROR - Prime Number generator failed !");
return pn;
}, "~N");
Clazz.defineMethod(c$, "saveXY", 
function(){
var x =  Clazz.newDoubleArray (this.natoms + 1, 0);
var y =  Clazz.newDoubleArray (this.natoms + 1, 0);
System.arraycopy(this.x, 1, x, 1, this.natoms);
System.arraycopy(this.y, 1, y, 1, this.natoms);
return  Clazz.newArray(-1, [x, y]);
});
Clazz.defineMethod(c$, "restoreXY", 
function(xy){
System.arraycopy(xy[0], 1, this.x, 1, this.natoms);
System.arraycopy(xy[1], 1, this.y, 1, this.natoms);
}, "~A");
c$.TESTDRAW = false;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
