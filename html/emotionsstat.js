var rekEmotions = ["happy", "confused", "sad", "angry", "surprised", "calm"];
var refresh_btn = document.querySelector('#refresh_btn');
var spinner = document.querySelector('#spinner');

function loadSpinner(div) {
    var opts = {
        lines: 13, // The number of lines to draw
        length: 20, // The length of each line
        width: 10, // The line thickness
        radius: 30, // The radius of the inner circle
        corners: 1, // Corner roundness (0..1)
        rotate: 0, // The rotation offset
        direction: 1, // 1: clockwise, -1: counterclockwise
        color: '#000', // #rgb or #rrggbb or array of colors
        speed: 1, // Rounds per second
        trail: 60, // Afterglow percentage
        shadow: false, // Whether to render a shadow
        hwaccel: false, // Whether to use hardware acceleration
        className: 'spinner', // The CSS class to assign to the spinner
        zIndex: 2e9, // The z-index (defaults to 2000000000)
        top: '50%', // Top position relative to parent in px
        left: '50%' // Left position relative to parent in px
    };
    var target = document.getElementById(div);
    spinner = new Spinner(opts).spin(target);
  
    return spinner;
  };

refresh_btn.addEventListener("click", function (e) {
    e.preventDefault();
    spinner = loadSpinner('spinner');
    refreshEmotions();
})

function httpRequestSuccess() { 
    this.callback.apply(this, this.arguments); 
    //if (httpRequest.readyState == XMLHttpRequest.DONE && httpRequest.status == 200) {
    //        
    //}
}

function httpRequestError() { 
    console.error(this.statusText);     
}

function callApiGw(url, callback) {
    httpRequest = new XMLHttpRequest();
    if (!httpRequest) {
        spinner.stop();
        alert('Giving up :( Cannot create an XMLHTTP instance');
    };    
    httpRequest.callback = callback;
    httpRequest.onload = httpRequestSuccess;
    httpRequest.onerror = httpRequestError;
    httpRequest.open("GET", url, true);
    httpRequest.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    httpRequest.setRequestHeader("x-api-key", "IVwpVRJja8A0YItIJx15nvSGxSU9RQ3hnNahs700");
    httpRequest.send(null);
}

function showMessage() {
    response = JSON.parse(this.responseText); 
    console.log(response);           
    if (response["result"]) {     
        //console.log(response["data"]);
        data = JSON.parse(response["data"]);
        console.log("image_url " + data["image_url"]);
        if (data.hasOwnProperty("image_url")) {
            // Getting all the keys
            for (var k in data) {
                var n = k.indexOf("_percentage");
                if (n > 0) {
                    emotion = k.substr(0,n);
                    break;
                } 
            };
            console.log(emotion);
            if (emotion.length > 2) {
                var str_image = "image_" + emotion;
                var str_name = "name_" + emotion;
                var str_score = "score_" + emotion;
                document.getElementById(str_image).src = data["image_url"];
                document.getElementById(str_name).innerHTML = data["first_name"] + ' ' + data["last_name"];
                document.getElementById(str_score).innerHTML = data[emotion + "_percentage"];
            }
        }
    }
}

function refreshEmotions() {  
    for (var i = 0; i < rekEmotions.length; i++) {
        //console.log(rekEmotions[i]);
        apiurl = 'https://awp4ero723.execute-api.us-west-2.amazonaws.com/v1/ath?emotion=' + rekEmotions[i]; 
        callApiGw(apiurl, showMessage);
    }
    spinner.stop();
};
