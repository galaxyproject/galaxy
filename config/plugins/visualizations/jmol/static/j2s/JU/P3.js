Clazz.declarePackage("JU");
Clazz.load(["JU.T3"], "JU.P3", null, function(){
var c$ = Clazz.declareType(JU, "P3", JU.T3);
c$.newP = Clazz.defineMethod(c$, "newP", 
function(t){
var p =  new JU.P3();
p.x = t.x;
p.y = t.y;
p.z = t.z;
return p;
}, "JU.T3");
c$.getUnlikely = Clazz.defineMethod(c$, "getUnlikely", 
function(){
return (JU.P3.unlikely == null ? JU.P3.unlikely = JU.P3.new3(3.141592653589793, 2.718281828459045, (8.539734222673566)) : JU.P3.unlikely);
});
c$.new3 = Clazz.defineMethod(c$, "new3", 
function(x, y, z){
var p =  new JU.P3();
p.x = x;
p.y = y;
p.z = z;
return p;
}, "~N,~N,~N");
c$.newA = Clazz.defineMethod(c$, "newA", 
function(a){
return JU.P3.new3(a[0], a[1], a[2]);
}, "~A");
c$.unlikely = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
