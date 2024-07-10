Clazz.declarePackage("J.adapter.readers.quantum");
Clazz.load(["J.adapter.readers.quantum.SlaterReader"], "J.adapter.readers.quantum.MopacSlaterReader", ["java.util.Hashtable"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.atomicNumbers = null;
this.mopacBasis = null;
this.allowMopacDCoef = false;
Clazz.instantialize(this, arguments);}, J.adapter.readers.quantum, "MopacSlaterReader", J.adapter.readers.quantum.SlaterReader);
Clazz.defineMethod(c$, "scaleSlater", 
function(ex, ey, ez, er, zeta){
var el = Math.abs(ex + ey + ez);
switch (el) {
case 0:
return J.adapter.readers.quantum.MopacSlaterReader.getSlaterConstSSpherical(er + 1, Math.abs(zeta));
case 1:
return J.adapter.readers.quantum.MopacSlaterReader.getSlaterConstPSpherical(er + 2, Math.abs(zeta));
}
if (ex >= 0 && ey >= 0) {
return Clazz.superCall(this, J.adapter.readers.quantum.MopacSlaterReader, "scaleSlater", [ex, ey, ez, er, zeta]);
}if (el == 3) {
return 0;
}return J.adapter.readers.quantum.MopacSlaterReader.getSlaterConstDSpherical(el + er + 1, Math.abs(zeta), ex, ey);
}, "~N,~N,~N,~N,~N");
c$.getSlaterConstDSpherical = Clazz.defineMethod(c$, "getSlaterConstDSpherical", 
function(n, zeta, ex, ey){
return J.adapter.readers.quantum.SlaterReader.fact(15 / (ex < 0 ? 12 : ey < 0 ? 4 : 1), zeta, n);
}, "~N,~N,~N,~N");
c$.getSlaterConstSSpherical = Clazz.defineMethod(c$, "getSlaterConstSSpherical", 
function(n, zeta){
return Math.pow(2 * zeta, n + 0.5) * Math.sqrt(0.07957747154594767 / J.adapter.readers.quantum.SlaterReader.fact_2n[n]);
}, "~N,~N");
c$.getSlaterConstPSpherical = Clazz.defineMethod(c$, "getSlaterConstPSpherical", 
function(n, zeta){
var f = J.adapter.readers.quantum.SlaterReader.fact_2n[n] / 3;
return Math.pow(2 * zeta, n + 0.5) * Math.sqrt(0.07957747154594767 / f);
}, "~N,~N");
Clazz.defineMethod(c$, "setMOData", 
function(clearOrbitals){
if (!this.allowNoOrbitals && this.orbitals.size() == 0) return;
if (this.mopacBasis == null || !this.forceMOPAC && this.gaussians != null && this.shells != null) {
if (this.forceMOPAC) System.out.println("MopacSlaterReader ignoring MOPAC zeta parameters -- using Gaussian contractions");
Clazz.superCall(this, J.adapter.readers.quantum.MopacSlaterReader, "setMOData", [clearOrbitals]);
return;
}this.setSlaters(false);
this.moData.put("calculationType", this.calculationType);
this.moData.put("energyUnits", this.energyUnits);
this.moData.put("mos", this.orbitals);
this.finalizeMOData(this.lastMoData = this.moData);
if (clearOrbitals) {
this.clearOrbitals();
}}, "~B");
c$.getNPQ = Clazz.defineMethod(c$, "getNPQ", 
function(atomicNumber){
return (atomicNumber < J.adapter.readers.quantum.MopacSlaterReader.principalQuantumNumber.length ? J.adapter.readers.quantum.MopacSlaterReader.principalQuantumNumber[atomicNumber] : 0);
}, "~N");
c$.getNPQs = Clazz.defineMethod(c$, "getNPQs", 
function(atomicNumber){
var n = J.adapter.readers.quantum.MopacSlaterReader.getNPQ(atomicNumber);
switch (atomicNumber) {
case 10:
case 18:
case 36:
case 54:
case 86:
return n + 1;
default:
return n;
}
}, "~N");
c$.getNPQp = Clazz.defineMethod(c$, "getNPQp", 
function(atomicNumber){
var n = J.adapter.readers.quantum.MopacSlaterReader.getNPQ(atomicNumber);
switch (atomicNumber) {
case 2:
return n + 1;
default:
return n;
}
}, "~N");
c$.getNPQd = Clazz.defineMethod(c$, "getNPQd", 
function(atomicNumber){
return (atomicNumber < J.adapter.readers.quantum.MopacSlaterReader.npqd.length ? J.adapter.readers.quantum.MopacSlaterReader.npqd[atomicNumber] : 0);
}, "~N");
Clazz.overrideMethod(c$, "addSlaterBasis", 
function(){
if (this.mopacBasis == null || this.slaters != null && this.slaters.size() > 0) return;
var ac = this.asc.ac;
var i0 = this.asc.getLastAtomSetAtomIndex();
var atoms = this.asc.atoms;
for (var i = i0; i < ac; ++i) {
var an = atoms[i].elementNumber;
this.createMopacSlaters(i, an, this.mopacBasis[an], this.allowMopacDCoef);
}
});
Clazz.defineMethod(c$, "createMopacSlaters", 
function(iAtom, atomicNumber, values, allowD){
var zeta;
if ((zeta = values[0]) != 0) {
this.createSphericalSlaterByType(iAtom, atomicNumber, "S", zeta, 1);
}if ((zeta = values[1]) != 0) {
this.createSphericalSlaterByType(iAtom, atomicNumber, "Px", zeta, 1);
this.createSphericalSlaterByType(iAtom, atomicNumber, "Py", zeta, 1);
this.createSphericalSlaterByType(iAtom, atomicNumber, "Pz", zeta, 1);
}if ((zeta = values[2]) != 0 && allowD) {
this.createSphericalSlaterByType(iAtom, atomicNumber, "Dx2-y2", zeta, 1);
this.createSphericalSlaterByType(iAtom, atomicNumber, "Dxz", zeta, 1);
this.createSphericalSlaterByType(iAtom, atomicNumber, "Dz2", zeta, 1);
this.createSphericalSlaterByType(iAtom, atomicNumber, "Dyz", zeta, 1);
this.createSphericalSlaterByType(iAtom, atomicNumber, "Dxy", zeta, 1);
}}, "~N,~N,~A,~B");
Clazz.defineMethod(c$, "createSphericalSlaterByType", 
function(iAtom, atomicNumber, type, zeta, coef){
var pt = "S Px Py Pz  Dx2-y2Dxz Dz2 Dyz Dxy".indexOf(type);
switch (pt) {
case 0:
var sd = this.addSlater(iAtom + 1, 0, 0, 0, J.adapter.readers.quantum.MopacSlaterReader.getNPQs(atomicNumber) - 1, zeta, coef);
sd.elemNo = atomicNumber;
return;
case 2:
case 5:
case 8:
this.addSlater(iAtom + 1, pt == 2 ? 1 : 0, pt == 5 ? 1 : 0, pt == 8 ? 1 : 0, J.adapter.readers.quantum.MopacSlaterReader.getNPQp(atomicNumber) - 2, zeta, coef);
return;
}
pt = (pt >> 2) * 3 - 9;
this.addSlater(iAtom + 1, J.adapter.readers.quantum.MopacSlaterReader.sphericalDValues[pt++], J.adapter.readers.quantum.MopacSlaterReader.sphericalDValues[pt++], J.adapter.readers.quantum.MopacSlaterReader.sphericalDValues[pt++], J.adapter.readers.quantum.MopacSlaterReader.getNPQd(atomicNumber) - 3, zeta, coef);
}, "~N,~N,~S,~N,~N");
c$.getMopacAtomZetaSPD = Clazz.defineMethod(c$, "getMopacAtomZetaSPD", 
function(type){
if (J.adapter.readers.quantum.MopacSlaterReader.mopacParams == null) J.adapter.readers.quantum.MopacSlaterReader.mopacParams =  new java.util.Hashtable();
var params = J.adapter.readers.quantum.MopacSlaterReader.mopacParams.get(type);
if (params == null) {
J.adapter.readers.quantum.MopacSlaterReader.mopacParams.put(type, params =  Clazz.newFloatArray (120, 3, 0));
var data = null;
switch ("AM1  MNDO PM3  PM6  PM7  RM1".indexOf(type)) {
case 0:
data = J.adapter.readers.quantum.MopacSlaterReader._AM1_C;
break;
case 5:
data = J.adapter.readers.quantum.MopacSlaterReader._MNDO_C;
break;
case 10:
data = J.adapter.readers.quantum.MopacSlaterReader._PM3_C;
break;
case 15:
data = J.adapter.readers.quantum.MopacSlaterReader._PM6_C;
break;
case 20:
data = J.adapter.readers.quantum.MopacSlaterReader._PM7_C;
break;
case 25:
J.adapter.readers.quantum.MopacSlaterReader.addData(params, J.adapter.readers.quantum.MopacSlaterReader._AM1_C);
data = J.adapter.readers.quantum.MopacSlaterReader._RM1_C;
break;
default:
System.err.println("MopacSlaterReader could not find MOPAC params for " + type);
return null;
}
J.adapter.readers.quantum.MopacSlaterReader.addData(params, data);
}System.out.println("MopacSlaterReader using MOPAC params for " + type);
return params;
}, "~S");
c$.addData = Clazz.defineMethod(c$, "addData", 
function(params, data){
for (var i = 0, p = 0, a = 0; i < data.length; i++) {
var d = data[i];
if (d < 0) {
a = Clazz.floatToInt(-d);
p = 0;
continue;
}params[a][p++] = d;
}
}, "~A,~A");
c$.principalQuantumNumber =  Clazz.newIntArray(-1, [0, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6]);
c$.npqd =  Clazz.newIntArray(-1, [0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 7]);
c$.sphericalDValues =  Clazz.newIntArray(-1, [0, -2, 0, 1, 0, 1, -2, 0, 0, 0, 1, 1, 1, 1, 0]);
c$.mopacParams = null;
c$._AM1_C =  Clazz.newFloatArray(-1, [-1, 1.188078, -2, 2.1956103, 6.9012486, -3, 0.7973487, 0.9045583, -4, 0.7425237, 0.8080499, -6, 1.808665, 1.685116, -7, 2.31541, 2.15794, -8, 3.108032, 2.524039, -9, 3.770082, 2.49467, -10, 5.998377, 4.1699304, -11, 0.789009, 1.1399864, -12, 1.0128928, 1.1798191, -13, 1.516593, 1.306347, -14, 1.830697, 1.284953, -15, 1.98128, 1.87515, -16, 2.366515, 1.667263, -17, 3.631376, 2.076799, -18, 0.9714216, 5.9236231, -19, 1.2660244, 0.9555939, -20, 1.1767754, 1.273852, -30, 1.954299, 1.372365, -31, 4.000216, 1.3540466, -32, 1.219631, 1.982794, -33, 2.2576897, 1.724971, -34, 2.684157, 2.0506164, -35, 3.064133, 2.038333, -36, 3.5931632, 2.0944633, -37, 4.0000187, 1.0140619, -38, 1.5236848, 1.5723524, -42, 1.945, 1.477, 2.468, -49, 1.8281576, 1.48475, -50, 1.6182807, 1.5084984, -51, 2.254823, 2.218592, -52, 2.1321165, 1.971268, -53, 2.102858, 2.161153, -54, 4.9675243, 3.1432142, -55, 5.7873708, 1.0311693, -56, 1.9136517, 1.3948894, -80, 2.036413, 1.955766, -81, 3.8077333, 1.5511578, -82, 2.4432161, 1.5506706, -83, 4.0007862, 0.9547714, -102, 4, 0.3, 0.3, -104]);
c$._MNDO_C =  Clazz.newFloatArray(-1, [-1, 1.331967, -2, 1.7710761, 6.9018258, -3, 0.4296141, 0.7554884, -4, 1.00421, 1.00421, -5, 1.506801, 1.506801, -6, 1.787537, 1.787537, -7, 2.255614, 2.255614, -8, 2.699905, 2.699905, -9, 2.848487, 2.848487, -10, 5.9998745, 4.17526, -11, 0.8213124, 1.030327, -12, 0.9394811, 1.3103428, -13, 1.444161, 1.444161, -14, 1.315986, 1.709943, -15, 2.10872, 1.78581, -16, 2.312962, 2.009146, -17, 3.784645, 2.036263, -18, 0.9821697, 5.999715, -19, 0.7276039, 0.9871174, -20, 1.0034161, 1.3102564, -21, 1.3951231, 5.0160943, 0.9264186, -22, 0.8961552, 0.9676159, 1.8698884, -23, 1.2873544, 1.1744379, 2.015022, -24, 2.1495003, 1.3131074, 2.3289346, -26, 1.4536275, 0.8933716, 1.8691105, -27, 0.59975, 0.607314, 1.856797, -28, 0.7735888, 6.0000132, 2.7857108, -29, 3.3957872, 1.786178, 3.3573266, -30, 2.047359, 1.460946, -31, 0.6986316, 1.8386933, -32, 1.29318, 2.020564, -33, 2.5614338, 1.6117315, -34, 0.7242956, 1.9267288, -35, 3.8543019, 2.1992091, -36, 3.5608622, 1.9832062, -37, 4.0001632, 0.9187408, -38, 1.3729266, 1.1118128, -40, 1.5386288, 1.1472515, 1.8744783, -42, 2.0001083, 1.4112837, 2.1944707, -46, 1.6942397, 6.0000131, 2.2314824, -47, 2.6156672, 1.5209942, 3.1178537, -48, 1.4192491, 1.0480637, -49, 1.762574, 1.8648962, -50, 2.08038, 1.937106, -51, 3.6458835, 1.9733156, -52, 2.7461609, 1.6160376, -53, 2.272961, 2.169498, -54, 4.9900791, 2.6929255, -55, 6.000417, 0.8986916, -56, 1.9765973, 1.3157348, -78, 1.8655763, 1.9475781, 2.8552253, -80, 2.218184, 2.065038, -81, 4.0000447, 1.8076332, -82, 2.498286, 2.082071, -83, 2.6772255, 0.6936864, -85, -87, -90, 1.435306, 1.435306, -100, -101, -102, 4, 0.3, 0.3, -103, -104, -105]);
c$._PM3_C =  Clazz.newFloatArray(-1, [-1, 0.967807, -2, 1.7710761, 6.9018258, -3, 0.65, 0.75, -4, 0.877439, 1.508755, -5, 1.5312597, 1.1434597, -6, 1.565085, 1.842345, -7, 2.028094, 2.313728, -8, 3.796544, 2.389402, -9, 4.708555, 2.491178, -10, 5.9998745, 4.17526, -11, 2.6618938, 0.8837425, -12, 0.698552, 1.483453, -13, 1.702888, 1.073629, -14, 1.635075, 1.313088, -15, 2.017563, 1.504732, -16, 1.891185, 1.658972, -17, 2.24621, 2.15101, -18, 0.9821697, 5.999715, -19, 0.8101687, 0.9578342, -20, 1.2087415, 0.940937, -30, 1.819989, 1.506922, -31, 1.84704, 0.839411, -32, 2.2373526, 1.5924319, -33, 2.636177, 1.703889, -34, 2.828051, 1.732536, -35, 5.348457, 2.12759, -36, 3.5608622, 1.9832062, -37, 4.0000415, 1.013459, -38, 1.2794532, 1.39125, -48, 1.679351, 2.066412, -49, 2.016116, 1.44535, -50, 2.373328, 1.638233, -51, 2.343039, 1.899992, -52, 4.165492, 1.647555, -53, 7.001013, 2.454354, -54, 4.9900791, 2.6929255, -55, 3.5960298, 0.9255168, -56, 1.9258219, 1.4519912, -80, 1.476885, 2.479951, -81, 6.867921, 1.969445, -82, 3.141289, 1.892418, -83, 4.916451, 1.934935, -87, -102, 4, 0.3, -104]);
c$._PM6_C =  Clazz.newFloatArray(-1, [-1, 1.268641, -2, 3.313204, 3.657133, -3, 0.981041, 2.953445, -4, 1.212539, 1.276487, -5, 1.634174, 1.479195, -6, 2.047558, 1.702841, -7, 2.380406, 1.999246, -8, 5.421751, 2.27096, -9, 6.043849, 2.906722, -10, 6.000148, 3.834528, -11, 0.686327, 0.950068, -12, 1.31083, 1.388897, -13, 2.364264, 1.749102, 1.269384, -14, 1.752741, 1.198413, 2.128593, -15, 2.158033, 1.805343, 1.230358, -16, 2.192844, 1.841078, 3.109401, -17, 2.63705, 2.118146, 1.324033, -18, 6.000272, 5.94917, -19, 6.000478, 1.127503, -20, 1.528258, 2.060094, -21, 1.402469, 1.345196, 1.859012, -22, 5.324777, 1.164068, 1.41828, -23, 1.97433, 1.063106, 1.394806, -24, 3.28346, 1.029394, 1.623119, -25, 2.13168, 1.52588, 2.6078, -26, 1.47915, 6.002246, 1.080747, -27, 1.166613, 3, 1.860218, -28, 1.591828, 2.304739, 2.514761, -29, 1.669096, 3, 2.73499, -30, 1.512875, 1.789482, -31, 2.339067, 1.729592, -32, 2.546073, 1.70913, -33, 2.926171, 1.765191, 1.392142, -34, 2.512366, 2.007576, -35, 4.670684, 2.035626, 1.521031, -36, 1.312248, 4.491371, -37, 5.510145, 1.33517, -38, 2.197303, 1.730137, -39, 0.593368, 1.490422, 1.650893, -40, 1.69259, 1.694916, 1.567392, -41, 2.355562, 1.386907, 1.977324, -42, 1.060429, 1.350412, 1.827152, -43, 1.956245, 6.006299, 1.76736, -44, 1.459195, 5.537201, 2.093164, -45, 1.324919, 4.306111, 2.901406, -46, 1.658503, 1.156718, 2.219861, -47, 1.994004, 0.681817, 6.007328, -48, 1.384108, 1.957413, -49, 2.023087, 2.106618, -50, 2.383941, 2.057908, -51, 2.391178, 1.773006, 2.46559, -52, 2.769862, 1.731319, -53, 4.498653, 1.917072, 1.875175, -54, 2.759787, 1.977446, -55, 5.956008, 1.619485, -56, 1.395379, 1.430139, -57, 2.67378, 1.248192, 1.688562, -71, 5.471741, 1.712296, 2.225892, -72, 3.085344, 1.575819, 1.84084, -73, 4.578087, 4.841244, 1.838249, -74, 2.66456, 1.62401, 1.7944, -75, 2.411839, 1.815351, 2.522766, -76, 3.031, 1.59396, 1.77557, -77, 1.500907, 4.106373, 2.676047, -78, 2.301264, 1.662404, 3.168852, -79, 1.814169, 1.618657, 5.053167, -80, 2.104896, 1.516293, -81, 3.335883, 1.766141, -82, 2.368901, 1.685246, -83, 3.702377, 1.872327, -85, -87, -90, 1.435306, 1.435306, -97, -98, 2, -100, -101, -102, 4, -103, -104, -105]);
c$._PM7_C =  Clazz.newFloatArray(-1, [-1, 1.260237, -2, 3.313204, 3.657133, -3, 0.804974, 6.02753, -4, 1.036199, 1.764629, -5, 1.560481, 1.449712, -6, 1.942244, 1.708723, -7, 2.354344, 2.028288, -8, 5.972309, 2.349017, -9, 6.07003, 2.930631, -10, 6.000148, 3.834528, -11, 1.666701, 1.397571, -12, 1.170297, 1.840439, -13, 1.232599, 1.219336, 1.617502, -14, 1.433994, 1.671776, 1.221915, -15, 2.257933, 1.555172, 1.235995, -16, 2.046153, 1.807678, 3.510309, -17, 2.223076, 2.264466, 0.949994, -18, 6.000272, 5.94917, -19, 5.422018, 1.471023, -20, 1.477988, 2.220194, -21, 1.794897, 2.174934, 5.99286, -22, 1.448579, 1.940695, 1.093648, -23, 6.051795, 2.249871, 1.087345, -24, 2.838413, 1.37956, 1.188729, -25, 1.66644, 2.078735, 2.89707, -26, 1.157576, 2.737621, 1.860792, -27, 1.789441, 1.531664, 1.951497, -28, 1.70834, 2.000099, 5.698724, -29, 1.735325, 3.219976, 6.013523, -30, 1.56014, 1.915631, -31, 1.913326, 1.811217, -32, 2.762845, 1.531131, -33, 3.21385, 1.628384, 3.314358, -34, 2.75113, 1.901764, -35, 3.72548, 2.242318, 1.591034, -36, 1.312248, 4.491371, -37, 1.314831, 6.015581, -38, 2.092264, 3.314082, -39, 1.605083, 2.131069, 6.021645, -40, 1.373517, 1.141705, 1.618769, -41, 2.761686, 5.999062, 1.611677, -42, 1.595399, 1.426575, 1.787748, -43, 2.104672, 2.669984, 3.030496, -44, 1.605646, 4.58082, 1.244578, -45, 1.591465, 4.546046, 2.685918, -46, 5.790768, 2.169788, 1.327661, -47, 1.793032, 2.528721, 3.524808, -48, 3.670047, 1.857036, -49, 1.902085, 1.940127, -50, 1.959238, 1.976146, -51, 1.9986, 1.887062, 1.475516, -52, 3.024819, 2.598283, -53, 3.316202, 2.449124, 1.716121, -54, 3.208788, 2.727979, -55, 1.776064, 6.02531, -56, 1.75049, 1.968788, -57, 3.398968, 1.811983, 1.894574, -71, 2.327039, 6.000335, 1.208414, -72, 2.854938, 3.079458, 2.067146, -73, 4.116264, 3.380936, 1.755408, -74, 3.881177, 2.044717, 1.928901, -75, 2.452162, 1.583194, 2.414839, -76, 3.094808, 2.845232, 1.986395, -77, 1.924564, 3.510744, 2.437796, -78, 2.922551, 0.725689, 2.158085, -79, 1.904923, 2.408005, 4.377691, -80, 2.575831, 1.955505, -81, 1.903342, 2.838647, 5.015677, -82, 4.706006, 2.591455, -83, 5.465413, 2.037481, 2.8554, -85, -87, -90, 1.435306, 1.435306, -97, -98, 2, -100, -101, -102, 4, -103, -104, -105]);
c$._RM1_C =  Clazz.newFloatArray(-1, [-1, 1.0826737, -6, 1.850188, 1.7683009, -7, 2.3744716, 1.9781257, -8, 3.1793691, 2.5536191, -9, 4.4033791, 2.6484156, -15, 2.1224012, 1.7432795, -16, 2.1334431, 1.8746065, -17, 3.8649107, 1.8959314, -35, 5.7315721, 2.0314758, -53, 2.5300375, 2.3173868, -57, 1.272677, 1.423276, 1.410369, -58, 1.281028, 1.425366, 1.412866, -59, 1.538039, 1.581647, 1.374904, -60, 1.45829, 1.570516, 1.513561, -61, 1.065536, 1.846925, 1.424049, -62, 1.293914, 1.738656, 1.521378, -63, 1.350342, 1.733714, 1.494122, -64, 1.272776, 1.908122, 1.515905, -65, 1.210052, 1.921514, 1.528123, -66, 1.295275, 1.912107, 1.413397, -67, 1.33055, 1.779559, 1.536524, -68, 1.347757, 1.806481, 1.466189, -69, 1.369147, 1.674365, 1.714394, -70, 1.239808, 1.849144, 1.485378, -71, 1.425302, 1.790353, 1.642603, -102, 4, 0.3]);
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
