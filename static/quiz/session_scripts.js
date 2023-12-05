const questionIds = JSON.parse(localStorage.getItem('question_ids'));
const questionIndex = parseInt(localStorage.getItem('question_index'));

function timeToMilliseconds(timeString) {
    const [hours, minutes, seconds] = timeString.split(':');
    const totalSeconds = parseInt(hours, 10) * 3600 + parseInt(minutes, 10) * 60 + parseInt(seconds, 10);
    return totalSeconds * 1000;
}

function updateTimer() {
    // Time in ms
    const startTime = parseInt(localStorage.getItem('quizStartTime'));
    const duration = timeToMilliseconds(localStorage.getItem('timer'));

    const currentTime = new Date().getTime();
    const elapsedTime = currentTime - startTime;
    const remainingTime = Math.max(duration - elapsedTime, 0);

    let hours = Math.floor(remainingTime / (60 * 60 * 1000));
    let minutes = Math.floor(remainingTime / (60 * 1000)) % 60;
    let seconds = Math.floor((remainingTime / 1000) % 60);

    hours = (hours < 10) ? "0" + hours : hours;
    minutes = (minutes < 10) ? "0" + minutes : minutes;
    seconds = (seconds < 10) ? "0" + seconds : seconds;

    document.getElementById('timer').textContent = hours + ":" + minutes + ":" + seconds;

    if (remainingTime <= 0 || questionIndex + 1 >= questionsCount) {
        document.querySelector('button[name="nextQuestion"]').disabled = true;
    }
}

function finishQuiz(event) {
    const sessionId = localStorage.getItem('session_id');

    fetch(finishSessionUrl + '?id=' + sessionId, {
        method: 'PUT'
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);

            localStorage.clear();
            // TODO: show results
            window.location.href = '/'
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function getAnswer() {
    const leftSide = $('#sortContainer').sortable("toArray");
    const rightSide = $('#rightSide div').map(function () {
        return this.id
    }).get();
    console.log(leftSide);
    console.log(rightSide);
}

function nextQuestion(event) {
    // TODO: make answerQuestion request
    // redirect to next question
    const questionId = questionIds[questionIndex];

    getAnswer();

    localStorage.setItem('question_index', (questionIndex + 1).toString());

    window.location.href = getQuestionUrl + `?question_id=` + questionIds[questionIndex + 1];


    // fetch(answerQuestionURL + '?id=' + questionId, {
    //     method: 'POST',
    //     // body:
    // })
    //     .then(response => response.json())
    //     .then(data => {
    //         console.log(data);
    //
    //         localStorage.clear();
    //         window.location.href = '/'
    //     })
    //     .catch(error => {
    //         console.error('Error:', error);
    //     });
}

function displayVariable(variant, index) {
    $('#variants.container').append(`<div class=form-check><input class=form-check-input type=checkbox value=${index} id=flexCheckDefault><label class=form-check-label for=flexCheckDefault>${variant}</label></div>`);
}

function displayMatching(key, value) {
    $('#sortContainer.keys').append(`<div id=${key} class=sortable>${key}</div>`);
    $('#rightSide.values').append(`<div id=${value}>${value}</div>`);
}

function displaySorting(value) {
    $('#sortContainer.keys').append(`<div id=${value} class=sortable>${value}</div>`);
}

setInterval(updateTimer, 1000);

// Add event listener for finishQuiz and nextQuestion buttons
document.querySelector('button[name="finishQuiz"]').addEventListener('click', finishQuiz);
document.querySelector('button[name="nextQuestion"]').addEventListener('click', nextQuestion);

// Saving data about session
const testName = localStorage.getItem('test_name');
const sectionName = localStorage.getItem('section_name');
const questionsCount = JSON.parse(localStorage.getItem('question_ids')).length;
timer = localStorage.getItem('timer');

// Display data
document.title = testName;
document.getElementById("test_name").innerHTML = testName;
document.getElementById("section_name").innerHTML = sectionName;
document.getElementById("counter").innerHTML = (questionIndex + 1) + '/' + questionsCount;

if (timer !== null) {
    document.getElementById("timer").innerHTML = timer;
}

// Set start time for the session
if (questionIndex === 0 && localStorage.getItem('quizStartTime') == null) {
    localStorage.setItem('quizStartTime', new Date().getTime().toString());
}
