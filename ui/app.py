import streamlit as st
import time
import api
import stream
import utils

# -------------------------------------------------------------------------
# 1. Config & State Init
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="Agentic AI System",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 600; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1rem; }
    .stAlert { padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# --- CRITICAL STATE MANAGEMENT ---
if "task_id" not in st.session_state:
    st.session_state.task_id = None

# Store FULL Event History
if "events" not in st.session_state:
    st.session_state.events = []

# Tracker for current step in UI
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

# Flag to stop streaming
if "stream_completed" not in st.session_state:
    st.session_state.stream_completed = False

# Optimized Buffer for Final Output (Text Only)
if "final_output" not in st.session_state:
    st.session_state.final_output = ""

# -------------------------------------------------------------------------
# 2. Sidebar
# -------------------------------------------------------------------------
with st.sidebar:
    st.header("⚡ System Status")
    backend_up = api.check_backend()
    
    st.markdown(f"**Backend API**")
    if backend_up: st.success("🟢 Online")
    else: st.error("🔴 Offline")

    st.markdown(f"**Redis Bus**")
    st.warning("⚠️ Fake / In-Memory Mode")
    
    st.divider()
    st.subheader("👁️ Live Status")
    
    # Determine Active Node
    active_node = "Orchestrator" 
    step = st.session_state.current_step
    if step == 0: active_node = "None"
    if step == 1: active_node = "Planner"
    if step == 2: active_node = "Orchestrator"
    if step >= 3: active_node = "Swarm" 
    if step == 4: active_node = "Writer"
    if step == 5: active_node = "Done"

    # Dynamic Formatting
    def get_fmt(node_name):
        fill = "#1E1E1E"
        font = "white"
        color = "#555555"
        pen = 1
        
        if node_name == active_node:
            fill = "#00C853" # Green
            color = "#00C853"
            pen = 2
        elif step > 5: # Done state
            fill = "#333333"
            font = "#888888"
            
        return f'fillcolor="{fill}" fontcolor="{font}" color="{color}" penwidth={pen}'

    # Vertical Layout for Sidebar
    graph = f"""
    digraph G {{
        rankdir=TB;
        bgcolor="transparent";
        node [shape=box style="filled,rounded" fontname="Helvetica" fontsize=10 height=0.4];
        edge [fontsize=8 color="#666666" arrowsize=0.6 fontcolor="#aaaaaa"];
        
        # Enforce User at Top
        {{ rank=source; User }}
        
        User [label="User" shape=circle style=filled fillcolor="#2196F3" fontcolor="white" color="#2196F3" width=0.6 fixedsize=true];
        Orchestrator [label="Orchestrator" {get_fmt('Orchestrator')}];
        Planner [label="Planner" {get_fmt('Planner')}];
        
        subgraph cluster_workers {{
            label = "Agent Swarm";
            style = dashed; color = "#444444"; fontcolor = "#888888"; 
            margin=10;
            
            Retriever [label="Retriever" {get_fmt('Swarm')}];
            Analyzer [label="Analyzer" {get_fmt('Swarm')}];
            Writer [label="Writer" {get_fmt('Swarm')}];
            
            # Invisible edge to force vertical ordering within cluster
            Retriever -> Analyzer [style="invis"];
            Analyzer -> Writer [style="invis"];
        }}
        
        # Main Flow
        User -> Orchestrator [label="Start"];
        Orchestrator -> Planner [dir=both label="Plan"];
        Orchestrator -> Retriever [label="Dispatch"];
        
        # Worker Flow (Explicit)
        Retriever -> Analyzer;
        Analyzer -> Writer;
        
        # Feedback Loop
        Writer -> User [label="Stream" color="#2196F3" style="dashed"];
    }}
    """
    st.graphviz_chart(graph, use_container_width=True)
    st.info("System is running in **Developer Mode**.")

# -------------------------------------------------------------------------
# 3. Main Header
# -------------------------------------------------------------------------
col_head_1, col_head_2 = st.columns([3, 1])
with col_head_1:
    st.title("Agentic AI Orchestrator")
    st.markdown("##### 🚀 Event-Driven Multi-Agent System")
with col_head_2:
    st.markdown("") 
    if st.button("🔄 Reset System", type="secondary"):
        st.session_state.task_id = None
        st.session_state.events = []
        st.session_state.current_step = 0
        st.session_state.stream_completed = False
        st.session_state.final_output = ""
        st.rerun()

st.divider()

# -------------------------------------------------------------------------
# 4. Input Panel
# -------------------------------------------------------------------------
if not st.session_state.task_id:
    st.markdown("### 🎯 Submit New Mission")
    with st.form("task_form", clear_on_submit=False):
        prompt = st.text_area("Task Description", height=120, placeholder="e.g., Research...")
        submitted = st.form_submit_button("Start Mission", type="primary", disabled=not backend_up)
            
        if submitted and prompt:
            with st.spinner("Initializing Agent Swarm..."):
                task_id = api.submit_task(prompt)
                time.sleep(0.5) 
                if task_id:
                    # RESET STATE FOR NEW TASK
                    st.session_state.task_id = task_id
                    st.session_state.task_prompt = prompt # Save prompt for display
                    st.session_state.current_step = 0
                    st.session_state.stream_completed = False
                    st.session_state.events = []
                    st.session_state.final_output = ""
                    st.rerun()
                else:
                    st.error("Failed to contact backend.")

# -------------------------------------------------------------------------
# 5. Active Execution View
# -------------------------------------------------------------------------
if st.session_state.task_id:
    
    # --- Mission Objective Header ---
    st.markdown(f"### 🎯 Current Mission: {st.session_state.get('task_prompt', 'Unknown Task')}")
    st.divider()

    # --- B. Telemetry & Output Columns ---
    col_log, col_out = st.columns([1, 1.5], gap="large")

    with col_log:
        st.subheader("📠 Agent Telemetry")
        with st.container(height=550, border=True):
            for e in st.session_state.events:
                ts = utils.format_timestamp()
                source = e.get('source', 'System').upper()
                msg = e.get('message', '')
                st.markdown(f"<small style='color:#666'>{ts}</small> :bound[{source}]  \n{msg}", unsafe_allow_html=True)
                st.markdown("---")

    with col_out:
        st.subheader("📄 Mission Report")
        with st.container(height=550, border=True):
            output_placeholder = st.empty()
            
            # 1. ALWAYS RENDER ACCUMULATED OUTPUT
            if not st.session_state.final_output:
                output_placeholder.info("⏳ Awaiting intelligence report...")
            else:
                # Render Markdown
                output_placeholder.markdown(st.session_state.final_output)
                if not st.session_state.stream_completed:
                     st.caption("🟢 _Receiving transmission..._")

    # --- C. EVENT CONSUMPTION (THE FIX) ---
    # Only connect if we haven't finished yet
    if not st.session_state.stream_completed:
        
        # Generator that yields events
        for event in stream.stream_events(st.session_state.task_id):
            
            # 1. Update Logs (in-memory)
            st.session_state.events.append(event)
            
            # 2. Update Progress Graph
            src = event.get("source", "").lower()
            if "planner" in src: st.session_state.current_step = 1
            if "retriever" in src: st.session_state.current_step = 3
            if "analyzer" in src: st.session_state.current_step = 3
            if "writer" in src: st.session_state.current_step = 4
            
            # 3. ACCUMULATE OUTPUT (The Critical Fix)
            if event.get("type") == "partial_output":
                chunk = event.get("message", "")
                st.session_state.final_output += chunk
                # Force live update of the placeholder
                output_placeholder.markdown(st.session_state.final_output + "▌")
            
            # 4. Handle Completion
            if event.get("type") == "done":
                st.session_state.current_step = 5
                st.session_state.stream_completed = True
                
                # Rerun one last time to finalize UI state (remove cursor, update graph)
                st.rerun()

# -------------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------------
st.markdown("---")
st.markdown("""<div style="text-align: center; color: #666; font-size: 0.8rem;">
    Agentic AI System v1.1 · Robust State Management · Powered by FastAPI & Redis
</div>""", unsafe_allow_html=True)
