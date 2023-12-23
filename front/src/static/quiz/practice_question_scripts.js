const units = ["switches", "hubs", "hosts", "routers", "servers"]

units.forEach(function (item) {
    document.getElementById(`${item}_counter`).innerHTML = 'Доступно:' + practiceQuestion[`available_${item}`];
});