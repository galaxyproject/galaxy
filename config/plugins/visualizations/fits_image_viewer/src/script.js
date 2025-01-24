var aladin;

function initializeAladinLite() {
    A.init.then(() => {
        aladin = A.aladin('#aladin-lite-div', {showCooGridControl: true});
        aladin.displayFITS(fileUrl)
        aladin.showCooGrid(true);
    });
}

function localScriptLoadingError() {
    addScriptToHead(appRoot+aladinLiteScriptAlternativeLocation);
}

function cdnLoadingError() {
    addScriptToHead(appRoot+aladinLiteScriptLocation, localScriptLoadingError);
}

function addScriptToHead(url, onerrorFunction) {
    const scriptToAdd = document.createElement("script");
    scriptToAdd.onload = initializeAladinLite;

    if(onerrorFunction) {
        scriptToAdd.onerror = onerrorFunction
    }

    document.head.appendChild(scriptToAdd);
    scriptToAdd.src = url;
}

addScriptToHead(aladinLiteCDNUrl, cdnLoadingError);
