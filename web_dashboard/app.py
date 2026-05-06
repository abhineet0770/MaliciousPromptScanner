"""
MAPS Web Dashboard
==================
Streamlit-based dashboard for visualizing scan results and analytics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Read API URL and Key from Streamlit Secrets (for cloud) or Environment Variables (for local)
try:
    API_BASE_URL = st.secrets.get("MAPS_API_URL", "https://diptansh-maps-api.hf.space")
    API_KEY = st.secrets.get("MAPS_API_KEY", "maps-secret-key-2026")
except Exception:
    API_BASE_URL = os.environ.get("MAPS_API_URL", "https://diptansh-maps-api.hf.space")
    API_KEY = os.environ.get("MAPS_API_KEY", "maps-secret-key-2026")

# Clean up the URL just in case '/scan_prompt' or trailing slashes were accidentally included in the secret
if API_BASE_URL.endswith('/scan_prompt'):
    API_BASE_URL = API_BASE_URL[:-12]
API_BASE_URL = API_BASE_URL.rstrip('/')

HEADERS = {"X-API-Key": API_KEY}


def check_api_health():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def scan_prompt(prompt: str, detailed: bool = False):
    try:
        response = requests.post(
            f"{API_BASE_URL}/scan_prompt",
            json={"prompt": prompt, "detailed": detailed},
            headers=HEADERS,
            timeout=30
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def get_statistics(hours: int = 24):
    try:
        response = requests.get(f"{API_BASE_URL}/statistics", params={"hours": hours}, headers=HEADERS, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def get_recent_scans(limit: int = 100):
    try:
        response = requests.get(f"{API_BASE_URL}/recent_scans", params={"limit": limit}, headers=HEADERS, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def get_trends(hours: int = 24):
    try:
        response = requests.get(f"{API_BASE_URL}/trends", params={"hours": hours}, headers=HEADERS, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def get_status():
    try:
        response = requests.get(f"{API_BASE_URL}/status", headers=HEADERS, timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html {
        scroll-behavior: smooth;
    }

    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* GSAP-like Entrance Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    .stApp {
        background-color: #0f172a; /* Slate 900 */
        color: #f1f5f9;
    }
    
    .premium-header {
        color: #f8fafc;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        letter-spacing: -0.5px;
        animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    
    .premium-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-top: 5px;
        margin-bottom: 30px;
        font-weight: 400;
        opacity: 0;
        animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards;
    }
    
    .metric-card {
        background: #1e293b; /* Slate 800 */
        border: 1px solid #334155; /* Slate 700 */
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        transition: border-color 0.15s ease, transform 0.15s ease;
        opacity: 0;
        animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    
    .metric-card:hover {
        border-color: #475569; /* Slate 600 */
    }
    
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 600;
        color: #f8fafc;
    }
    
    .metric-value.safe { color: #22c55e; }
    .metric-value.warn { color: #eab308; }
    .metric-value.danger { color: #ef4444; }
    
    .verdict-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 20px;
        border: 1px solid transparent;
        opacity: 0;
        animation: fadeIn 0.4s ease forwards;
    }
    
    .verdict-badge.ALLOW { background-color: rgba(34, 197, 94, 0.1); color: #4ade80; border-color: rgba(34, 197, 94, 0.2); }
    .verdict-badge.WARN { background-color: rgba(234, 179, 8, 0.1); color: #facc15; border-color: rgba(234, 179, 8, 0.2); }
    .verdict-badge.BLOCK { background-color: rgba(239, 68, 68, 0.1); color: #f87171; border-color: rgba(239, 68, 68, 0.2); }
    
    .stButton>button {
        background-color: #2563eb; /* Blue 600 */
        color: white;
        border: 1px solid #1d4ed8; /* Blue 700 */
        border-radius: 6px;
        font-weight: 500;
        transition: background-color 0.15s;
    }
    .stButton>button:hover {
        background-color: #1d4ed8; /* Blue 700 */
        color: white;
    }
    
    div[data-testid="stExpander"] {
        background: #1e293b;
        border-radius: 8px;
        border: 1px solid #334155;
        animation: fadeIn 0.6s ease forwards;
    }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown('<h1 class="premium-header">MAPS Shield</h1>', unsafe_allow_html=True)
    st.markdown('<p class="premium-subtitle">Advanced Multi-Layer AI Prompt Security Engine</p>', unsafe_allow_html=True)
    st.divider()


def render_scanner():
    st.header("Prompt Scanner")
    
    prompt = st.text_area("Enter prompt to scan:", height=100, placeholder="Type or paste a prompt here...")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        scan_button = st.button("Scan Prompt", type="primary", use_container_width=True)
    with col2:
        detailed = st.checkbox("Show detailed results", value=False)
    
    if scan_button and prompt:
        with st.spinner("Scanning prompt..."):
            result = scan_prompt(prompt, detailed)
        
        if result:
            render_scan_result(result, detailed)


def render_scan_result(result: dict, detailed: bool):
    st.markdown("<br>", unsafe_allow_html=True)
    
    decision = result.get('decision', 'UNKNOWN')
    icon = "✅" if decision == "ALLOW" else "⚠️" if decision == "WARN" else "🚫"
    
    st.markdown(f'<div class="verdict-badge {decision}">{icon} Decision: {decision}</div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    
    risk_score = result.get('risk_score', 0)
    score_class = "safe" if risk_score < 30 else "warn" if risk_score < 60 else "danger"
    
    with c1:
        st.markdown(f'''
        <div class="metric-card" style="animation-delay: 0.1s;">
            <div class="metric-label">Risk Score</div>
            <div class="metric-value {score_class}">{risk_score}/100</div>
        </div>
        ''', unsafe_allow_html=True)
        
    classification = result.get('classification', 'UNKNOWN')
    class_color = "safe" if classification == "SAFE" else "warn" if classification == "SUSPICIOUS" else "danger"
    with c2:
        st.markdown(f'''
        <div class="metric-card" style="animation-delay: 0.2s;">
            <div class="metric-label">Classification</div>
            <div class="metric-value {class_color}">{classification}</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with c3:
        st.markdown(f'''
        <div class="metric-card" style="animation-delay: 0.3s;">
            <div class="metric-label">Confidence</div>
            <div class="metric-value" style="color: #60a5fa;">{result.get('confidence', 0):.0%}</div>
        </div>
        ''', unsafe_allow_html=True)
        
    with c4:
        st.markdown(f'''
        <div class="metric-card" style="animation-delay: 0.4s;">
            <div class="metric-label">Scan Time</div>
            <div class="metric-value" style="color: #94a3b8;">{result.get('scan_time_ms', 0):.0f}ms</div>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.info(f"📋 Reason: {result.get('reason', 'N/A')}")
    
    detectors = result.get('detectors_triggered', [])
    if detectors:
        st.markdown("**Detectors Triggered:**")
        for detector in detectors:
            st.write(f"  - `{detector}`")
    
    categories = result.get('categories', [])
    if categories:
        st.markdown(f"**Attack Categories:** `{'`, `'.join(categories)}`")

    # LLM verdict badge (shown even outside detailed mode)
    llm_analysis = result.get('llm_analysis')
    if result.get('llm_invoked') and llm_analysis:
        verdict = llm_analysis.get('verdict', '')
        reason  = llm_analysis.get('reason', '')
        model   = llm_analysis.get('model', 'LLM')
        latency = llm_analysis.get('latency_ms', '')
        badge   = {'MALICIOUS': '🔴', 'SUSPICIOUS': '🟡', 'SAFE': '🟢'}.get(verdict, '🔵')
        st.markdown(f"> {badge} **Layer 8 LLM Verdict ({model}):** `{verdict}`  \n> {reason}  \n> _(response time: {latency}ms)_")

    # --- Detailed Analysis Section ---
    if detailed:
        layer_results = result.get('layer_results')
        risk_details = result.get('risk_details')

        st.divider()
        st.markdown("## 🔍 Detailed Layer Analysis")

        LAYER_ICONS = {
            'keyword_detection':   '🔑',
            'regex_detection':     '🔤',
            'ngram_detection':     '📝',
            'semantic_similarity': '🧠',
            'ml_classifier':       '🤖',
            'rule_engine':         '⚙️',
            'llm_classifier':      '🌐',
        }

        if layer_results:
            # Build a lookup from risk_details for per-layer scores
            layer_breakdown = {}
            if risk_details:
                layer_breakdown = risk_details.get('layer_breakdown', {})

            for lr in layer_results:
                layer_name = lr.get('layer', 'unknown')
                triggered  = lr.get('triggered', False)
                confidence = lr.get('confidence', 0.0)
                icon       = LAYER_ICONS.get(layer_name, '🔹')
                label      = layer_name.replace('_', ' ').title()
                status     = "🔴 TRIGGERED" if triggered else "🟢 Clean"

                # Pull weighted score from risk_details breakdown
                breakdown  = layer_breakdown.get(layer_name, {})
                layer_score    = breakdown.get('score', 0)
                layer_weight   = breakdown.get('weight', 0)
                layer_mult     = breakdown.get('multiplier', 0)

                with st.expander(f"{icon} {label}  —  {status}  ({confidence:.0%} confidence)", expanded=triggered):
                    st.markdown("**Confidence**")
                    st.progress(min(confidence, 1.0))

                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("Confidence", f"{confidence:.1%}")
                    with col_b:
                        st.metric("Weighted Score", f"{layer_score:.2f}")
                    with col_c:
                        st.metric("Layer Weight", f"{layer_weight}")
                    with col_d:
                        st.metric("Multiplier", f"{layer_mult:.2f}" if layer_mult else "—")

                    # Key findings per layer type
                    if layer_name == 'keyword_detection':
                        matches = lr.get('matches', [])
                        cats    = lr.get('categories', [])
                        details = lr.get('details', {})
                        if matches:
                            st.markdown("**Matched Keywords:**")
                            st.code(', '.join(str(m) for m in matches[:20]))
                        if cats:
                            st.markdown(f"**Categories:** {', '.join(cats)}")
                        if details:
                            nm = details.get('num_matches', len(matches))
                            st.caption(f"Total keyword hits: {nm}")

                    elif layer_name == 'regex_detection':
                        patterns = lr.get('matches', [])
                        details  = lr.get('details', {})
                        if patterns:
                            st.markdown("**Matched Patterns:**")
                            for p in patterns:
                                name = p.get('name', str(p))
                                sev  = p.get('severity', '')
                                desc = p.get('description', '')
                                st.write(f"  - **`{name}`** ({sev}) — {desc}")
                        if details:
                            sev = details.get('severity_breakdown', {})
                            if any(v for v in sev.values()):
                                st.markdown("**Severity Breakdown:**")
                                for level, count in sev.items():
                                    if count:
                                        st.write(f"  - {level.capitalize()}: {count}")

                    elif layer_name == 'ngram_detection':
                        details = lr.get('details', {})
                        nm     = details.get('num_templates_matched', 0) if details else 0
                        scores = details.get('overlap_scores', {}) if details else {}
                        st.write(f"**Templates matched:** {nm}")
                        if scores:
                            st.markdown("**Top overlap scores:**")
                            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
                            for template, score in top:
                                st.write(f"  - `{template[:70]}` → {score:.0%}")

                    elif layer_name == 'semantic_similarity':
                        details = lr.get('details', {})
                        if details:
                            sim  = details.get('max_similarity', 0)
                            mode = details.get('mode', 'unknown')
                            st.write(f"**Max similarity:** {sim:.1%}")
                            st.write(f"**Detection mode:** {mode}")

                    elif layer_name == 'ml_classifier':
                        details = lr.get('details', {})
                        if details:
                            prob = details.get('malicious_probability', confidence)
                            st.write(f"**Malicious probability:** {prob:.1%}")

                    elif layer_name == 'rule_engine':
                        details = lr.get('details', {})
                        if details:
                            rules = details.get('triggered_rules', [])
                            if rules:
                                st.markdown("**Rules fired:**")
                                for r in rules:
                                    st.write(f"  - `{r}`")

                    elif layer_name == 'llm_classifier':
                        details = lr.get('details', {})
                        if details.get('skipped'):
                            st.info(f"⏭️ Skipped: {details.get('reason', 'Not in ambiguity band')}")
                        elif details.get('error'):
                            st.error(f"❌ Error: {details.get('error')}")
                        else:
                            verdict     = details.get('verdict', 'N/A')
                            attack_type = details.get('attack_type', 'N/A')
                            reason_text = details.get('reason', 'N/A')
                            model_used  = details.get('model', 'N/A')
                            latency     = details.get('latency_ms', 'N/A')
                            badge = {'MALICIOUS': '🔴', 'SUSPICIOUS': '🟡', 'SAFE': '🟢'}.get(verdict, '🔵')
                            st.markdown(f"**LLM Verdict:** {badge} `{verdict}`")
                            st.markdown(f"**Attack Type Identified:** `{attack_type}`")
                            st.info(f"💬 Reasoning: {reason_text}")
                            col_m, col_l = st.columns(2)
                            with col_m:
                                st.caption(f"Model: `{model_used}`")
                            with col_l:
                                st.caption(f"Latency: `{latency}ms`")

                    if lr.get('error'):
                        st.warning("⚠️ This layer encountered an error during detection.")
        else:
            st.info("No per-layer data available.")

        # Risk Score Breakdown
        if risk_details:
            st.divider()
            st.markdown("### 📊 Risk Score Breakdown")

            raw_score    = risk_details.get('raw_score', 0)
            max_possible = risk_details.get('max_possible_score', 135)
            final_score  = result.get('risk_score', 0)

            # Compute base normalised score (before bonuses)
            base_normalised = int((raw_score / max_possible) * 100) if max_possible else 0
            # Adjustment = whatever bonus was added on top of the base
            adjustment = final_score - base_normalised

            r1, r2, r3, r4 = st.columns(4)
            with r1:
                st.metric("Raw Score", f"{raw_score:.2f}",
                          help="Sum of (weight × multiplier × confidence) across all triggered layers")
            with r2:
                st.metric("Base (Normalised)", str(base_normalised),
                          help=f"raw_score / max_possible ({max_possible}) × 100, scaled to 0–100")
            with r3:
                delta_str = f"+{adjustment}" if adjustment >= 0 else str(adjustment)
                st.metric("Adjustment", delta_str,
                          help="Bonus points added for high-confidence consensus, critical patterns, or dangerous categories")
            with r4:
                st.metric("Final Score", f"{final_score} / 100",
                          help="Base + Adjustment, capped at 100")

            # Explain what caused the adjustment
            if adjustment > 0:
                st.markdown("**Why was a bonus applied?** The system adds extra points when:")
                if adjustment >= 20:
                    st.write("  ➕ **+20** — Attack categories include hacking, malware, illegal, or violence")
                if adjustment >= 15:
                    st.write("  ➕ **+15** — A critical regex pattern matched (e.g. 'reveal system prompt')")
                high_conf = sum(1 for lr in (layer_results or [])
                                if lr.get('triggered') and lr.get('confidence', 0) > 0.8)
                if high_conf >= 2:
                    st.write(f"  ➕ **+15** — {high_conf} layers all reported >80% confidence")
            elif adjustment < 0:
                st.write("  📉 Score was **reduced** because only one weak layer triggered (confidence < 50%)")


def render_statistics():
    st.header("Statistics")

    hours = st.select_slider("Time Window", options=[1, 6, 12, 24, 48, 72, 168], value=24, format_func=lambda x: f"{x} hours")

    stats = get_statistics(hours)

    if stats:
        st.markdown("### Summary")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Scans", stats.get('total_scans', 0))
        with c2:
            st.metric("Avg Risk Score", f"{stats.get('average_risk_score', 0):.1f}")
        with c3:
            by_decision = stats.get('by_decision', {})
            st.metric("Blocked", by_decision.get('BLOCK', 0))
        with c4:
            st.metric("Warnings", by_decision.get('WARN', 0))
        
        st.subheader("Classification Breakdown")
        by_classification = stats.get('by_classification', {})
        if by_classification:
            fig = px.pie(
                values=list(by_classification.values()),
                names=list(by_classification.keys()),
                title="Scans by Classification",
                color=list(by_classification.keys()),
                color_discrete_map={'SAFE': '#10b981', 'SUSPICIOUS': '#f59e0b', 'MALICIOUS': '#ef4444'}
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#cbd5e1', family='Inter')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Top Detectors Triggered")
        top_detectors = stats.get('top_detectors', {})
        if top_detectors:
            df = pd.DataFrame(list(top_detectors.items()), columns=['Detector', 'Count']).head(10)
            fig = px.bar(df, x='Detector', y='Count', title="Most Triggered Detectors")
            fig.update_traces(marker_color='#3b82f6')
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#cbd5e1', family='Inter')
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No statistics available. Start scanning prompts to see data.")


def render_trends():
    st.header("Trends")
    
    hours = st.select_slider("Trend Time Window", options=[6, 12, 24, 48, 72], value=24, format_func=lambda x: f"{x} hours", key="trend_hours")
    
    trends_data = get_trends(hours)
    
    if trends_data and trends_data.get('trends'):
        df = pd.DataFrame(trends_data['trends'])
        
        for col in ['SAFE', 'SUSPICIOUS', 'MALICIOUS']:
            if col not in df.columns:
                df[col] = 0
        
        fig = go.Figure()
        
        if 'SAFE' in df.columns:
            fig.add_trace(go.Scatter(x=df['hour'], y=df['SAFE'], name='SAFE', line=dict(color='#10b981'), fill='tonexty'))
        if 'SUSPICIOUS' in df.columns:
            fig.add_trace(go.Scatter(x=df['hour'], y=df['SUSPICIOUS'], name='SUSPICIOUS', line=dict(color='#f59e0b'), fill='tonexty'))
        if 'MALICIOUS' in df.columns:
            fig.add_trace(go.Scatter(x=df['hour'], y=df['MALICIOUS'], name='MALICIOUS', line=dict(color='#ef4444'), fill='tonexty'))
        
        fig.update_layout(
            title="Scan Trends Over Time", 
            xaxis_title="Hour", 
            yaxis_title="Number of Scans", 
            hovermode='x unified',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#cbd5e1', family='Inter')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available yet.")


def render_recent_scans():
    st.header("Recent Scans")
    
    scans_data = get_recent_scans(limit=50)
    
    if scans_data and scans_data.get('logs'):
        logs = scans_data['logs']
        df = pd.DataFrame(logs)
        
        display_cols = ['timestamp', 'prompt', 'classification', 'risk_score', 'decision']
        available_cols = [c for c in display_cols if c in df.columns]
        df_display = df[available_cols].copy()
        
        if 'prompt' in df_display.columns:
            df_display['prompt'] = df_display['prompt'].str[:80] + '...'
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No recent scans available.")


def render_status():
    st.header("System Status")
    
    status = get_status()
    
    if status:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Layer Status")
            enabled_layers = status.get('enabled_layers', {})
            for layer, enabled in enabled_layers.items():
                if enabled:
                    st.success(f"{layer}")
                else:
                    st.error(f"{layer}")
        
        with col2:
            st.subheader("Model Information")
            st.write(f"ML Model Type: {status.get('ml_model_type', 'N/A')}")
            st.write(f"ML Trained: {'Yes' if status.get('ml_trained') else 'No'}")
            st.write(f"Keywords: {status.get('num_keywords', 0)}")
            st.write(f"Regex Patterns: {status.get('num_regex_patterns', 0)}")
            st.write(f"N-gram Templates: {status.get('num_ngram_templates', 0)}")
            st.write(f"Semantic Examples: {status.get('num_semantic_examples', 0)}")
        
        st.subheader("Risk Thresholds")
        thresholds = status.get('risk_thresholds', {})
        st.write(f"Safe: 0-{thresholds.get('safe_max', 30)}")
        st.write(f"Suspicious: {thresholds.get('safe_max', 30)+1}-{thresholds.get('suspicious_max', 60)}")
        st.write(f"Malicious: {thresholds.get('suspicious_max', 60)+1}-100")
    else:
        st.error("Unable to fetch system status. Is the API running?")


def main():
    st.set_page_config(page_title="MAPS Security", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
    inject_custom_css()
    
    st.sidebar.title("MAPS")
    st.sidebar.markdown("Malicious AI Prompt Scanner")
    st.sidebar.divider()
    
    page = st.sidebar.radio("Navigation", ["Scanner", "Statistics", "Trends", "Recent Scans", "System Status"])
    
    if not check_api_health():
        st.sidebar.error("API Offline")
        st.sidebar.info("Start the API with: python -m backend.api.main")
    else:
        st.sidebar.success("API Online")
    
    render_header()
    
    if page == "Scanner":
        render_scanner()
    elif page == "Statistics":
        render_statistics()
    elif page == "Trends":
        render_trends()
    elif page == "Recent Scans":
        render_recent_scans()
    elif page == "System Status":
        render_status()
    
    st.sidebar.divider()
    st.sidebar.caption("MAPS v1.0.0 - AI Security")


if __name__ == "__main__":
    main()
