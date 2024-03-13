function displayVariable(answersParsed) {
    for (let i = 0; i < answersParsed.length; i++) {
        const value = answersParsed[i]['variant']
        $('#variants.container')
            .append(`<div class=form-check><input class=form-check-input type=checkbox value=${value} id=flexCheckDefault><label class=form-check-label for=flexCheckDefault>${value}</label></div>`);
    }
}

// TODO: shuffle sides
function displayMatching(answersParsed) {
    $('#variants.container')
        .css({display: "flex"})
        .append(`<div class=keys id=sortContainer></div><div class=values id=rightSide></div>`);

    for (let i = 0; i < answersParsed.length; i++) {
        const value = answersParsed[i];
        $('#sortContainer.keys').append(`<div id=${value["left"]} class=sortable>${value["left"]}</div>`);
        $('#rightSide.values').append(`<div id=${value["right"]} class=matching>${value["right"]}</div>`);
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
