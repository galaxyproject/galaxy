let aladin;

A.init.then(() => {
    aladin = A.aladin('#aladin-lite-div', {showCooGridControl: true});
    aladin.displayFITS(file_url)
    aladin.showCooGrid(true);
});