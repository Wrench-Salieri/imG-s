from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

import api_client
from components.theme import TEAL, AMBER, RED, MUTED, TEXT, style_figure

APP_DIR = Path(__file__).parent
im = Image.open(APP_DIR / "components" / "images" / "favicon.png")

st.set_page_config(page_title="imG's", page_icon=im, layout="wide")

START_COMMAND = "python -m uvicorn --app-dir backend api:app --reload"

def image_figure(z, colorscale="gray", zmin=0.0, zmax=1.0):
    fig = go.Figure(
        go.Heatmap(z=z, colorscale=colorscale, zmin=zmin, zmax=zmax,
                   showscale=False, hoverinfo="skip")
    )
    style_figure(fig, height=340)
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, autorange="reversed", scaleanchor="x"),
    )
    return fig

def call_api(func, *args):
    try:
        return func(*args)
    except api_client.ApiNotReady as err:
        st.info(f"Waiting for the Physics & DSP team. {err}")
    except api_client.ApiOffline as err:
        st.error(f"{err} Start it in a second terminal, from the project root:")
        st.code(START_COMMAND, language="bash")
    except api_client.ApiError as err:
        st.error(f"The backend rejected the request: {err}")
    return None


@st.cache_data(ttl=300, show_spinner=False)
def load_parameters():
    return api_client.get_parameters()


@st.cache_data(show_spinner=False)
def run_simulation(params, seed, scenario):
    return api_client.simulate(params, seed, scenario)

@st.cache_data(show_spinner=False)
def run_sweep(params, seed, name, points):
    return api_client.sweep(params, seed, name, points)

def show_results(simulation, meta, prefix):
    """Metrics, rack check and the three images for one simulation result."""
    metrics = simulation["metrics"]
    ideal = np.array(simulation["images"]["ideal"])
    simulated = np.array(simulation["images"]["simulated"])
    max_volume = meta["iss_rack_max_volume_m3"]
    max_weight = meta["iss_rack_max_weight_kg"]
    max_ssim = meta["ssim_max"]
    min_ssim = meta["ssim_min"]

    a, b, c = st.columns(3)
    a.metric("SSIM", f"{metrics['SSIM']:.3f}",
             help="Structural similarity to the ideal image (1 is perfect).")
    b.metric("PSNR", f"{metrics['PSNR_dB']:.1f} dB",
             help="Peak signal-to-noise ratio against the ideal image.")
    c.metric("ISS rack", "Compatible" if metrics["ISS_Rack_Compatible"] else "Does not fit")

    volume, weight = metrics["Volume_m3"], metrics["Weight_kg"]
    d, e, f = st.columns(3)
    d.metric("Scanner volume", f"{volume:.3f} m³",
             delta=f"{volume - max_volume:+.3f} m³ vs rack limit", delta_color="inverse")
    e.metric("Estimated weight", f"{weight:.0f} kg",
             delta=f"{weight - max_weight:+.0f} kg vs rack limit", delta_color="inverse")
    f.metric("Power", f"{metrics['Power_W']:,.0f} W")

    if metrics["ISS_Rack_Compatible"]:
        st.success(f"This scanner fits an ISS rack (volume up to {max_volume} m³ "
                   f"and weight up to {max_weight:.0f} kg).")
    else:
        st.error("This scanner does not fit an ISS rack. Reduce the bore, the length "
                 "or the field strength.")
    ssim = metrics["SSIM"]
    if metrics["SSIM_Compatible"]:
        st.success(f"Scan quality is in the acceptable range "
                   f"(SSIM {ssim:.2f}, target {min_ssim:.2f} to {max_ssim:.2f}).")
    elif ssim < min_ssim:
        st.error(f"Scan quality is too low (SSIM {ssim:.2f}, minimum {min_ssim:.2f}). "
                 f"Reduce the vibration or increase the averaging.")
    else:
        st.warning(f"Scan quality is above the target range (SSIM {ssim:.2f}, "
                   f"maximum {max_ssim:.2f}).")

    left, middle, right = st.columns(3)
    left.markdown("**Ideal phantom**")
    left.plotly_chart(image_figure(ideal), key=f"{prefix}_ideal")
    middle.markdown("**Simulated scan**")
    middle.plotly_chart(image_figure(simulated), key=f"{prefix}_simulated")
    right.markdown("**Difference**")
    diff = np.abs(ideal - simulated)
    right.plotly_chart(image_figure(diff, "magma", 0.0, max(float(diff.max()), 0.05)),
                       key=f"{prefix}_diff")

meta = call_api(load_parameters)
if meta is None:
    st.stop()                     # no backend, no sliders: the message above says what to do
specs = {p["name"]: p for p in meta["parameters"]}

st.sidebar.header("Scanner settings")
params = {}
for group, names in meta["groups"].items():
    st.sidebar.subheader(group)
    for name in names:
        spec = specs[name]
        cast = int if spec["is_int"] else float        # JSON turns 2 into 2.0: restore whole numbers
        label = f"{spec['label']} ({spec['unit']})" if spec["unit"] else spec["label"]
        params[name] = st.sidebar.slider(
            label, cast(spec["minimum"]), cast(spec["maximum"]),
            cast(spec["default"]), cast(spec["step"]), help=spec["help"], key=name,
        )

st.sidebar.subheader("Test image")
phantom = call_api(api_client.get_phantom_info)
if phantom is not None:
    st.sidebar.caption(f"Current image: {phantom['name']}")

uploader_key = f"phantom_uploader_{st.session_state.get('uploader_n', 0)}"
uploaded = st.sidebar.file_uploader(
    "Upload your own image", type=["png", "jpg", "jpeg", "npy"], key=uploader_key,
    help="A grayscale MRI slice works best. It is cut to a square and resized to 128 x 128.",
)
if uploaded is not None:
    token = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("phantom_token") != token:
        if call_api(api_client.upload_phantom, uploaded.name, uploaded.getvalue()) is not None:
            st.session_state["phantom_token"] = token
            st.session_state.pop("mission", None)      # an old Mission Control result shows the old image
            st.cache_data.clear()                      # cached simulations belong to the old image
            st.rerun()

if st.sidebar.button("Use the default image"):
    if call_api(api_client.reset_phantom) is not None:
        st.session_state["uploader_n"] = st.session_state.get("uploader_n", 0) + 1   # empties the upload box
        st.session_state.pop("phantom_token", None)
        st.session_state.pop("mission", None)
        st.cache_data.clear()
        st.rerun()
        
seed = 42

st.title("imG's MRI Designer (name subject to change)")
st.caption("A portable MRI designer for the ISS.")

tab_design, tab_mission, tab_sweep = st.tabs(
    ["Engineering Design Mode", "Mission Control Mode", "Parameter sweep"]
)

with tab_design:
    st.subheader("Engineering Design Mode")
    st.caption("Move the sliders in the sidebar to design the scanner and see the result.")

    SOURCES = {
        "custom": "Custom (use the vibration sliders)",
        "quiet": "Quiet ambient (NASA SAMS recording)",
        "disturbed": "Orbital Maneuver (Thrusters), not quiet (NASA SAMS recording)",
    }
    choice = st.selectbox("Vibration source", list(SOURCES), format_func=lambda key: SOURCES[key],
                          key="design_source")
    scenario = None if choice == "custom" else choice
    if scenario:
        st.caption("The scan uses the recording. The vibration intensity and frequency sliders "
                   "are ignored; vibration sensitivity still applies.")

    result = call_api(run_simulation, params, seed, scenario)
    
    if result is not None:
        show_results(result, meta, "design")
    with st.expander("What do the parameters mean?"):
        st.dataframe(pd.DataFrame([
            {
                "Parameter": p["name"],
                "Description": p["help"],
                "Range": f"{p['minimum']:g} to {p['maximum']:g} {p['unit']}".strip(),
                "Default": f"{p['default']:g}",
            }
            for p in meta["parameters"]
        ]))

with tab_mission:
    st.subheader("Mission Control Mode")
    st.caption(
        "Takes your design from the sidebar (field strength, helium, averaging, scanner size) "
        "and simulates the scan under the ISS conditions of this moment. Vibration comes from "
        "telemetry, not from the sliders."
    )

    design = {k: v for k, v in params.items() if k not in ("g_level_mg", "vibration_freq_hz")}
    this_run = {**design, "seed": seed}

    live = st.toggle("Live updates (every 5 seconds)", key="mission_live")
    clicked = st.button("Fetch live ISS data and simulate")

    @st.fragment(run_every=5 if live else None)
    def mission_panel(clicked):
        if live or clicked:
            mission = call_api(api_client.mission, design, seed)
            if mission is not None:
                st.session_state["mission"] = mission
                st.session_state["mission_run"] = this_run

        mission = st.session_state.get("mission")
        if mission is None:
            st.caption("Press the button to load live data.")
            return

        if st.session_state.get("mission_run") != this_run:
            st.warning("The sidebar settings changed since this run. Press the button again to update.")

        tel = mission["telemetry"]
        if tel["b0_penalty_tesla"] > 0:
            st.warning(tel["environment_status"])
        else:
            st.success(tel["environment_status"])

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("ISS activity", tel["iss_activity"])
        t2.metric("Vibration", f"{tel['live_g_level_mg']:.1f} milli-g")
        t3.metric("Frequency", f"{tel['live_vibration_hz']:.1f} Hz")
        t4.metric("Effective B0", f"{mission['effective_b0_tesla']:.3f} T",
                  delta=f"{-tel['b0_penalty_tesla']:+.3f} T radiation penalty",
                  delta_color="inverse")

        if tel["position_live"]:
            position = f"{tel['latitude']:.1f}°, {tel['longitude']:.1f}°"
        else:
            position = "unavailable (offline)"
        st.caption(f"ISS position: {position}  |  recorded {tel['timestamp_utc']} UTC  |  "
                   "vibration profile: scripted demo scenario, not SAMS-II data")

        show_results(mission["simulation"], meta, "mission")

    mission_panel(clicked)

with tab_sweep:
    st.subheader("Parameter sweep")
    st.caption("Change one setting across its whole range, keep the others from the sidebar, "
               "and see how quality, size, weight and power respond.")

    sweep_name = st.selectbox(
        "Setting to sweep", list(specs), format_func=lambda n: specs[n]["label"],
    )
    points = st.slider("Number of points", 5, 25, 11)
    spec = specs[sweep_name]
    axis_title = f"{spec['label']} ({spec['unit']})" if spec["unit"] else spec["label"]

    data = call_api(run_sweep, params, seed, sweep_name, points)
    if data is not None:
        df = pd.DataFrame([{"value": row["value"], **row["metrics"]} for row in data["rows"]])
        current = params[sweep_name]
        marker_colors = [TEAL if ok else RED for ok in df["ISS_Rack_Compatible"]]

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Image quality**")
            qfig = go.Figure()
            qfig.add_trace(go.Scatter(x=df["value"], y=df["SSIM"], name="SSIM",
                                      mode="lines+markers", line=dict(color=TEAL, width=2.5)))
            qfig.add_trace(go.Scatter(x=df["value"], y=df["PSNR_dB"], name="PSNR (dB)",
                                      mode="lines+markers", yaxis="y2",
                                      line=dict(color=MUTED, dash="dash")))
            qfig.add_vline(x=current, line_dash="dot", line_color="white")
            style_figure(qfig, height=380)
            qfig.update_layout(
                xaxis=dict(title=axis_title),
                yaxis=dict(title="SSIM"),
                yaxis2=dict(title="PSNR (dB)", overlaying="y", side="right"),
            )
            st.plotly_chart(qfig, key="sweep_quality")

        with c2:
            st.markdown("**Weight and power**")
            wfig = go.Figure()
            wfig.add_trace(go.Scatter(x=df["value"], y=df["Weight_kg"], name="Weight (kg)",
                                      mode="lines+markers",
                                      line=dict(color=AMBER, width=2.5),
                                      marker=dict(color=marker_colors, size=8)))
            wfig.add_trace(go.Scatter(x=df["value"], y=df["Power_W"], name="Power (W)",
                                      mode="lines+markers", yaxis="y2",
                                      line=dict(color=MUTED, dash="dash")))
            wfig.add_vline(x=current, line_dash="dot", line_color="white")
            style_figure(wfig, height=380)
            wfig.update_layout(
                xaxis=dict(title=axis_title),
                yaxis=dict(title="Weight (kg)"),
                yaxis2=dict(title="Power (W)", overlaying="y", side="right"),
            )
            st.plotly_chart(wfig, key="sweep_swap")

        st.caption("Teal markers fit an ISS rack, red ones do not. "
                   "The dotted white line is your current sidebar setting.")
        with st.expander("Show the numbers"):
            st.dataframe(df)