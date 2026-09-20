/**
 * THINKAGAIN — Agent Flow State Machine Graph Visualizer (Redesigned)
 *
 * ─ Structured layered layout (5 Y-lanes)
 * ─ Orthogonal / stepped edge routing (no free Bézier curves)
 * ─ Outer-lane routing for all backward / loop transitions
 * ─ Professional card nodes with icon + title + status badge
 * ─ Three edge classes: active (purple), inactive (gray), loop (dashed)
 *
 * All backend API calls, state polling, STATE_META keys, and TRANSITIONS
 * are preserved exactly. Only visual rendering is changed.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ── DOM References ──────────────────────────────────────────────────────
    const nodesLayer   = document.getElementById('nodes-layer');
    const edgesLayer   = document.getElementById('edges-layer');
    const labelsLayer  = document.getElementById('labels-layer');
    const infoCurrentState = document.getElementById('info-current-state');
    const infoStateDesc    = document.getElementById('info-state-desc');
    const infoCurrentAgent = document.getElementById('info-current-agent');
    const infoAgentPhase   = document.getElementById('info-agent-phase');
    const infoSessionId    = document.getElementById('info-session-id');

    // ── Layout Constants ────────────────────────────────────────────────────
    const NW = 172;   // Node width
    const NH = 72;    // Node height
    const RX = 14;    // Border radius

    // Y-lanes for the 5 horizontal rows
    const LANE = {
        TOP_OUTER : 20,   // Outer routing lane for backward edges (top)
        ROW_A     : 90,   // Top branch row (Socratic, Waiting, Update, Plan)
        ROW_B     : 290,  // Center main flow (Start, Diagnosing, Evaluating, Complete)
        ROW_C     : 490,  // Lower branch (Targeted Tutoring, Generate Transfer, Escalated)
        BOT_OUTER : 660,  // Outer routing lane for backward edges (bottom)
        HUMAN     : 565,  // Human Review (slightly above bottom outer)
    };

    // ── State Metadata ──────────────────────────────────────────────────────
    // Keys preserved exactly from state_machine.py.
    // x,y define the TOP-LEFT corner of each node card.
    const STATE_META = {
        START: {
            title: 'START',
            icon: '▶',
            desc: "Session initialized with student's initial code, query, or problem.",
            agent: 'System Runtime',
            x: 40, y: LANE.ROW_B,
        },
        DIAGNOSING: {
            title: 'DIAGNOSING',
            icon: '🔍',
            desc: 'Question Classifier & Diagnostic Agent detect conceptual misconceptions.',
            agent: 'Diagnostic Agent',
            x: 260, y: LANE.ROW_B,
        },
        SOCRATIC_GUIDANCE: {
            title: 'SOCRATIC GUIDANCE',
            icon: '💡',
            desc: 'Selects an unused angle and poses a targeted reasoning question.',
            agent: 'Socratic Agent',
            x: 480, y: LANE.ROW_A,
        },
        TARGETED_TUTORING: {
            title: 'TARGETED TUTORING',
            icon: '🎯',
            desc: 'Provides explicit explanation, worked example, and key invariant insight.',
            agent: 'Targeted Tutor Agent',
            x: 480, y: LANE.ROW_C,
        },
        WAITING_FOR_STUDENT: {
            title: 'WAITING FOR STUDENT',
            icon: '⏳',
            desc: 'Machine halts awaiting external student code or explanation response.',
            agent: 'Student Turn',
            x: 700, y: LANE.ROW_A,
        },
        GENERATE_TRANSFER_TASK: {
            title: 'GENERATE TRANSFER',
            icon: '📄',
            desc: 'Synthesizes a fresh transfer task to verify reasoning generalization.',
            agent: 'Transfer Task Agent',
            x: 700, y: LANE.ROW_C,
        },
        EVALUATING: {
            title: 'EVALUATING',
            icon: '📊',
            desc: 'Evaluator Agent assesses reasoning correctness and misconception recurrence.',
            agent: 'Evaluator Agent',
            x: 930, y: LANE.ROW_B,
        },
        UPDATE_STATE: {
            title: 'UPDATE STATE',
            icon: '⚙️',
            desc: 'Updates mastery status, resolves misconceptions, and logs audit record.',
            agent: 'Runtime Persistence',
            x: 1160, y: LANE.ROW_A,
        },
        ESCALATED: {
            title: 'ESCALATED',
            icon: '⚠️',
            desc: 'Budget limits reached without transfer pass; escalates to instructor.',
            agent: 'Escalation Policy',
            x: 1160, y: LANE.ROW_C,
        },
        PLAN_NEXT: {
            title: 'PLAN NEXT',
            icon: '📋',
            desc: 'Planner Agent synthesizes pedagogical next action based on learning state.',
            agent: 'Planner Agent',
            x: 1380, y: LANE.ROW_A,
        },
        HUMAN_REVIEW_WAITING: {
            title: 'HUMAN REVIEW',
            icon: '👤',
            desc: 'Terminal state waiting for instructor intervention and feedback.',
            agent: 'Human Instructor',
            x: 1380, y: LANE.HUMAN,
        },
        COMPLETE: {
            title: 'COMPLETE',
            icon: '✅',
            desc: 'Terminal state: Learning session completed successfully.',
            agent: 'Tutoring Engine',
            x: 1480, y: LANE.ROW_B,
        },
    };

    // ── Transitions (preserved from slice/state_machine.py) ─────────────────
    // isLoop: true  → backward edge → routed via outer lane
    // port hints tell the router which connection side to prefer
    const TRANSITIONS = [
        { from: 'START',                to: 'DIAGNOSING' },
        { from: 'DIAGNOSING',           to: 'SOCRATIC_GUIDANCE' },
        { from: 'DIAGNOSING',           to: 'TARGETED_TUTORING' },
        { from: 'DIAGNOSING',           to: 'COMPLETE',             isLoop: true, lane: 'bottom' },
        { from: 'SOCRATIC_GUIDANCE',    to: 'WAITING_FOR_STUDENT' },
        { from: 'WAITING_FOR_STUDENT',  to: 'EVALUATING' },
        { from: 'EVALUATING',           to: 'SOCRATIC_GUIDANCE',    isLoop: true, lane: 'top'    },
        { from: 'EVALUATING',           to: 'GENERATE_TRANSFER_TASK' },
        { from: 'EVALUATING',           to: 'TARGETED_TUTORING',    isLoop: true, lane: 'top'    },
        { from: 'EVALUATING',           to: 'UPDATE_STATE' },
        { from: 'EVALUATING',           to: 'ESCALATED' },
        { from: 'GENERATE_TRANSFER_TASK', to: 'WAITING_FOR_STUDENT', isLoop: true, lane: 'bottom' },
        { from: 'TARGETED_TUTORING',    to: 'GENERATE_TRANSFER_TASK' },
        { from: 'TARGETED_TUTORING',    to: 'ESCALATED' },
        { from: 'UPDATE_STATE',         to: 'PLAN_NEXT' },
        { from: 'PLAN_NEXT',            to: 'COMPLETE' },
        { from: 'PLAN_NEXT',            to: 'SOCRATIC_GUIDANCE',    isLoop: true, lane: 'top'    },
        { from: 'ESCALATED',            to: 'HUMAN_REVIEW_WAITING' },
    ];

    // ── Runtime State ───────────────────────────────────────────────────────
    let currentState    = 'START';
    let completedStates = new Set(['START']);
    let isTerminal      = false;

    // ── Port Helpers ────────────────────────────────────────────────────────
    function port(meta, side) {
        const cx = meta.x + NW / 2;
        const cy = meta.y + NH / 2;
        switch (side) {
            case 'left':   return { x: meta.x,       y: cy };
            case 'right':  return { x: meta.x + NW,  y: cy };
            case 'top':    return { x: cx,            y: meta.y };
            case 'bottom': return { x: cx,            y: meta.y + NH };
        }
    }

    // ── Orthogonal / Outer-Lane Edge Router ─────────────────────────────────
    /**
     * Returns an SVG path `d` string using only horizontal and vertical segments.
     *
     * Forward edges:
     *   - Same Y-lane  → straight horizontal: RIGHT → LEFT
     *   - Different Y  → 3-segment elbow: RIGHT → midX → target Y → LEFT
     *
     * Backward / loop edges (isLoop or source.x >= target.x):
     *   - lane='top'    → route above graph through LANE.TOP_OUTER
     *   - lane='bottom' → route below graph through LANE.BOT_OUTER
     *   - path: source TOP/BOTTOM → outer lane → target TOP/BOTTOM
     */
    function routeEdge(t) {
        const from = STATE_META[t.from];
        const to   = STATE_META[t.to];
        if (!from || !to) return '';

        const isBackward = t.isLoop || (from.x >= to.x && t.from !== t.to);

        if (isBackward) {
            return routeLoopEdge(from, to, t.lane || 'top');
        }

        // Determine whether source and target are on same Y-lane
        const fromR  = port(from, 'right');
        const toL    = port(to, 'left');
        const yDelta = Math.abs(fromR.y - toL.y);

        if (yDelta < 8) {
            // Straight horizontal connector
            return `M ${fromR.x} ${fromR.y} L ${toL.x} ${toL.y}`;
        }

        // 3-segment elbow: right → midX (vertical step) → left
        // Choose midX between the two nodes
        const midX = fromR.x + (toL.x - fromR.x) * 0.55;
        return [
            `M ${fromR.x} ${fromR.y}`,
            `L ${midX} ${fromR.y}`,
            `L ${midX} ${toL.y}`,
            `L ${toL.x} ${toL.y}`,
        ].join(' ');
    }

    function routeLoopEdge(from, to, lane) {
        if (lane === 'bottom') {
            const outerY = LANE.BOT_OUTER;
            const fromB  = port(from, 'bottom');
            const toB    = port(to, 'bottom');
            return [
                `M ${fromB.x} ${fromB.y}`,
                `L ${fromB.x} ${outerY}`,
                `L ${toB.x}   ${outerY}`,
                `L ${toB.x}   ${toB.y}`,
            ].join(' ');
        }
        // default: top lane
        const outerY = LANE.TOP_OUTER;
        const fromT  = port(from, 'top');
        const toT    = port(to, 'top');
        return [
            `M ${fromT.x} ${fromT.y}`,
            `L ${fromT.x} ${outerY}`,
            `L ${toT.x}   ${outerY}`,
            `L ${toT.x}   ${toT.y}`,
        ].join(' ');
    }

    // ── Render Edges ────────────────────────────────────────────────────────
    function renderEdges() {
        edgesLayer.innerHTML  = '';
        labelsLayer.innerHTML = '';

        TRANSITIONS.forEach(t => {
            const from = STATE_META[t.from];
            const to   = STATE_META[t.to];
            if (!from || !to) return;

            const pathD = routeEdge(t);
            if (!pathD) return;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', pathD);

            const isFromCurrent = (t.from === currentState);
            const isTraversed   = completedStates.has(t.from) &&
                                  (completedStates.has(t.to) || t.to === currentState);
            const isLoop        = !!t.isLoop;

            if (isTraversed || isFromCurrent) {
                // Active / traversed path
                path.setAttribute('class', 'graph-edge edge-active');
                path.setAttribute('marker-end', 'url(#arrow-active)');
            } else if (isLoop) {
                // Loop / return edge
                path.setAttribute('class', 'graph-edge edge-loop');
                path.setAttribute('marker-end', 'url(#arrow-loop)');
            } else {
                // Possible but not yet traversed
                path.setAttribute('class', 'graph-edge edge-inactive');
                path.setAttribute('marker-end', 'url(#arrow)');
            }

            edgesLayer.appendChild(path);
        });
    }

    // ── SVG Text Helper (auto line-break at max chars) ──────────────────────
    function svgText(x, y, text, cls, maxWidth) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        el.setAttribute('x', x);
        el.setAttribute('y', y);
        el.setAttribute('class', cls);
        el.textContent = text;
        return el;
    }

    // ── Render Nodes ────────────────────────────────────────────────────────
    function renderNodes() {
        nodesLayer.innerHTML = '';

        Object.entries(STATE_META).forEach(([key, meta]) => {
            const isCurrent   = (key === currentState);
            const isCompleted = completedStates.has(key) && !isCurrent;

            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('class', `graph-node ${isCurrent ? 'node-current' : isCompleted ? 'node-completed' : 'node-waiting'}`);
            g.setAttribute('transform', `translate(${meta.x}, ${meta.y})`);
            g.setAttribute('data-key', key);

            // ── Card background rect ──────────────────────────────────────
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('width',  NW);
            rect.setAttribute('height', NH);
            rect.setAttribute('rx', RX);
            rect.setAttribute('class', 'node-rect');

            // Apply appropriate filter
            if (isCurrent) {
                rect.setAttribute('filter', 'url(#purple-glow)');
            } else if (isCompleted) {
                rect.setAttribute('filter', 'url(#card-shadow)');
            } else {
                rect.setAttribute('filter', 'url(#card-shadow)');
            }
            g.appendChild(rect);

            // ── Icon circle (left accent) ─────────────────────────────────
            const iconBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            iconBg.setAttribute('x', 10);
            iconBg.setAttribute('y', 12);
            iconBg.setAttribute('width', 32);
            iconBg.setAttribute('height', 32);
            iconBg.setAttribute('rx', 8);
            iconBg.setAttribute('class', 'node-icon-bg');
            g.appendChild(iconBg);

            const iconText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            iconText.setAttribute('x', 26);
            iconText.setAttribute('y', 33);
            iconText.setAttribute('text-anchor', 'middle');
            iconText.setAttribute('dominant-baseline', 'middle');
            iconText.setAttribute('class', 'node-icon');
            iconText.textContent = meta.icon;
            g.appendChild(iconText);

            // ── State title ───────────────────────────────────────────────
            // Shorten long titles for display
            const displayTitle = meta.title.length > 20
                ? meta.title.substring(0, 18) + '…'
                : meta.title;

            const title = svgText(50, 26, displayTitle, 'node-title');
            g.appendChild(title);

            // ── Status badge ──────────────────────────────────────────────
            const badgeText = isCurrent   ? '● CURRENT'
                            : isCompleted ? '✓ COMPLETED'
                            : '○ WAITING';
            const badge = svgText(50, 50, badgeText, 'node-badge');
            g.appendChild(badge);

            // ── Hover & click ─────────────────────────────────────────────
            g.addEventListener('mouseenter', () => {
                rect.style.transform = 'translateY(-2px)';
            });
            g.addEventListener('mouseleave', () => {
                rect.style.transform = '';
            });
            g.addEventListener('click', () => {
                selectNodeForInspection(key);
            });
            g.style.cursor = 'pointer';

            nodesLayer.appendChild(g);
        });
    }

    // ── Info Panel ──────────────────────────────────────────────────────────
    function selectNodeForInspection(key) {
        const meta = STATE_META[key];
        if (!meta) return;
        infoCurrentState.textContent  = meta.title;
        infoStateDesc.textContent     = meta.desc;
        infoCurrentAgent.textContent  = `🤖 ${meta.agent}`;
    }

    // ── Fetch Machine State from API ─────────────────────────────────────────
    async function updateGraphState() {
        try {
            const res  = await fetch('/api/state');
            const data = await res.json();

            if (data.active && data.session_id) {
                currentState    = data.state || 'START';
                completedStates = new Set(data.completed_states || ['START']);
                isTerminal      = data.is_terminal || false;

                infoSessionId.textContent = data.session_id;
                selectNodeForInspection(currentState);
                infoAgentPhase.textContent = `Phase: ${data.current_phase || 'Active'}`;
            } else {
                currentState    = 'START';
                completedStates = new Set(['START']);
                infoSessionId.textContent = 'No active session';
                selectNodeForInspection('START');
            }

            renderEdges();
            renderNodes();

        } catch (err) {
            console.error('Failed to sync graph state:', err);
        }
    }

    // ── Init & Poll ──────────────────────────────────────────────────────────
    updateGraphState();

    setInterval(() => {
        if (!document.hidden) {
            updateGraphState();
        }
    }, 3000);
});
