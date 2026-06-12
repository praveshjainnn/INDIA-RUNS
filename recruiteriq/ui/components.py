"""UI Components — renders all Streamlit UI elements for RecruiterIQ."""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
from typing import List, Optional
from ..models.schemas import RankedCandidate, JobDescriptionProfile
from ..config import TIER_LABELS, TIER_COLORS, DISPLAY_DEFAULT


def _score_to_class(tier: str) -> str:
    return {"strong_match": "strong", "good_match": "good",
            "possible": "possible", "stretch": "stretch"}.get(tier, "stretch")


def _bar_html(label: str, value: float, color: str = "#4F6EF7") -> str:
    """Render a single score dimension bar."""
    pct = min(100, max(0, value))
    return f"""
    <div class="score-bar-container">
        <span class="score-bar-label">{label}</span>
        <div class="score-bar-track">
            <div class="score-bar-fill" style="width:{pct}%; background: linear-gradient(90deg, {color}, {color}cc)"></div>
        </div>
        <span class="score-bar-pct">{pct:.0f}%</span>
    </div>"""


def _chip_html(text: str, kind: str = "must") -> str:
    return f'<span class="chip {kind}">{text}</span>'


def render_header():
    """Render the top header banner."""
    st.markdown("""
    <div class="riq-header">
        <div>
            <div class="riq-header-title">🎯 RecruiterIQ</div>
            <div class="riq-header-subtitle">AI-Powered Candidate Ranking · India Runs Data &amp; AI Challenge</div>
        </div>
        <span class="riq-badge">✦ Semantic + Signal Scoring</span>
    </div>
    """, unsafe_allow_html=True)


def render_jd_panel(jd: JobDescriptionProfile):
    """Render the JD summary panel in the sidebar."""
    with st.container():
        st.markdown(f"""
        <div class="jd-panel animate-in">
            <div class="jd-role-title">📋 {jd.role_title}</div>
            <div class="jd-meta">
                <span>🎯 {jd.seniority_level.title()}</span>
                <span>🏢 {', '.join(jd.domain_industry[:2]).title() or 'Technology'}</span>
                <span>🏠 {jd.work_mode.title()}</span>
                {f'<span>📅 {jd.seniority_years_min}–{jd.seniority_years_max} yrs</span>' if jd.seniority_years_min else ''}
            </div>
        """, unsafe_allow_html=True)

        if jd.must_have_skills:
            st.markdown('<h4>Must-Have Skills</h4>', unsafe_allow_html=True)
            chips = "".join(_chip_html(s.name, "must") for s in jd.must_have_skills[:12])
            st.markdown(f'<div>{chips}</div>', unsafe_allow_html=True)

        if jd.nice_to_have_skills:
            st.markdown('<h4>Nice-to-Have</h4>', unsafe_allow_html=True)
            chips = "".join(_chip_html(s.name, "nice") for s in jd.nice_to_have_skills[:8])
            st.markdown(f'<div>{chips}</div>', unsafe_allow_html=True)

        if jd.behavioral_signals:
            st.markdown('<h4>Behavioral Signals</h4>', unsafe_allow_html=True)
            chips = "".join(_chip_html(s, "matched") for s in jd.behavioral_signals[:6])
            st.markdown(f'<div>{chips}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


def render_metrics_bar(ranked: List[RankedCandidate], total_candidates: int):
    """Render top-level metrics row."""
    strong = sum(1 for r in ranked if r.score_tier == "strong_match")
    good = sum(1 for r in ranked if r.score_tier == "good_match")
    avg_score = sum(r.scores.composite for r in ranked[:10]) / max(len(ranked[:10]), 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card animate-in">
            <span class="metric-value">{total_candidates:,}</span>
            <div class="metric-label">Total Candidates</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card animate-in">
            <span class="metric-value" style="color:#22C55E">{strong}</span>
            <div class="metric-label">Strong Matches</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card animate-in">
            <span class="metric-value" style="color:#4F6EF7">{good}</span>
            <div class="metric-label">Good Matches</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card animate-in">
            <span class="metric-value">{avg_score:.1f}</span>
            <div class="metric-label">Top-10 Avg Score</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


def render_candidate_card(rc: RankedCandidate, jd: Optional[JobDescriptionProfile] = None):
    """Render a collapsible candidate card."""
    tier_class = _score_to_class(rc.score_tier)
    tier_label = TIER_LABELS.get(rc.score_tier, "Stretch")
    tier_color = TIER_COLORS.get(rc.score_tier, "#9CA3AF")
    rank_class = "top3" if rc.rank <= 3 else ""
    composite = rc.scores.composite

    # Collapsed header (always visible)
    header_html = f"""
    <div class="riq-card animate-in" style="margin-bottom:0.5rem">
        <div style="display:flex; align-items:flex-start; gap:0.85rem">
            <div class="rank-badge {rank_class}">#{rc.rank}</div>
            <div style="flex:1">
                <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.5rem">
                    <div>
                        <div style="font-weight:700; font-size:1.05rem; color:#111827">{rc.name or 'Candidate '+rc.candidate_id}</div>
                        <div style="font-size:0.8rem; color:#6B7280; margin-top:0.1rem">
                            {rc.current_title} · {rc.current_company} · {rc.total_experience_years:.1f} yrs
                        </div>
                    </div>
                    <div>
                        <span class="score-badge {tier_class}">{composite:.1f} / 100</span>
                        <span style="font-size:0.7rem; color:{tier_color}; font-weight:600; margin-left:0.4rem">{tier_label}</span>
                    </div>
                </div>
                <div style="margin-top:0.75rem">
                    {_bar_html("Skill Alignment", rc.scores.skill_alignment, "#4F6EF7")}
                    {_bar_html("Experience", rc.scores.experience_relevance, "#7C3AED")}
                    {_bar_html("Career Signal", rc.scores.career_signal, "#0891B2")}
                </div>
                <div style="margin-top:0.6rem; font-size:0.82rem; color:#374151; font-style:italic; border-left:3px solid {tier_color}; padding-left:0.6rem">
                    ✦ {rc.recruiter_rationale[:120]}{'...' if len(rc.recruiter_rationale) > 120 else ''}
                </div>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    # Expandable deep-dive
    with st.expander(f"▼ View full profile — {rc.name or rc.candidate_id}", expanded=False):
        _render_expanded_card(rc, jd)


def _render_expanded_card(rc: RankedCandidate, jd: Optional[JobDescriptionProfile] = None):
    """Full expanded view of a candidate."""
    col_chart, col_info = st.columns([1, 1])

    with col_chart:
        st.plotly_chart(
            render_radar_chart(rc),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with col_info:
        # Full score bars
        st.markdown("**Score Breakdown**")
        st.markdown(
            _bar_html("Skill Alignment", rc.scores.skill_alignment, "#4F6EF7") +
            _bar_html("Experience", rc.scores.experience_relevance, "#7C3AED") +
            _bar_html("Career Signal", rc.scores.career_signal, "#0891B2") +
            _bar_html("Behavioral Fit", rc.scores.behavioral_fit, "#059669") +
            _bar_html("Cultural Align", rc.scores.cultural_alignment, "#D97706"),
            unsafe_allow_html=True,
        )

        # Matched skills
        if rc.top_skills:
            st.markdown("**Matched Skills**")
            chips = "".join(_chip_html(s, "matched") for s in rc.top_skills)
            st.markdown(f'<div>{chips}</div>', unsafe_allow_html=True)

    st.markdown('<div class="riq-divider"></div>', unsafe_allow_html=True)

    # Career timeline
    if rc.career_history:
        st.markdown("**📅 Career Timeline**")
        timeline_html = '<div class="timeline">'
        for entry in rc.career_history:
            period = f"{entry.start_date or '?'} → {entry.end_date or 'Present'}"
            months = f"{entry.duration_months} months" if entry.duration_months else ""
            timeline_html += f"""
            <div class="timeline-entry">
                <div class="timeline-title">{entry.title} @ {entry.company}</div>
                <div class="timeline-meta">{period} · {months} · {entry.industry}</div>
            </div>"""
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)

    st.markdown('<div class="riq-divider"></div>', unsafe_allow_html=True)

    # Rationale & Probe
    col_r, col_p = st.columns(2)
    with col_r:
        st.markdown("**🧠 Recruiter Notes**")
        st.markdown(f'<div class="rationale-box">{rc.recruiter_rationale}</div>', unsafe_allow_html=True)
        if rc.top_strength:
            st.markdown(f'<div style="font-size:0.8rem; color:#6B7280; margin-top:0.5rem">⭐ <strong>Top Strength:</strong> {rc.top_strength}</div>', unsafe_allow_html=True)
    with col_p:
        st.markdown("**❓ Interview Probe**")
        st.markdown(f'<div class="probe-box">💬 {rc.probe_question}</div>', unsafe_allow_html=True)

        # Platform signals
        if rc.redrob_signals:
            sig = rc.redrob_signals
            signals_text = []
            if sig.open_to_work_flag:
                signals_text.append("✅ Open to work")
            if sig.github_activity_score >= 0:
                signals_text.append(f"⚡ GitHub score: {sig.github_activity_score:.0f}")
            signals_text.append(f"📬 Response rate: {sig.recruiter_response_rate:.0%}")
            signals_text.append(f"📅 Notice: {sig.notice_period_days}d")
            if sig.preferred_work_mode:
                signals_text.append(f"🏠 {sig.preferred_work_mode.title()}")
            st.markdown("<br>".join(signals_text), unsafe_allow_html=True)


def render_radar_chart(rc: RankedCandidate) -> go.Figure:
    """Render a 5-axis Plotly radar chart for candidate scores."""
    categories = ["Skill\nAlignment", "Experience\nRelevance", "Career\nSignal",
                  "Behavioral\nFit", "Cultural\nAlignment"]
    values = [
        rc.scores.skill_alignment,
        rc.scores.experience_relevance,
        rc.scores.career_signal,
        rc.scores.behavioral_fit,
        rc.scores.cultural_alignment,
    ]
    # Close the polygon
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()

    # Reference rings
    for pct in [50, 75, 100]:
        fig.add_trace(go.Scatterpolar(
            r=[pct] * (len(categories) + 1),
            theta=categories_closed,
            mode="lines",
            line=dict(color="rgba(0,0,0,0.08)", width=1, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Candidate polygon
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor="rgba(79,110,247,0.18)",
        line=dict(color="#4F6EF7", width=2.5),
        marker=dict(size=6, color="#4F6EF7"),
        showlegend=False,
        hovertemplate="%{theta}: %{r:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                tickfont=dict(size=9, color="#9CA3AF"),
                gridcolor="rgba(0,0,0,0.06)",
                linecolor="rgba(0,0,0,0.1)",
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color="#374151", family="Inter"),
                gridcolor="rgba(0,0,0,0.06)",
                linecolor="rgba(0,0,0,0.1)",
            ),
            bgcolor="rgba(248,249,255,0.8)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=30),
        height=280,
    )
    return fig


def render_processing_state(steps: List[dict]):
    """Render step-by-step processing overlay."""
    items_html = ""
    for step in steps:
        status = step.get("status", "pending")  # done | active | pending
        icon = {"done": "✅", "active": "⚙️", "pending": "○"}[status]
        items_html += f'<div class="step-item {status}">{icon} {step["label"]}</div>'

    st.markdown(f"""
    <div class="processing-card animate-in">
        <div class="processing-icon">⚙</div>
        <h3 style="color:#1A1F36; margin-bottom:1.5rem">Analysing Your Candidates</h3>
        {items_html}
    </div>
    """, unsafe_allow_html=True)
