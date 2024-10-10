function updateTimer() {
    // Time in ms
    const startTime = parseInt(sessionStorage.getItem('quizStartTime'));
    // Convert minutes to milliseconds
    const duration = (sessionStorage.getItem('timer')) * 60000;

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
        if (isLastQuestion) {
            $('button[name="seeResults"]')?.prop('hidden', false);
            $('button[name="answerQuestion"]')?.prop('hidden', true);
            $('button[name="finishQuiz"]')?.prop('hidden', true);
        }

        $('button[name="nextQuestion"]')?.prop('disabled', true);
        $('button[name="answerQuestion"]')?.prop('disabled', true);
    }
}

function seeResults() {
    window.removeEventListener('beforeunload', handleUnload);
    finishQuiz();
}

function finishQuiz() {
    const sessionId = sessionStorage.getItem('session_id');
    if (!sessionId) {
        return;
    }

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

function RunAndWaitSimulation(network_guid) {
    RunSimulation(network_guid);

    return new Promise(function (resolve, reject) {
        function checkReady(hop) {
            if (packets !== "null" && packets !== undefined && packets !== null) {
                resolve(packets)
            } else {
                if (hop > 15) {
                    reject(new Error("Exceeded simulation wait time"))
                }
                setTimeout(function () {
                    checkReady(hop + 1)
                }, 2000)
            }
        }

        checkReady(0)
    })
}

async function getAnswer() {
    if (questionType !== "practice") {
        switch (questionType) {
            case 'variable':
                const checked = $('input.form-check-input:checked');
                if ($('input[type=radio].form-check-input').length !== 0) {
                    return [{'variant': checked.siblings('label').text()}];
                }
                return checked.map(function () {
                    return {'variant': $(this).siblings('label').text()};
                }).get();
            case 'matching':
                const leftSide = $('#sortContainer div').map(function () {
                    return $(this).text();
                }).get();
                const rightSide = $('#rightSide div').map(function () {
                    return $(this).text();
                }).get();
                let resultArray = [];
                leftSide.forEach((leftValue, index) => {
                    resultArray.push({
                        "left": leftValue,
                        "right": rightSide[index]
                    });
                });
                return resultArray;
            case 'sorting':
                let sortableArray = $('#sortContainer div').map(function () {
                    return $(this).text();
                }).get();
                let dictionary = {};
                sortableArray.forEach((value, index) => {
                    dictionary[index] = value;
                });
                return dictionary;
        }
    }
    if (questionType === "practice") {
        if (packets === "null" || packets === undefined || packets === null || packets === "") {
            // simulate and get packets
            if (!jobs.length) {
                $('#noJobsModal').modal('toggle');
                return;
            }

            await RunAndWaitSimulation(network_guid).catch((error) => console.log(error))
            return {'nodes': nodes, 'edges': edges, 'packets': packets}
        } else {
            return {'nodes': nodes, 'edges': edges, 'packets': packets}
        }
    }
}

function nextQuestion() {
    window.removeEventListener('beforeunload', handleUnload);
    // redirect to next question
    sessionStorage.setItem('question_index', (questionIndex + 1).toString());
    sessionStorage.removeItem('explanation');
    sessionStorage.removeItem('answer');
    sessionStorage.removeItem('is_correct');

    window.location.href = getQuestionUrl + `?question_id=` + questionIds[questionIndex + 1];
}

function changeVisibility(is_correct) {
    document.querySelector('button[name="answerQuestion"]').hidden = true;
    document.querySelector('button[name="nextQuestion"]').hidden = isLastQuestion;

    if (isLastQuestion) {
        document.querySelector('button[name="finishQuiz"]').hidden = true;
        document.querySelector('button[name="seeResults"]').hidden = false;

        document.querySelector('button[name="seeResults"]').classList.add(is_correct ? 'btn-outline-success' : 'btn-outline-danger');
        document.querySelector('button[name="seeResults"]').textContent = is_correct ? 'Верно! Посмотреть резульататы' : 'Неверно! Посмотреть резульататы';
    } else {
        document.querySelector('button[name="nextQuestion"]').classList.add(is_correct ? 'btn-outline-success' : 'btn-outline-danger');
        document.querySelector('button[name="nextQuestion"]').textContent = is_correct ? 'Верно! Следующий вопрос' : 'Неверно! Следующий вопрос';
    }
}

async function answerQuestion() {
    const questionId = questionIds[questionIndex];

    let playerDiv = document.getElementById("NetworkPlayerDiv")

    if (playerDiv) {
        playerDiv.hidden = true;
    }

    document.querySelector('button[name="answerQuestion"]').textContent = "Проверка..."
    document.querySelector('button[name="answerQuestion"]').disabled = true

    if (sessionStorage.getItem('answer')) {
        return;
    }
    const answer = await getAnswer();
    sessionStorage.setItem('answer', JSON.stringify(answer));
    // console.log(JSON.stringify(answer));
    if (answer === undefined) {
        if (playerDiv) {
            playerDiv.hidden = false;
        }
        document.querySelector('button[name="answerQuestion"]').textContent = "Ответить";
        document.querySelector('button[name="answerQuestion"]').disabled = false;
        return;
    }

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
            sessionStorage.setItem('is_correct', data['is_correct']);
            sessionStorage.setItem('explanation', data['explanation']);
            changeVisibility(data['is_correct']);
            displayExplanation(data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function displayExplanation(data) {
    if (!data['explanation']) {
        return;
    }
    $('#explanation.container')
        .removeAttr('hidden')
        .append(`<text>${data['explanation']}</text>`);
}

window.onload = function () {
    const answer = sessionStorage.getItem('answer');
    if (answer) {
        const is_correct = sessionStorage.getItem('is_correct') === "true";
        displayExplanation({"explanation": sessionStorage.getItem('explanation')});
        $('#sortContainer').sortable("disable");
        changeVisibility(is_correct);
    }
}

function handleUnload(e) {
    e.preventDefault();
    e.returnValue = '';
}

window.addEventListener('beforeunload', handleUnload);

// Markdown convert
let questionText = document.querySelector('div[id="question_text"]')?.innerHTML;
const converter = new showdown.Converter();
const html = converter.makeHtml(questionText);

// Parse html string
const parser = new DOMParser();
const doc = parser.parseFromString(html, 'text/html');
const documentChildren = doc.body.children;

// Append html elements
let textField = document.querySelector('div[id="question_text"]')
textField.innerHTML = ""
for (const child of documentChildren) {
    textField.appendChild(child.cloneNode(true))
}

// If there's a code, unescape string
const codeElement = document.getElementsByTagName("code")[0]
if (codeElement) {
    codeElement.textContent = _.unescape(codeElement.textContent)
}

// Saving data about session
const testName = sessionStorage.getItem('test_name');
const sectionName = sessionStorage.getItem('section_name');
const questionsCount = JSON.parse(sessionStorage.getItem('question_ids')).length;
timer = sessionStorage.getItem('timer');
const questionIds = JSON.parse(sessionStorage.getItem('question_ids'));
const questionIndex = parseInt(sessionStorage.getItem('question_index'));
const isLastQuestion = questionIndex + 1 >= questionsCount;

if (timer !== null) {
    setInterval(updateTimer, 1000);

    document.getElementById("timer").innerHTML = timer;

    // Set start time for the session
    if (questionIndex === 0 && sessionStorage.getItem('quizStartTime') == null) {
        sessionStorage.setItem('quizStartTime', new Date().getTime().toString());
    }
}

// Add event listener for finishQuiz and nextQuestion buttons
document.querySelector('button[name="finishQuiz"]')?.addEventListener('click', finishQuiz);
document.querySelector('button[name="seeResults"]')?.addEventListener('click', seeResults);
document.querySelector('button[name="answerQuestion"]')?.addEventListener('click', answerQuestion);
document.querySelector('button[name="nextQuestion"]')?.addEventListener('click', nextQuestion);

// Display data
document.title = testName;
document.getElementById("test_name").innerHTML = testName;
document.getElementById("slash_symbol").innerHTML = sectionName ? " / " : "";
document.getElementById("section_name").innerHTML = sectionName;
document.getElementById("counter").innerHTML = (questionIndex + 1) + '/' + questionsCount;
