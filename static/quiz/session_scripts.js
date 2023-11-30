const testName = localStorage.getItem('test_name');
const sectionName = localStorage.getItem('section_name');
const questionsCount = JSON.parse(localStorage.getItem('question_ids')).length;
timer = localStorage.getItem('timer');

document.title = testName;
document.getElementById("test_name").innerHTML = testName;
document.getElementById("section_name").innerHTML = sectionName;
document.getElementById("counter").innerHTML = localStorage.getItem("question_index") + '/' + questionsCount;

if (timer !== "00:00:00") {
    document.getElementById("timer").innerHTML = timer;
}