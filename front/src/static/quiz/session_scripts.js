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

    if (remainingTime <= 0) {
        if (questionIndex + 1 >= questionsCount) {
            document.querySelector('button[name="seeResults"]').hidden = false;
            document.querySelector('button[name="answerQuestion"]').hidden = true;
        }
        document.querySelector('button[name="nextQuestion"]').disabled = true;
        document.querySelector('button[name="answerQuestion"]').disabled = true;
    }
}

function finishQuiz() {
    const sessionId = localStorage.getItem('session_id');

    fetch(finishSessionUrl + '?id=' + sessionId, {
        method: 'PUT'
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);

            window.location.href = sessionResultUrl + '?id=' + sessionId
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function getAnswer() {
    switch (textType) {
        case 'variable':
            return $('input.form-check-input:checked').map(function () {
                return {'answer_text': this.value};
            }).get();
        case 'matching':
            const leftSide = $('#sortContainer').sortable("toArray");
            const rightSide = $('#rightSide div').map(function () {
                return this.id
            }).get();
            return leftSide.reduce((acc, current, index) => {
                acc[current] = rightSide[index];
                return acc;
            }, {});
        case 'sorting':
            return $('#sortContainer').sortable("toArray").join(' ');
    }


}

function nextQuestion() {
    // redirect to next question
    localStorage.setItem('question_index', (questionIndex + 1).toString());

    window.location.href = getQuestionUrl + `?question_id=` + questionIds[questionIndex + 1];
}

function answerQuestion() {
    const questionId = questionIds[questionIndex];

    document.querySelector('button[name="answerQuestion"]').hidden = true;
    document.querySelector('button[name="nextQuestion"]').hidden = (questionIndex + 1 >= questionsCount);

    if (questionIndex + 1 >= questionsCount) {
        document.querySelector('button[name="seeResults"]').hidden = false;
        document.querySelector('button[name="finishQuiz"]').hidden = true;
    }

    const answer = getAnswer();
    console.log(JSON.stringify(answer));

    fetch(answerQuestionURL + '?id=' + questionId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({'answer': answer})
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);

            displayExplanation(data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function displayExplanation(data) {
    const borderColor = data['is_correct'] ? '#63F297' : '#F26963'
    const phrase = data['is_correct'] ? 'Верно!\n' : 'Неверно!\n'
    $('#explanation.container')
        .removeAttr('hidden')
        .css({borderColor: borderColor})
        .append(`<text>${phrase}</text><br><text>${data['explanation']}</text>`);
}

function displayVariable(answersParsed) {
    for (let i = 0; i < answersParsed.length; i++) {
        const value = answersParsed[i]['answer_text']
        $('#variants.container')
            .append(`<div class=form-check><input class=form-check-input type=checkbox value=${value} id=flexCheckDefault><label class=form-check-label for=flexCheckDefault>${value}</label></div>`);
    }
}

function displayMatching(answersParsed) {
    $('#variants.container')
        .css({display: "flex"})
        .append(`<div class=keys id=sortContainer></div><div class=values id=rightSide></div>`);

    for (const item in answersParsed) {
        if (answersParsed.hasOwnProperty(item)) {
            const value = answersParsed[item];
            $('#sortContainer.keys').append(`<div id=${item} class=sortable>${item}</div>`);
            $('#rightSide.values').append(`<div id=${value} class=matching>${value}</div>`);
        }
    }
}

function displaySorting(answersParsed) {
    $('#variants.container')
        .css({display: "flex"})
        .append(`<div class=keys id=sortContainer></div>`)

    for (let i = 0; i < answersParsed.length; i++) {
        const value = answersParsed[i];
        $('#sortContainer.keys').append(`<div id=${value} class=sortable>${value}</div>`);
    }
}

// Saving data about session
const testName = localStorage.getItem('test_name');
const sectionName = localStorage.getItem('section_name');
const questionsCount = JSON.parse(localStorage.getItem('question_ids')).length;
timer = localStorage.getItem('timer');

if (timer !== null) {
    setInterval(updateTimer, 1000);

    document.getElementById("timer").innerHTML = timer;

    // Set start time for the session
    if (questionIndex === 0 && localStorage.getItem('quizStartTime') == null) {
        localStorage.setItem('quizStartTime', new Date().getTime().toString());
    }
}

// Add event listener for finishQuiz and nextQuestion buttons
document.querySelector('button[name="finishQuiz"]').addEventListener('click', finishQuiz);
document.querySelector('button[name="seeResults"]').addEventListener('click', finishQuiz);
document.querySelector('button[name="answerQuestion"]').addEventListener('click', answerQuestion);
document.querySelector('button[name="nextQuestion"]').addEventListener('click', nextQuestion);

if (questionIndex + 1 >= questionsCount) {
    document.querySelector('button[name="nextQuestion"]').hidden = true;
    // document.querySelector('button[name="finishQuiz"]').hidden = true;
}

// Display data
document.title = testName;
document.getElementById("test_name").innerHTML = testName;
document.getElementById("section_name").innerHTML = sectionName;
document.getElementById("counter").innerHTML = (questionIndex + 1) + '/' + questionsCount;
