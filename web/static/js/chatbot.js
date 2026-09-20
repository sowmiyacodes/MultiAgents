/**
 * THINKAGAIN — Chatbot Frontend Logic
 * Connects the browser chat interface with the Flask API and existing multi-agent engine.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const welcomeCard = document.getElementById('welcome-card');
    const activeChatWrapper = document.getElementById('active-chat-wrapper');
    const initialQueryForm = document.getElementById('initial-query-form');
    const initialQueryInput = document.getElementById('initial-query-input');
    const chatForm = document.getElementById('chat-form');
    const studentAnswerInput = document.getElementById('student-answer-input');
    const messagesContainer = document.getElementById('messages-container');
    const studentOptionsCard = document.getElementById('student-options-card');
    const terminalOutcomeCard = document.getElementById('terminal-outcome-card');
    const btnDownloadJson = document.getElementById('btn-download-json');
    const btnNewSession = document.getElementById('btn-new-session');
    const navSessionIndicator = document.getElementById('nav-session-indicator');
    const navSessionText = document.getElementById('nav-session-text');

    // Right-Side Live Agent Panel Elements
    const agentNameEl = document.getElementById('agent-name');
    const agentActivityEl = document.getElementById('agent-activity');
    const panelPhaseEl = document.getElementById('panel-phase');
    const panelConceptEl = document.getElementById('panel-concept');
    const panelSubconceptEl = document.getElementById('panel-subconcept');
    const panelStatusEl = document.getElementById('panel-status');
    const diagnosisPanelCard = document.getElementById('diagnosis-panel-card');
    const panelInvariantEl = document.getElementById('panel-invariant');
    const chatPhaseBadge = document.getElementById('chat-phase-badge');

    // Preset Sample Queries
    const samples = {
        binary_search: `int left = 0;\nint right = nums.length - 1;\nwhile (left <= right) {\n    int mid = (left + right) / 2;\n    if (nums[mid] == target) return mid;\n    if (nums[mid] < target) left++; else right--;\n}\nreturn -1;`,
        two_pointers: `def two_sum_sorted(nums, target):\n    left = 0\n    right = len(nums) - 1\n    while left < right:\n        cur = nums[left] + nums[right]\n        if cur == target:\n            return [left, right]\n        elif cur > target:\n            left += 1  # Arbitrary pointer movement\n        else:\n            right -= 1\n    return []`,
        general_question: `What is the core invariant of Binary Search and why does left++ cause infinite loops or wrong bounds?`
    };

    let currentSessionId = null;

    // ── Preset Chip Click Handlers ───────────────────────────────────────────
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const key = chip.getAttribute('data-sample');
            if (samples[key]) {
                initialQueryInput.value = samples[key];
                initialQueryInput.focus();
            }
        });
    });

    // ── Multiline Input Keyboard Behavior ────────────────────────────────────
    // Normal Enter creates a new line; Ctrl + Enter submits the form.
    studentAnswerInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    });

    initialQueryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            initialQueryForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    });

    // ── Initial State Fetch ──────────────────────────────────────────────────
    async function fetchState() {
        try {
            const res = await fetch('/api/state');
            const data = await res.json();
            if (data.active && data.session_id) {
                currentSessionId = data.session_id;
                renderActiveSession(data);
            } else {
                showWelcome();
            }
        } catch (err) {
            console.error('Error fetching state:', err);
            showWelcome();
        }
    }

    function showWelcome() {
        welcomeCard.classList.remove('hidden');
        activeChatWrapper.classList.add('hidden');
        navSessionIndicator.classList.add('hidden');
        currentSessionId = null;
    }

    // ── Render Active Session ────────────────────────────────────────────────
    function renderActiveSession(state) {
        welcomeCard.classList.add('hidden');
        activeChatWrapper.classList.remove('hidden');
        navSessionIndicator.classList.remove('hidden');
        navSessionText.textContent = state.session_id;

        updateLiveAgentPanel(state);

        // Render conversation messages
        messagesContainer.innerHTML = '';
        if (state.messages && state.messages.length > 0) {
            state.messages.forEach(msg => appendMessageCard(msg));
        }

        // Student Support Options card
        if (state.options_available) {
            studentOptionsCard.classList.remove('hidden');
        } else {
            studentOptionsCard.classList.add('hidden');
        }

        // Terminal Outcome card
        if (state.is_terminal || state.state === 'COMPLETE' || state.state === 'HUMAN_REVIEW_WAITING' || state.state === 'ESCALATED') {
            renderTerminalBanner(state);
        } else {
            terminalOutcomeCard.classList.add('hidden');
            document.getElementById('chat-input-area').classList.remove('hidden');
        }

        scrollToBottom();
    }

    // ── Live Agent Panel Updates ─────────────────────────────────────────────
    function updateLiveAgentPanel(state) {
        agentNameEl.textContent = state.current_agent || 'Socratic Agent';
        agentActivityEl.textContent = (state.agent_status || 'ACTIVE').toUpperCase();
        panelPhaseEl.textContent = state.current_phase || 'Socratic Guidance';
        panelConceptEl.textContent = state.topic || 'DSA Concept';
        panelSubconceptEl.textContent = state.subconcept || '';
        panelStatusEl.textContent = state.agent_status || 'Waiting for your answer';

        if (chatPhaseBadge) {
            chatPhaseBadge.textContent = state.current_phase || 'Socratic Guidance';
        }

        if (state.diagnosis && state.diagnosis.invariant) {
            diagnosisPanelCard.classList.remove('hidden');
            panelInvariantEl.textContent = state.diagnosis.invariant;
        } else {
            diagnosisPanelCard.classList.add('hidden');
        }
    }

    // ── Render Message Cards ─────────────────────────────────────────────────
    function appendMessageCard(msg) {
        const wrapper = document.createElement('div');
        wrapper.className = 'msg-wrapper';

        if (msg.role === 'user') {
            wrapper.classList.add('msg-user');
            wrapper.innerHTML = `
                <div class="msg-header msg-header-user">
                    <span>👤 YOU</span>
                </div>
                <div class="msg-text">${escapeHtml(msg.text)}</div>
            `;
        } else if (msg.type === 'evaluation') {
            wrapper.classList.add('eval-card');
            const isPass = msg.reasoning_correct || msg.result === 'PASS';
            wrapper.classList.add(isPass ? 'pass' : 'fail');
            
            const resultLabel = isPass ? 'Successful Reasoning' : 'Needs Another Attempt';
            const reasoningLabel = msg.reasoning_correct ? 'Correct' : 'Not yet';
            const transferLabel = msg.transfer_success ? 'Success' : '—';

            wrapper.innerHTML = `
                <div class="eval-header">
                    <span class="eval-title">EVALUATION</span>
                    <span class="badge ${isPass ? 'badge-green' : 'badge-purple'}">${escapeHtml(resultLabel)}</span>
                </div>
                <div class="eval-grid">
                    <div>
                        <div class="eval-item-label">Result</div>
                        <div class="eval-item-val">${escapeHtml(msg.result)}</div>
                    </div>
                    <div>
                        <div class="eval-item-label">Reasoning</div>
                        <div class="eval-item-val">${escapeHtml(reasoningLabel)}</div>
                    </div>
                    <div>
                        <div class="eval-item-label">Transfer</div>
                        <div class="eval-item-val">${escapeHtml(transferLabel)}</div>
                    </div>
                </div>
                <div class="eval-feedback">
                    <div class="eval-feedback-title">Feedback</div>
                    <div class="eval-feedback-text">${escapeHtml(msg.feedback || '')}</div>
                </div>
            `;
        } else if (msg.type === 'transfer_task') {
            wrapper.classList.add('transfer-card');
            wrapper.innerHTML = `
                <span class="transfer-badge">Fresh Transfer Task</span>
                <h3 class="transfer-headline">Let's test whether you can apply the same reasoning to a new problem</h3>
                <p class="transfer-sub">Apply the diagnosed invariant in this fresh scenario:</p>
                <div class="transfer-problem-box">${escapeHtml(msg.text)}</div>
            `;
        } else if (msg.type === 'targeted_tutor') {
            wrapper.classList.add('tutor-card');
            wrapper.innerHTML = `
                <div class="tutor-header">
                    <span class="agent-avatar">📘</span>
                    <span class="tutor-title">Targeted Tutor Explanation</span>
                </div>
                ${msg.misconception_stated ? `
                    <div class="tutor-section">
                        <div class="tutor-sec-title">Diagnosed Misconception</div>
                        <div class="tutor-sec-content">${escapeHtml(msg.misconception_stated)}</div>
                    </div>
                ` : ''}
                <div class="tutor-section">
                    <div class="tutor-sec-title">Explanation</div>
                    <div class="tutor-sec-content">${escapeHtml(msg.explanation || '')}</div>
                </div>
                ${msg.worked_example ? `
                    <div class="tutor-section">
                        <div class="tutor-sec-title">Worked Example</div>
                        <div class="tutor-example-box">${escapeHtml(msg.worked_example)}</div>
                    </div>
                ` : ''}
                ${msg.key_insight ? `
                    <div class="tutor-section">
                        <div class="tutor-sec-title">Key Invariant Insight</div>
                        <div class="tutor-insight-box">${escapeHtml(msg.key_insight)}</div>
                    </div>
                ` : ''}
            `;
        } else if (msg.type === 'hint') {
            wrapper.classList.add('hint-card');
            wrapper.innerHTML = `
                <div class="hint-header">💡 Progressive Hint</div>
                <div class="hint-text">${escapeHtml(msg.text)}</div>
            `;
        } else {
            // Standard assistant response (Socratic question, general explanation, etc.)
            wrapper.classList.add('msg-assistant');
            wrapper.innerHTML = `
                <div class="msg-header msg-header-assistant">
                    <span>⚡ THINKAGAIN</span>
                    ${msg.angle ? `<span class="badge badge-purple">${escapeHtml(msg.angle)}</span>` : ''}
                </div>
                <div class="msg-text">${escapeHtml(msg.text)}</div>
            `;
        }

        messagesContainer.appendChild(wrapper);
    }

    // ── Render Terminal Outcome Banner ───────────────────────────────────────
    function renderTerminalBanner(state) {
        terminalOutcomeCard.classList.remove('hidden');
        document.getElementById('chat-input-area').classList.add('hidden');

        const titleEl = document.getElementById('terminal-title');
        const descEl = document.getElementById('terminal-desc');
        const iconEl = document.getElementById('terminal-icon');

        if (state.state === 'HUMAN_REVIEW_WAITING' || state.state === 'ESCALATED') {
            terminalOutcomeCard.classList.add('escalated');
            iconEl.textContent = '⚠️';
            titleEl.textContent = 'SESSION ESCALATED';
            descEl.textContent = 'The maximum attempts were reached without successful transfer. Session escalated to HUMAN INSTRUCTOR REVIEW.';
        } else {
            terminalOutcomeCard.classList.remove('escalated');
            iconEl.textContent = '✓';
            titleEl.textContent = 'SESSION COMPLETED SUCCESSFULLY';
            descEl.textContent = 'You successfully demonstrated the required reasoning and completed the learning goals.';
        }
    }

    // ── Start Learning (Initial Query Form) ──────────────────────────────────
    initialQueryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = initialQueryInput.value.trim();
        if (!query) return;

        const btn = document.getElementById('btn-start-learning');
        btn.disabled = true;
        btn.innerHTML = 'Analyzing...';

        try {
            const res = await fetch('/api/session/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initial_query: query,
                    student_id: 'student_001'
                })
            });

            if (!res.ok) {
                const err = await res.json();
                alert(err.error || 'Failed to start session');
                return;
            }

            const data = await res.json();
            currentSessionId = data.session_id;
            renderActiveSession(data);
            studentAnswerInput.focus();
        } catch (err) {
            console.error('Failed to start session:', err);
            alert('Could not start tutoring session. Check server logs.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Start Learning';
        }
    });

    // ── Send Answer Form ─────────────────────────────────────────────────────
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = studentAnswerInput.value.trim();
        if (!message) return;

        const sendBtn = document.getElementById('btn-send-answer');
        sendBtn.disabled = true;
        sendBtn.innerHTML = 'Evaluating...';

        // Optimistically show user message
        appendMessageCard({ role: 'user', text: message });
        studentAnswerInput.value = '';
        scrollToBottom();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!res.ok) {
                const err = await res.json();
                alert(err.error || 'Failed to evaluate answer');
                return;
            }

            const data = await res.json();
            renderActiveSession(data);
        } catch (err) {
            console.error('Failed to send answer:', err);
            alert('Failed to send message to tutoring engine.');
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<span>Send Answer</span> <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
            studentAnswerInput.focus();
        }
    });

    // ── Student Options Handlers ─────────────────────────────────────────────
    document.getElementById('opt-try-again').addEventListener('click', async () => {
        studentOptionsCard.classList.add('hidden');
        try {
            await fetch('/api/option', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ option: 'retry' })
            });
            studentAnswerInput.focus();
        } catch (e) {
            console.error(e);
        }
    });

    document.getElementById('opt-hint').addEventListener('click', async () => {
        studentOptionsCard.classList.add('hidden');
        try {
            const res = await fetch('/api/option', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ option: 'hint' })
            });
            const data = await res.json();
            if (data.message) {
                appendMessageCard(data.message);
                scrollToBottom();
            }
            studentAnswerInput.focus();
        } catch (e) {
            console.error(e);
        }
    });

    document.getElementById('opt-worked-example').addEventListener('click', async () => {
        studentOptionsCard.classList.add('hidden');
        try {
            const res = await fetch('/api/option', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ option: 'worked_example' })
            });
            const data = await res.json();
            if (data.message) {
                appendMessageCard(data.message);
                scrollToBottom();
            }
            studentAnswerInput.focus();
        } catch (e) {
            console.error(e);
        }
    });

    // ── Download Session JSON ────────────────────────────────────────────────
    btnDownloadJson.addEventListener('click', () => {
        if (!currentSessionId) return;
        window.location.href = `/api/session/${encodeURIComponent(currentSessionId)}/download`;
    });

    // ── New Session Button ───────────────────────────────────────────────────
    btnNewSession.addEventListener('click', async () => {
        if (confirm('Start a new session? The current session data is securely stored.')) {
            await fetch('/api/session/new', { method: 'POST' });
            showWelcome();
            initialQueryInput.value = '';
            initialQueryInput.focus();
        }
    });

    // ── Helper Utilities ─────────────────────────────────────────────────────
    function scrollToBottom() {
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 50);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Initialize
    fetchState();
});
