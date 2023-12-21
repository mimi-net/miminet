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

// Make divs with id="sortContainer" sortable
$(() => $('#sortContainer').sortable({placeholder: 'emptySpace'}));
