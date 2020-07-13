var ath_btn = document.querySelector('#athqueries_btn');

ath_btn.addEventListener("click", function (e) {
    e.preventDefault();
    spinner = loadSpinner('spinner');
    runQueries();
})

function runQueries() {
    httpRequest = new XMLHttpRequest();
    if (!httpRequest) {
        spinner.stop();
        alert('Giving up :( Cannot create an XMLHTTP instance');
    }

    httpRequest.open('GET', 'https://awp4ero723.execute-api.us-west-2.amazonaws.com/v1/ath');
    httpRequest.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    httpRequest.setRequestHeader("x-api-key", "IVwpVRJja8A0YItIJx15nvSGxSU9RQ3hnNahs700");
    httpRequest.send();
    httpRequest.onreadystatechange = function () {//Call a function when the state changes.      
        if (httpRequest.readyState == XMLHttpRequest.DONE && httpRequest.status == 200) {
            response = JSON.parse(httpRequest.responseText);
            if (response["result"]) {
                spinner.stop();
                swal('Success', 'Queries submitted', 'success');
            }
            else {
                spinner.stop();
                swal('Oops..', response["msg"], 'error');
            }
        }
        else {
            spinner.stop();
            swal('Error', httpRequest.status, 'error');
        }
    };
}
