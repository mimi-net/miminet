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

function finishQuiz() {
    window.removeEventListener('beforeunload', handleUnload);
    const sessionId = sessionStorage.getItem('session_id');

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

    window.location.href = getQuestionUrl + `?question_id=` + questionIds[questionIndex + 1];
}

async function answerQuestion() {
    const questionId = questionIds[questionIndex];

    let playerDiv = document.getElementById("NetworkPlayerDiv")

    if (playerDiv) {
        playerDiv.hidden = true;
    }

    document.querySelector('button[name="answerQuestion"]').textContent = "Проверка..."
    document.querySelector('button[name="answerQuestion"]').disabled = true

    const answer = await getAnswer();
    // console.log(JSON.stringify(answer));
    if (answer === undefined) {
        if (playerDiv) {
            playerDiv.hidden = false;
        }
        document.querySelector('button[name="answerQuestion"]').textContent = "Ответить"
        document.querySelector('button[name="answerQuestion"]').disabled = false
        return;
    }

    document.querySelector('button[name="answerQuestion"]').hidden = true;
    document.querySelector('button[name="nextQuestion"]').hidden = isLastQuestion;

    if (isLastQuestion) {
        document.querySelector('button[name="seeResults"]').hidden = false;
        document.querySelector('button[name="finishQuiz"]').hidden = true;
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
        .append(`<text>${phrase}</text><br><text>${data['explanation'] ?? ""}</text>`);
}

function handleUnload(e) {
    e.preventDefault();
    e.returnValue = '';
}

window.addEventListener('beforeunload', handleUnload);

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
document.querySelector('button[name="seeResults"]')?.addEventListener('click', finishQuiz);
document.querySelector('button[name="answerQuestion"]')?.addEventListener('click', answerQuestion);
document.querySelector('button[name="nextQuestion"]')?.addEventListener('click', nextQuestion);

// Display data
document.title = testName;
document.getElementById("test_name").innerHTML = testName;
document.getElementById("section_name").innerHTML = sectionName;
document.getElementById("counter").innerHTML = (questionIndex + 1) + '/' + questionsCount;
