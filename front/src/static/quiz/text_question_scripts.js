function displayVariable(answersParsed) {
    const buttonType = correctCount === "1" ? 'radio' : 'checkbox'
    const buttonId = correctCount === "1" ? "flexRadioDefault" : "flexCheckDefault"
    const answer = sessionStorage.getItem("answer")
    $('#variants.container').append(`<div class="form-group" id="variants"></div>`)
    for (let i = 0; i < answersParsed.length; i++) {
        const value = answersParsed[i]['variant']
        $('#variants.form-group')
            .append(`<div class=form-check>
                        <input class=form-check-input type=${buttonType} name=${buttonId} id=${buttonId}${i} ${answer ? "disabled" : ""}>
                        <label class=form-check-label for=${buttonId}${i}>${value}</label>
                     </div>`);
    }
}

function displayMatching(answersParsed) {
    $('#variants.container')
        .css({display: "flex"})
        .append(`<div class=keys id=sortContainer></div><div class=values id=rightSide></div>`);

    let left = [];
    let right = [];
    for (let i = 0; i < answersParsed.length; i++) {
        left.push(answersParsed[i]["left"]);
        right.push(answersParsed[i]["right"]);
    }
    // shuffle left side
    left.sort(() => Math.random() - 0.5);

    for (let i = 0; i < left.length; i++) {
        $('#sortContainer.keys').append(`<div id=${left[i]} class=sortable>${left[i]}</div>`);
        $('#rightSide.values').append(`<div id=${right[i]} class=matching>${right[i]}</div>`);
    }
}

function displaySorting(answersParsed) {
    $('#variants.container')
        .css({display: "flex"})
        .append(`<div class=keys id=sortContainer></div>`)

    for (let i = 0; i < answersParsed.length; i++) {
        const value = answersParsed[i]['variant']
        $('#sortContainer.keys').append(`<div id=${value} class=sortable>${value}</div>`);
    }
}

// Make divs with id="sortContainer" sortable
$(() => $('#sortContainer').sortable({placeholder: 'emptySpace'}));
