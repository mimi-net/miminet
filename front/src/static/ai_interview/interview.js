(function () {
    const script = document.currentScript;
    const config = window.aiInterviewConfig || {
        stateUrl: script.dataset.stateUrl,
        interviewPageUrl: script.dataset.interviewPageUrl,
        startUrl: script.dataset.startUrl,
        answerUrl: script.dataset.answerUrl,
        abortUrl: script.dataset.abortUrl,
        resultUrl: script.dataset.resultUrl,
        resultPageBaseUrl: script.dataset.resultPageBaseUrl,
        resultGuid: script.dataset.resultGuid || null
    };
    const errorBox = document.getElementById("ai-interview-error");
    const noticeBox = document.getElementById("ai-interview-notice");
    const statusBox = document.getElementById("ai-interview-status");
    const startPanel = document.getElementById("ai-interview-start");
    const sessionPanel = document.getElementById("ai-interview-session");
    const resultPanel = document.getElementById("ai-interview-result");
    const historyPanel = document.getElementById("ai-interview-history-panel");
    const startForm = document.getElementById("ai-interview-start-form");
    const startButton = document.getElementById("ai-interview-start-button");
    const accessCodeInput = document.getElementById("ai-interview-access-code");
    const allowFollowupsInput = document.getElementById("ai-interview-allow-followups");
    const answerForm = document.getElementById("ai-interview-answer-form");
    const answerButton = document.getElementById("ai-interview-answer-button");
    const answerInput = document.getElementById("ai-interview-answer");
    const abortButton = document.getElementById("ai-interview-abort-button");
    const charCount = document.getElementById("ai-interview-char-count");
    const historyMoreButton = document.getElementById("ai-interview-history-more");
    const historyCollapseButton = document.getElementById("ai-interview-history-collapse");
    const historyPageSize = 5;
    let currentTurn = null;
    let currentSessionGuid = null;
    let historyItems = [];
    let visibleHistoryCount = historyPageSize;
    let waiting = false;

    function shouldOpenActiveSession() {
        const params = new URLSearchParams(window.location.search);
        return params.get("continue") === "1";
    }

    function activeSessionUrl() {
        return config.interviewPageUrl + "?continue=1";
    }

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
        if (allowFollowupsInput) {
            allowFollowupsInput.disabled = value;
        }
        if (answerButton) {
            answerButton.disabled = value;
        }
        if (answerInput) {
            answerInput.disabled = value;
        }
        if (abortButton) {
            abortButton.disabled = value;
        }
    }

    function renderResult(result) {
        setNotice("");
        setVisible(startPanel, false);
        setVisible(sessionPanel, false);
        setVisible(resultPanel, true);
        setVisible(historyPanel, false);
        document.getElementById("ai-interview-grade").textContent = result.grade;
        document.getElementById("ai-interview-score").textContent =
            "(" + result.score_total + " из " + result.score_max + " баллов)";
        document.getElementById("ai-interview-verdict").textContent = result.verdict || "";
        listInto("ai-interview-strengths", result.strengths);
        listInto("ai-interview-gaps", result.gaps);
        listInto("ai-interview-recommendations", result.recommendations);
        document.getElementById("ai-interview-result-questions").innerHTML =
            (result.questions || []).map(function (turn) {
                return "<article class=\"border rounded p-3\">" +
                    (turn.topic_position
                        ? "<div class=\"text-muted\">Тема " + turn.topic_position +
                            ", вопрос " + turn.question_position + "</div>"
                        : "") +
                    "<h4 class=\"h6 mt-2\">" + escapeHtml(turn.question) +
                    " <span class=\"text-muted\">(" + turn.answer_score + " из " +
                    turn.answer_max_score + " баллов)</span></h4>" +
                    "<p class=\"mb-1\"><strong>Ответ:</strong> " + escapeHtml(turn.answer) + "</p>" +
                    "<p class=\"mb-0 text-muted\">" + escapeHtml(turn.feedback) + "</p>" +
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
        historyItems = history || [];
        if (!historyItems.length) {
            container.innerHTML = "<div class=\"text-muted\">Попыток пока нет</div>";
            setVisible(historyMoreButton, false);
            setVisible(historyCollapseButton, false);
            return;
        }
        container.innerHTML = historyItems.slice(0, visibleHistoryCount).map(function (item) {
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
                    escapeHtml(activeSessionUrl()) +
                    "\">" + content + "</a>";
            }
            return "<div class=\"ai-interview__history-row ai-interview__history-row--muted\">" +
                content +
                "</div>";
        }).join("");
        setVisible(historyMoreButton, visibleHistoryCount < historyItems.length);
        setVisible(historyCollapseButton, visibleHistoryCount > historyPageSize);
    }

    function renderState(state, options) {
        options = options || {};
        setError("");
        const isActiveSession = state.status === "active" || state.status === "failed-recoverable";
        const showActiveSession = isActiveSession &&
            (options.openActiveSession || shouldOpenActiveSession());
        const showLaunch = state.status === "ready" || (isActiveSession && !showActiveSession);
        const noticeMessage = state.notice
            ? state.notice.message
            : (showLaunch && isActiveSession
                ? "У вас есть незавершенная попытка. Ее можно открыть из истории попыток."
                : "");
        setNotice(noticeMessage);
        renderHistory(state.history || []);
        setVisible(startPanel, showLaunch);
        setVisible(sessionPanel, showActiveSession);
        setVisible(resultPanel, false);
        setVisible(historyPanel, state.status === "ready" || (isActiveSession && !showActiveSession));
        statusBox.textContent = "";

        if (state.status === "ready" || (isActiveSession && !showActiveSession)) {
            currentTurn = null;
            currentSessionGuid = null;
            return;
        }
        if (state.status === "completed") {
            currentSessionGuid = null;
            renderResult(state.result || {});
            statusBox.textContent = "Попытка завершена";
            return;
        }

        currentTurn = state.current_turn;
        currentSessionGuid = state.session_guid;
        const meta = document.getElementById("ai-interview-meta");
        const topicLabels = (state.selected_topics || []).map(function (topic) {
            return "<span class=\"ai-interview__badge\">" + escapeHtml(topic.label) + "</span>";
        });
        meta.innerHTML = "<span class=\"ai-interview__badge\">Тема " +
            currentTurn.topic_position + " из " + state.topic_count + "</span>" +
            "<span class=\"ai-interview__badge\">Вопрос " +
            currentTurn.question_position + " из 4</span>" +
            topicLabels.join("");
        document.getElementById("ai-interview-current-meta").textContent =
            currentTurn.topic.label;
        document.getElementById("ai-interview-question").textContent =
            currentTurn.question;
        answerInput.disabled = false;
        answerButton.disabled = false;
        answerInput.value = "";
        charCount.textContent = "0/1000";
        answerInput.focus();
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
            throw new Error(payload.error || "Ошибка AI-тестирования");
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
                access_code: accessCode,
                question_mode: allowFollowupsInput.checked ? "adaptive" : "bank_only"
            }), {openActiveSession: true});
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
            }), {openActiveSession: true});
        } catch (error) {
            setError(error.message);
        } finally {
            setWaiting(false);
        }
    });

    abortButton.addEventListener("click", async function () {
        if (waiting || !currentSessionGuid) {
            return;
        }
        if (!window.confirm("Завершить попытку досрочно? Она будет учтена в лимите кода и не сохранится в истории.")) {
            return;
        }
        setWaiting(true);
        try {
            renderState(await postJson(config.abortUrl, {
                session_guid: currentSessionGuid
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

    historyMoreButton.addEventListener("click", function () {
        visibleHistoryCount += historyPageSize;
        renderHistory(historyItems);
    });

    historyCollapseButton.addEventListener("click", function () {
        visibleHistoryCount = historyPageSize;
        renderHistory(historyItems);
    });

    if (config.resultGuid) {
        loadResult(config.resultGuid);
    } else {
        loadState();
    }
}());
