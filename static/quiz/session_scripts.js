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

    if (remainingTime <= 0) {
        document.querySelector('button[name="nextQuestion"]').disabled = true;
        // document.querySelector('button[name="finishQuiz"]').style.display = 'block';
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
            window.location.href = '/'
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

setInterval(updateTimer, 1000);

// Add event listener for finishQuiz button
document.querySelector('button[name="finishQuiz"]').addEventListener('click', finishQuiz);

// Saving data about session
const testName = localStorage.getItem('test_name');
const sectionName = localStorage.getItem('section_name');
const questionsCount = JSON.parse(localStorage.getItem('question_ids')).length;
timer = localStorage.getItem('timer');

// Display data
document.title = testName;
document.getElementById("test_name").innerHTML = testName;
document.getElementById("section_name").innerHTML = sectionName;
// document.getElementById("question_text").innerHTML = JSON.parse(question)["question_text"];
document.getElementById("counter").innerHTML = localStorage.getItem("question_index") + '/' + questionsCount;

if (timer !== null) {
    document.getElementById("timer").innerHTML = timer;
}

// Set start time for the session
if (localStorage.getItem('question_index') === '1' && localStorage.getItem('quizStartTime') == null) {
    localStorage.setItem('quizStartTime', new Date().getTime().toString());
}

// Get question id
// const question = JSON.parse(document.querySelector('input[name="question"]').value);



