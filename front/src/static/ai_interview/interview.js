(function () {
    const script = document.currentScript;
    const config = window.aiInterviewConfig || {
        stateUrl: script.dataset.stateUrl,
        interviewPageUrl: script.dataset.interviewPageUrl,
        startUrl: script.dataset.startUrl,
        answerUrl: script.dataset.answerUrl,
        resultUrl: script.dataset.resultUrl,
        resultPageBaseUrl: script.dataset.resultPageBaseUrl,
        resultGuid: script.dataset.resultGuid || null
    };
    const errorBox = document.getElementById("ai-interview-error");
    const noticeBox = document.getElementById("ai-interview-notice");
    const statusBox = document.getElementById("ai-interview-status");
    const closedPanel = document.getElementById("ai-interview-closed");
    const startPanel = document.getElementById("ai-interview-start");
    const sessionPanel = document.getElementById("ai-interview-session");
    const resultPanel = document.getElementById("ai-interview-result");
    const historyPanel = document.getElementById("ai-interview-history-panel");
    const startForm = document.getElementById("ai-interview-start-form");
    const startButton = document.getElementById("ai-interview-start-button");
    const accessCodeInput = document.getElementById("ai-interview-access-code");
    const answerForm = document.getElementById("ai-interview-answer-form");
    const answerButton = document.getElementById("ai-interview-answer-button");
    const answerInput = document.getElementById("ai-interview-answer");
    const charCount = document.getElementById("ai-interview-char-count");
    let currentTurn = null;
    let waiting = false;

    function setVisible(element, visible) {
        if (!element) {
            return;
        }
        element.classList.toggle("d-none", !visible);
    }

    function setError(message) {
        errorBox.textContent = message || "";
        setVisible(errorBox, Boolean(message));
    }

    function setNotice(message) {
        if (!noticeBox) {
            return;
        }
        noticeBox.textContent = message || "";
        setVisible(noticeBox, Boolean(message));
    }

    function escapeHtml(value) {
        const node = document.createElement("span");
        node.textContent = value || "";
        return node.innerHTML;
    }

    function listInto(elementId, items) {
        const element = document.getElementById(elementId);
        element.innerHTML = "";
        (items || []).forEach(function (item) {
            const li = document.createElement("li");
            li.textContent = item;
            element.appendChild(li);
        });
    }

    function formatDate(value) {
        if (!value) {
            return "";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return "";
        }
        return date.toLocaleString("ru-RU", {
            day: "2-digit",
            month: "long",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
        });
    }

    function setWaiting(value) {
        waiting = value;
        if (startButton) {
            startButton.disabled = value;
        }
        if (answerButton) {
            answerButton.disabled = value;
        }
        if (answerInput) {
            answerInput.disabled = value;
        }
    }

    function renderResult(result) {
        setNotice("");
        setVisible(startPanel, false);
        setVisible(sessionPanel, false);
        setVisible(resultPanel, true);
        setVisible(closedPanel, false);
        setVisible(historyPanel, false);
        document.getElementById("ai-interview-grade").textContent = result.grade;
        document.getElementById("ai-interview-verdict").textContent = result.verdict || "";
        listInto("ai-interview-strengths", result.strengths);
        listInto("ai-interview-gaps", result.gaps);
        listInto("ai-interview-recommendations", result.recommendations);
        const totalQuestions = (result.questions || []).length;
        document.getElementById("ai-interview-result-questions").innerHTML =
            (result.questions || []).map(function (turn) {
                return "<article class=\"border rounded p-3\">" +
                    "<div class=\"text-muted\">Вопрос " + turn.position + " из " + totalQuestions + "</div>" +
                    "<h4 class=\"h6 mt-2\">" + escapeHtml(turn.question) + "</h4>" +
                    "<p class=\"mb-1\"><strong>Ответ:</strong> " + escapeHtml(turn.answer) + "</p>" +
                    "<p class=\"mb-0 text-muted\">" + escapeHtml(turn.answer_summary) + "</p>" +
                    "</article>";
            }).join("");
        if (answerInput) {
            answerInput.disabled = true;
        }
        if (answerButton) {
            answerButton.disabled = true;
        }
    }

    function renderHistory(history) {
        const container = document.getElementById("ai-interview-history");
        if (!container) {
            return;
        }
        if (!history || !history.length) {
            container.innerHTML = "<div class=\"text-muted\">Попыток пока нет</div>";
            return;
        }
        container.innerHTML = history.map(function (item) {
            const topics = (item.topics || []).map(function (topic) {
                return topic.label;
            }).join(", ");
            const questionText = item.answered_count + " из " + item.question_count + " вопросов";
            const gradeText = item.grade ? "Оценка " + item.grade : "Без оценки";
            const content = "<div>" +
                    "<div class=\"fw-semibold\">" + escapeHtml(formatDate(item.finished_at || item.created_on)) + "</div>" +
                    "<div class=\"text-muted small\">" + escapeHtml(item.status_label) + "</div>" +
                "</div>" +
                "<div>" + escapeHtml(topics || "Темы не выбраны") + "</div>" +
                "<div class=\"text-muted\">" + escapeHtml(questionText) + "</div>" +
                "<div class=\"text-end\">" + escapeHtml(gradeText) + "</div>";

            if (item.status === "completed") {
                return "<a class=\"ai-interview__history-row\" href=\"" +
                    escapeHtml(config.resultPageBaseUrl + encodeURIComponent(item.guid)) +
                    "\">" + content + "</a>";
            }
            if (item.status === "active" || item.status === "failed-recoverable") {
                return "<a class=\"ai-interview__history-row\" href=\"" +
                    escapeHtml(config.interviewPageUrl) +
                    "\">" + content + "</a>";
            }
            return "<div class=\"ai-interview__history-row ai-interview__history-row--muted\">" +
                content +
                "</div>";
        }).join("");
    }

    function renderState(state) {
        setError("");
        setNotice(state.notice ? state.notice.message : "");
        renderHistory(state.history || []);
        setVisible(closedPanel, !state.enabled);
        setVisible(startPanel, state.enabled && state.status === "ready");
        setVisible(sessionPanel, state.enabled &&
            (state.status === "active" || state.status === "failed-recoverable"));
        setVisible(resultPanel, false);
        setVisible(historyPanel, state.enabled && state.status === "ready");
        statusBox.textContent = state.enabled ? "" : (state.message || "");

        if (!state.enabled || state.status === "ready") {
            currentTurn = null;
            return;
        }
        if (state.status === "completed") {
            renderResult(state.result || {});
            statusBox.textContent = "Попытка завершена";
            return;
        }

        currentTurn = state.current_turn;
        const meta = document.getElementById("ai-interview-meta");
        const topicLabels = (state.selected_topics || []).map(function (topic) {
            return "<span class=\"ai-interview__badge\">" + escapeHtml(topic.label) + "</span>";
        });
        meta.innerHTML = "<span class=\"ai-interview__badge\">Вопрос " +
            currentTurn.position + " из " + state.question_count + "</span>" +
            topicLabels.join("");
        document.getElementById("ai-interview-current-meta").textContent =
            currentTurn.topic.label;
        document.getElementById("ai-interview-question").textContent =
            currentTurn.question;
        answerInput.disabled = false;
        answerButton.disabled = false;
        answerInput.value = "";
        charCount.textContent = "0/1000";
    }

    async function responseJson(response) {
        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            throw new Error("Сервер вернул не JSON. Обновите страницу и войдите снова.");
        }
        return response.json();
    }

    async function postJson(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        const payload = await responseJson(response);
        if (!response.ok) {
            throw new Error(payload.error || "Ошибка AI-собеседования");
        }
        return payload;
    }

    async function loadState() {
        try {
            const response = await fetch(config.stateUrl);
            const payload = await responseJson(response);
            if (!response.ok) {
                throw new Error(payload.error || "Не удалось загрузить состояние");
            }
            renderState(payload);
        } catch (error) {
            setError(error.message);
        }
    }

    async function loadResult(sessionGuid) {
        try {
            const response = await fetch(config.resultUrl + "?guid=" + encodeURIComponent(sessionGuid));
            const payload = await responseJson(response);
            if (!response.ok) {
                throw new Error(payload.error || "Не удалось загрузить результат");
            }
            setError("");
            statusBox.textContent = "Результат попытки";
            setVisible(startPanel, false);
            setVisible(sessionPanel, false);
            renderResult(payload);
            await loadState();
            setVisible(closedPanel, false);
            setVisible(startPanel, false);
            setVisible(sessionPanel, false);
            setVisible(resultPanel, true);
            setVisible(historyPanel, false);
            statusBox.textContent = "Результат попытки";
        } catch (error) {
            setError(error.message);
        }
    }

    startForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (waiting) {
            return;
        }
        const topics = Array.from(startForm.querySelectorAll("input[name=topic]:checked"))
            .map(function (input) { return input.value; });
        const accessCode = accessCodeInput ? accessCodeInput.value.trim() : "";
        setWaiting(true);
        try {
            renderState(await postJson(config.startUrl, {
                topics: topics,
                access_code: accessCode
            }));
        } catch (error) {
            setError(error.message);
        } finally {
            setWaiting(false);
        }
    });

    answerForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        if (waiting || !currentTurn || !answerInput.value.trim()) {
            return;
        }
        setWaiting(true);
        try {
            renderState(await postJson(config.answerUrl, {
                turn_id: currentTurn.id,
                answer: answerInput.value
            }));
        } catch (error) {
            setError(error.message);
        } finally {
            setWaiting(false);
        }
    });

    answerInput.addEventListener("input", function () {
        charCount.textContent = answerInput.value.length + "/1000";
    });

    answerInput.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" || event.shiftKey) {
            return;
        }
        event.preventDefault();
        if (!waiting && currentTurn && answerInput.value.trim()) {
            answerForm.requestSubmit();
        }
    });

    if (config.resultGuid) {
        loadResult(config.resultGuid);
    } else {
        loadState();
    }
}());
