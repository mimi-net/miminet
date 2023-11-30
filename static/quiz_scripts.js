function morph(int, array) {
    return (array = array || ['раздел', 'раздела', 'разделов']) && array[(int % 100 > 4 && int % 100 < 20) ? 2 : [2, 0, 1, 1, 1, 2][(int % 10 < 5) ? int % 10 : 5]];
}

function timeToMinutes(timeString) {
    const [hours, minutes, seconds] = timeString.split(':');
    const totalSeconds = parseInt(hours, 10) * 3600 + parseInt(minutes, 10) * 60 + parseInt(seconds, 10);
    return Math.ceil(totalSeconds / 60);
}

function findParent(element) {
    while (element && element.tagName !== 'FORM') {
        element = element.parentNode;
    }

    return element;
}

function submitForm(event) {
    const form = findParent(event.target);
    // const sectionId = form.getAttribute('name');
    const questionIndex = parseInt(form.querySelector('[name="question_index"]').value);
    const sectionName = form.querySelector(`[name="section_name"]`).value

    fetch(form.action, {
        method: form.method,
        body: new FormData(form)
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            console.log(data.session_question_ids);
            console.log(data.session_question_ids.type);

            sessionStorage.setItem("section_name", sectionName)
            sessionStorage.setItem("session_id", data.quiz_session_id)
            sessionStorage.setItem("question_ids", JSON.stringify(data.session_question_ids))
            sessionStorage.setItem("question_index", (questionIndex+1).toString())

            if (questionIndex < data.session_question_ids.length) {
                window.location.href = endpointUrl + `?question_id=` + data.session_question_ids[questionIndex];
            } else {
                window.location.href = "/quiz/session/finish?id=" + data.quiz_session_id;
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

