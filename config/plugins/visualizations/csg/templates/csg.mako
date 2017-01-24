<%
    root = h.url_for( "/" )
    app_root = root + "plugins/visualizations/csg/static/"
%>

<!DOCTYPE HTML>
<html>
    <head>
        <!-- CSG Viewer is a web application for 3D shape visualization. -->
        <title>${hda.name | h} | ${visualization_name}</title>
        ${h.javascript_link( app_root + 'dat.gui.min.js' )}
        ${h.javascript_link( app_root + 'three.min.js' )}
        ${h.javascript_link( app_root + 'Detector.js' )}
        ${h.javascript_link( app_root + 'OrbitControls.js' )}
        ${h.javascript_link( app_root + 'PLYLoader.js' )}
        ${h.javascript_link( app_root + 'VTKLoader.js' )}
    </head>
    <body>
        <!-- Div which will hold the Output -->
        <div id="WebGL-output"></div>
        <script type="text/javascript">

            // Global variables
            var container;
            var scene = new THREE.Scene();
            var renderer;
            var controls;
            var bbHelper;
            var defaultBackgroundColor = 0x4d576b;

            // Camera
            var screenWidth = window.innerWidth;
            var screenHeight = window.innerHeight;
            var VIEW_ANGLE = 40;
            var aspect = screenWidth / screenHeight;
            var near = 1;
            var far = 10000;
            var camera = new THREE.PerspectiveCamera(VIEW_ANGLE, aspect, near, far);

            init();
            //animate();

            function init() {
                window.addEventListener('resize', onWindowResize, false);
                // Color, near, far
                scene.fog = new THREE.Fog(0x111111, 0.1, 1000);
                // Data format and loader
                var hdaExt  = '${hda.ext}';
                if (hdaExt == 'plyascii' || hdaExt == 'plybinary') {
                    // This returns THREE.Geometry()
                    var loader = new THREE.PLYLoader();
                } else {
                    // This returns THREE.BufferGeometry()
                    var loader = new THREE.VTKLoader();
                }
                loader.load("${h.url_for( controller='/datasets', action='index')}/${trans.security.encode_id( hda.id )}/display",
                function (geometry) {
                    var surface = new THREE.MeshPhongMaterial({shading: THREE.SmoothShading,
                                                                side: THREE.DoubleSide,
                                                                shininess: 100,
                                                                emissive: 0x000000,
                                                                specular: 0x111111,
                                                                metal: false});
                    var edges = new THREE.MeshBasicMaterial({color: 0x111111});
                    geometry.receiveShadow = true;
                    geometry.computeFaceNormals();
                    // Normals may or may not have been set
                    if ( geometry.type == "BufferGeometry" && ! geometry.getAttribute( 'normal' ) ) {
                         geometry.computeVertexNormals();
                    }
                    var geometryHasColor = false;
                    if ( geometry.type == "BufferGeometry" && geometry.getAttribute( 'color' ) ) {
                        geometryHasColor = true;
                        // Color vertices
                        surface[ 'vertexColors' ] = THREE.VertexColors;
                    } else if ( geometry.type == "Geometry" ) { 
                        // A geometry implies colors
                        geometryHasColor = true;
                        // Color Faces
                        surface[ 'vertexColors' ] = THREE.FaceColors;
                    } else {
                        // No color, use gui input
                        surface[ 'color' ] = new THREE.Color( 0xAAAAAA );
                        surface[ 'vertexColors' ] = THREE.NoColors;
                    }
                    var meshSurface = new THREE.Mesh(geometry, surface);
                    scene.add(meshSurface);
                    var mesh = new THREE.Mesh(geometry, surface);
                    // Will be added on request to the scene
                    var meshEdges = new THREE.EdgesHelper(mesh, 0x111111);
                    // Define the BoundingBox
                    bbHelper = new THREE.BoundingBoxHelper(meshSurface, 0x333333);
                    bbHelper.update();

                    // Determine box boundaries based on geometry.
                    var xmin = bbHelper.box.min.x;
                    var xmax = bbHelper.box.max.x;
                    var xmid = 0.5*(xmin + xmax);
                    var xlen = xmax - xmin;

                    var ymin = bbHelper.box.min.y;
                    var ymax = bbHelper.box.max.y;
                    var ymid = 0.5*(ymin + ymax);
                    var ylen = ymax - ymin;

                    var zmin = bbHelper.box.min.z;
                    var zmax = bbHelper.box.max.z;
                    var zmid = 0.5*(zmin + zmax);
                    var zlen = zmax - zmin;

                    var lightX = xmid + 1*xlen;
                    var lightY = ymid + 2*ylen;
                    var lightZ = zmid + 5*zlen;

                    // Camera
                    var camDist = 3*Math.max(xmax - xmin, ymax - ymin, zmax - zmin);
                    camera.position.set(xmid, ymid, zmax + camDist);

                    // Renderer
                    renderer = new THREE.WebGLRenderer({antialias: false});
                    renderer.shadowMapEnabled = true;
                    renderer.setClearColor(new THREE.Color(defaultBackgroundColor, 1.0));
                    renderer.setSize(screenWidth, screenHeight);

                    // Add the output of the renderer to the html element
                    container = document.getElementById("WebGL-output")
                    container.appendChild(renderer.domElement);

                    // Controls
                    controls = new THREE.OrbitControls(camera, renderer.domElement);
                    // this will set the camera position, atempting to use camera.lookAt
                    // will as THREE.OrbitControls will override the camera target position
                    controls.target = new THREE.Vector3(xmid, ymid, zmid);

                    // Light
                    var light = new THREE.SpotLight(0xBBBBBB);
                    light.castShadow = true;
                    light.position.set(xmid + 5*xlen, ymid + 5*ylen, zmid + 5*zlen);
                    light.target.position.set(xmid, ymid, zmid);
                    light.exponent = 1;
                    light.angle = 60 * Math.PI / 180;
                    scene.add(light);
  
                    // Ambient light
                    var lightAmbient = new THREE.AmbientLight(0xffffff);
                    scene.add(lightAmbient);

                    // Axes
                    var origin = new THREE.Vector3(xmin, ymin, zmin);
                    var ex = new THREE.Vector3(xmax, 0, 0);
                    var ey = new THREE.Vector3(0, ymax, 0);
                    var ez = new THREE.Vector3(0, 0, zmax);
                    var xAxis = new THREE.ArrowHelper(ex, origin, xlen, 0xff0000);
                    var yAxis = new THREE.ArrowHelper(ey, origin, ylen, 0x00ff00);
                    var zAxis = new THREE.ArrowHelper(ez, origin, zlen, 0x0000ff);
                    scene.add(xAxis);
                    scene.add(yAxis);
                    scene.add(zAxis);

                    // Planes
                    var el = 5; // length of the planes in xlen, ylen, and zlen units
                    var eps = 1.e-3 * Math.max(xlen, ylen, zlen);
                    var xPlaneGeo = new THREE.PlaneBufferGeometry(el*zlen, el*ylen);
                    var yPlaneGeo = new THREE.PlaneBufferGeometry(el*xlen, el*zlen);
                    var zPlaneGeo = new THREE.PlaneBufferGeometry(el*xlen, el*ylen);
                    var xPlaneMat = new THREE.MeshLambertMaterial( {color: 0x550000, 
                                                                    side: THREE.DoubleSide,
                                                                    transparent: true,
                                                                    opacity: 0.5} );
                    var yPlaneMat = new THREE.MeshLambertMaterial( {color: 0x005500, 
                                                                    side: THREE.DoubleSide,
                                                                    transparent: true,
                                                                    opacity: 0.5} );
                    var zPlaneMat = new THREE.MeshLambertMaterial( {color: 0x000055, 
                                                                    side: THREE.DoubleSide, 
                                                                    transparent: true,
                                                                    opacity: 0.5} );
                    var xPlane = new THREE.Mesh(xPlaneGeo, xPlaneMat);
                    xPlane.rotation.y = - Math.PI/2;
                    xPlane.position.x = xmin - eps; 
                    xPlane.position.y = ymin + el*ylen/2; 
                    xPlane.position.z = zmin + el*zlen/2;
                    var yPlane = new THREE.Mesh(yPlaneGeo, yPlaneMat);
                    yPlane.rotation.x = Math.PI/2;
                    yPlane.position.x = xmin + el*xlen/2;
                    yPlane.position.y = ymin - eps;
                    yPlane.position.z = zmin + el*zlen/2;
                    var zPlane = new THREE.Mesh(zPlaneGeo, zPlaneMat);
                    zPlane.position.x = xmin + el*xlen/2;
                    zPlane.position.y = ymin + el*ylen/2;
                    zPlane.position.z = zmin - eps;

                    // GUI
                    gui = new dat.GUI();
                    parameters = {'background': '#4d576b',
                                  'shininess': 100,
                                  'color': '#aaaaaa',
                                  'emissive': '#000000',
                                  'specular': '#111111',
                                  'edges': false,
                                  'lightX': lightX,
                                  'lightY': lightY,
                                  'lightZ': lightZ,
                                  'planes': false,
                                  'bounding box': false};

                    var sceneFolder = gui.addFolder('scene');
                    var backgroundGui = sceneFolder.addColor(parameters, 'background').name('background').listen();
                    backgroundGui.onChange( function(value) {renderer.setClearColor(value);} );
                    var lightXGui = sceneFolder.add(parameters, 'lightX' ).min(xmid-10*xlen).max(xmid+10*xlen).step(xlen/10.).name('light x').listen();
                    lightXGui.onChange( function(value) {light.position.x = value} );
                    var lightYGui = sceneFolder.add(parameters, 'lightY' ).min(ymid-10*ylen).max(ymid+10*ylen).step(ylen/10.).name('light y').listen();
                    lightYGui.onChange( function(value) {light.position.y = value} );
                    var lightZGui = sceneFolder.add(parameters, 'lightZ' ).min(zmid-10*zlen).max(zmid+10*zlen).step(zlen/10.).name('light z').listen();
                    lightZGui.onChange( function(value) {light.position.z = value} );
                    var scenePlanesGui = sceneFolder.add(parameters, 'planes').listen();
                    scenePlanesGui.onChange( function(value) {
                        if (value) {
                            scene.add(xPlane);
                            scene.add(yPlane);
                            scene.add(zPlane) 
                        } else {
                            scene.remove(xPlane);
                            scene.remove(yPlane);
                            scene.remove(zPlane)
                        } 
                    } );

                    var sceneBBoxGui = sceneFolder.add(parameters, 'bounding box').listen();
                    sceneBBoxGui.onChange( function(value) {
                       if (value) {
                           scene.add(bbHelper);
                       } else {
                           scene.remove(bbHelper);
                       }
                    } );

                    var materialFolder = gui.addFolder('material');
                    var materialShininessGui = materialFolder.add(parameters, 'shininess').min(0).max(100).step(5).listen();
                    materialShininessGui.onChange( function(value) {surface.shininess = value} );

                    if (! geometryHasColor) {
                        var materialColorGui = materialFolder.addColor(parameters, 'color').name('ambient color').listen();
                        materialColorGui.onChange( function(value) {surface.color.setHex(value.replace('#', '0x'));} );
                    }

                    var materialEmissiveGui = materialFolder.addColor(parameters, 'emissive').name('emissive color').listen();
                    materialEmissiveGui.onChange( function(value) {surface.emissive.setHex(value.replace('#', '0x'));} );
                    var materialSpecularGui = materialFolder.addColor(parameters, 'specular').name('specular color').listen();
                    materialSpecularGui.onChange( function(value) {surface.specular.setHex(value.replace('#', '0x'));} );
                    var materialEdgesGui = materialFolder.add(parameters, 'edges').listen();
                    materialEdgesGui.onChange( function(value) {if (value) {scene.add(meshEdges);} else {scene.remove(meshEdges);} } );

                    // Animate
                    animate();
                });
            }

             function animate() {
               requestAnimationFrame(animate);
               render();
               controls.update();
             }

            function render() {
                renderer.render(scene, camera);
            }

            function onWindowResize() {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
                controls.handleResize();
                render();
            }
        </script>
    </body>
</html>
