function updateRadioOrder() {
    const radios = answersContainer.querySelectorAll('.answer-radio');

    radios.forEach((radio, index) => {
        radio.value = index;
    });
}

function updateRadioNames() {
    const answerType = document.querySelector('input[name="answer_type"]:checked').value;
    const radioName = answerType === 'single' ? 'correct_answer' : 'correct_answers[]';

    const radios = answersContainer.querySelectorAll('.answer-radio');
    radios.forEach((r, index) => {
        r.name = radioName;
//        if (answerType === 'single' && index === 0) {
//            r.checked = true;
//        }
    });
}

const InitializeAnswerControls = function() {
    const answersContainer = document.getElementById('answersContainer');

    answersContainer.addEventListener('click', function(e) {
        const deleteBtn = e.target.closest('.delete');
        if (deleteBtn) {
            const answerItem = deleteBtn.closest('.answer-item');
            if (answersContainer.children.length > 1) {
                answerItem.remove();
                updateRadioNames();
            } else {
                alert('Должен быть хотя бы один вариант ответа');
            }
        }

        const moveUpBtn = e.target.closest('.move-up');
        if (moveUpBtn) {
            const answerItem = moveUpBtn.closest('.answer-item');
            const prevItem = answerItem.previousElementSibling;
            if (prevItem) {
                answersContainer.insertBefore(answerItem, prevItem);
            }
        }

        const moveDownBtn = e.target.closest('.move-down');
        if (moveDownBtn) {
            const answerItem = moveDownBtn.closest('.answer-item');
            const nextItem = answerItem.nextElementSibling;
            if (nextItem) {
                answersContainer.insertBefore(nextItem, answerItem);
            }
        }

        updateRadioOrder();
    });

    // Drag and Drop
    let draggedItem = null;

    answersContainer.addEventListener('dragstart', function(e) {
        if (e.target.classList.contains('answer-item')) {
            draggedItem = e.target;
            setTimeout(() => {
                e.target.classList.add('dragging');
            }, 0);
        }
        updateRadioOrder();
    });

    answersContainer.addEventListener('dragend', function(e) {
        if (e.target.classList.contains('answer-item')) {
            e.target.classList.remove('dragging');
            draggedItem = null;
        }
        updateRadioOrder();
    });

    answersContainer.addEventListener('dragover', function(e) {
        e.preventDefault();
        const afterElement = getDragAfterElement(answersContainer, e.clientY);
        if (draggedItem) {
            if (afterElement == null) {
                answersContainer.appendChild(draggedItem);
            } else {
                answersContainer.insertBefore(draggedItem, afterElement);
            }
        }
        updateRadioOrder();
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.answer-item:not(.dragging)')];

        updateRadioOrder();

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;

            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
}

const InitializeQuestionMatchForm = function() {
    const answersContainer = document.getElementById('answersContainer');
    const addAnswerBtn = document.getElementById('addAnswer');
    let answerCounter = 1;

    addAnswerBtn.addEventListener('click', function() {
        answerCounter++;

        const answerItem = document.createElement('div');
        answerItem.className = 'answer-item';
        answerItem.draggable = true;
        answerItem.innerHTML = `
            <input type="text" class="answer-input" name="answer_text_left[]" value="" placeholder="" required>
            <div class="answer-separator">
                <i class='bx bx-transfer' style='color: #9ca3af; font-size: 16px;'></i>
            </div>
            <input type="text" class="answer-input" name="answer_text_right[]" value="" placeholder="" required>
            <div class="answer-actions">
                <button type="button" class="delete" title="Удалить"><i class="bx bx-x"></i></button>
            </div>
        `;

        answersContainer.appendChild(answerItem);
    });

    InitializeAnswerControls();
}

const InitializeQuestionOrderForm = function() {
    const answersContainer = document.getElementById('answersContainer');
    const addAnswerBtn = document.getElementById('addAnswer');
    let answerCounter = 1;

    addAnswerBtn.addEventListener('click', function() {
        answerCounter++;

        const answerItem = document.createElement('div');
        answerItem.className = 'answer-item';
        answerItem.draggable = true;
        answerItem.innerHTML = `
            <i class="bx bx-dots-vertical-rounded drag-handle"></i>
            <input type="text" class="answer-input" name="answer_text[]" value="" placeholder="Введите вариант ответа" required>
            <div class="answer-actions">
                <button type="button" class="move-up" title="Вверх"><i class="bx bx-chevron-up"></i></button>
                <button type="button" class="move-down" title="Вниз"><i class="bx bx-chevron-down"></i></button>
                <button type="button" class="delete" title="Удалить"><i class="bx bx-x"></i></button>
            </div>
        `;

        answersContainer.appendChild(answerItem);
    });

    InitializeAnswerControls();
};

const InitializeQuestionSelectForm = function() {
    const answersContainer = document.getElementById('answersContainer');
    const addAnswerBtn = document.getElementById('addAnswer');
    const answerTypeRadios = document.querySelectorAll('input[name="answer_type"]');
    let answerCounter = 1;

    addAnswerBtn.addEventListener('click', function() {
        answerCounter++;
        const answerType = document.querySelector('input[name="answer_type"]:checked').value;
        const inputType = answerType === 'single' ? 'radio' : 'checkbox';
        const radioName = answerType === 'single' ? 'correct_answer' : 'correct_answers[]';

        const answerItem = document.createElement('div');
        answerItem.className = 'answer-item';
        answerItem.draggable = true;
        answerItem.innerHTML = `
            <i class="bx bx-dots-vertical-rounded drag-handle"></i>
            <input type="${inputType}" name="${radioName}" class="answer-radio">
            <input type="text" class="answer-input" name="answer_text[]" value="" placeholder="Введите вариант ответа" required>
            <div class="answer-actions">
                <button type="button" class="move-up" title="Вверх"><i class="bx bx-chevron-up"></i></button>
                <button type="button" class="move-down" title="Вниз"><i class="bx bx-chevron-down"></i></button>
                <button type="button" class="delete" title="Удалить"><i class="bx bx-x"></i></button>
            </div>
        `;

        answersContainer.appendChild(answerItem);
        updateRadioNames();
        updateRadioOrder();
    });

    answerTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const inputType = this.value === 'single' ? 'radio' : 'checkbox';
            const radioName = this.value === 'single' ? 'correct_answer' : 'correct_answers[]';

            const radios = answersContainer.querySelectorAll('.answer-radio');
            radios.forEach((r, index) => {
                r.type = inputType;
                r.name = radioName;
                if (this.value === 'single' && index === 0) {
                    r.checked = true;
                } else {
                    r.checked = false;
                }
            });
        });
    });

    InitializeAnswerControls();
};