const units = ["l2_switch", "l1_hub", "host", "l3_router", "server"];
const counters = {};

units.forEach(function (item) {
    counters[item] = parseInt(practiceQuestion[`available_${item}`]);
    document.getElementById(`${item}_counter`).innerHTML = `Доступно: ${counters[item]}`;

    if (counters[item] <= 0) {
        document.getElementById(`${item}`).classList.add('unit-drag-disabled');
    }
});

// Function to update counter value
function updateCounter(unit, value) {
    counters[unit] -= value;
    document.getElementById(`${unit}_counter`).innerText = `Доступно: ${counters[unit]}`;

    // Disable unit dragging when counter reaches zero
    if (counters[unit] <= 0) {
        document.getElementById(`${unit}`).classList.add('unit-drag-disabled');
    } else {
        document.getElementById(`${unit}`).classList.remove('unit-drag-disabled');
    }
}
