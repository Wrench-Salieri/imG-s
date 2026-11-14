from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from mri.parameters import (
    GROUPS,
    ISS_RACK_MAX_VOLUME_M3,
    ISS_RACK_MAX_WEIGHT_KG,
    PARAMS,
    PARAMS_BY_NAME,
    parameter_table,
)
from mri.phantom import head_phantom
from mri.simulator import SpaceMRISimulator
from mri.telemetry import get_sams_telemetry
from components.theme import TEAL, AMBER, RED, MUTED, TEXT, style_figure

APP_DIR = Path(__file__).parent
im = Image.open(APP_DIR / "components" / "images" / "favicon.png")

st.set_page_config(page_title="Space MRI Twin", page_icon=im, layout="wide")

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


def clamp_to_range(name, value):
    p = PARAMS_BY_NAME[name]
    return float(min(max(value, p.minimum), p.maximum))


def try_call(func, *args):
    try:
        return func(*args)
    except NotImplementedError as err:
        st.info(f"Waiting for the Physics & DSP team. {err}")
        return None


@st.cache_data
def get_phantom():
    return head_phantom(128, 208.0)


@st.cache_data(show_spinner=False)
def run_simulation(params, seed):
    np.random.seed(seed)        
    return SpaceMRISimulator(get_phantom()).simulate(**params)


@st.cache_data(show_spinner=False)
def run_sweep(params, name, values, seed):
    spec = PARAMS_BY_NAME[name]
    rows = []
    for value in values:
        trial = {**params, name: int(value) if spec.is_int else float(value)}
        _, metrics = run_simulation(trial, seed)
        rows.append({"value": float(value), **metrics})
    return rows


def sweep_values(spec, points):
    if spec.is_int:
        return tuple(range(spec.minimum, spec.maximum + 1))
    return tuple(float(v) for v in np.linspace(spec.minimum, spec.maximum, points))


def show_results(result, prefix):
    simulated, metrics = result
    ideal = get_phantom()

    a, b, c = st.columns(3)
    a.metric("SSIM", f"{metrics['SSIM']:.3f}",
             help="Structural similarity to the ideal image (1 is perfect).")
    b.metric("PSNR", f"{metrics['PSNR_dB']:.1f} dB",
             help="Peak signal-to-noise ratio against the ideal image.")
    c.metric("ISS rack", "Compatible" if metrics["ISS_Rack_Compatible"] else "Does not fit")

    volume, weight = metrics["Volume_m3"], metrics["Weight_kg"]
    d, e, f = st.columns(3)
    d.metric("Scanner volume", f"{volume:.3f} m³",
             delta=f"{volume - ISS_RACK_MAX_VOLUME_M3:+.3f} m³ vs rack limit",
             delta_color="inverse")
    e.metric("Estimated weight", f"{weight:.0f} kg",
             delta=f"{weight - ISS_RACK_MAX_WEIGHT_KG:+.0f} kg vs rack limit",
             delta_color="inverse")
    f.metric("Power", f"{metrics['Power_W']:,.0f} W")

    if metrics["ISS_Rack_Compatible"]:
        st.success(f"This scanner fits an ISS rack (volume up to {ISS_RACK_MAX_VOLUME_M3} m³ "
                   f"and weight up to {ISS_RACK_MAX_WEIGHT_KG:.0f} kg).")
    else:
        st.error("This scanner does not fit an ISS rack. Reduce the bore, the length "
                 "or the field strength.")

    if simulated.shape != ideal.shape:
        st.warning("The simulated image has a different size than the phantom, "
                   "so the comparison images are skipped.")
        st.plotly_chart(image_figure(simulated), key=f"{prefix}_sim_only")
        return

    left, middle, right = st.columns(3)
    left.markdown("**Ideal phantom**")
    left.plotly_chart(image_figure(ideal), key=f"{prefix}_ideal")
    middle.markdown("**Simulated scan**")
    middle.plotly_chart(image_figure(simulated), key=f"{prefix}_simulated")
    right.markdown("**Difference**")
    diff = np.abs(ideal - simulated)
    right.plotly_chart(image_figure(diff, "magma", 0.0, max(float(diff.max()), 0.05)),
                       key=f"{prefix}_diff")

st.sidebar.header("Scanner settings")
params = {}
for group, names in GROUPS.items():
    st.sidebar.subheader(group)
    for name in names:
        p = PARAMS_BY_NAME[name]
        label = f"{p.label} ({p.unit})" if p.unit else p.label
        params[name] = st.sidebar.slider(
            label, p.minimum, p.maximum, p.default, p.step, help=p.help, key=name
        )

with st.sidebar.expander("Advanced"):
    seed = st.number_input(
        "Noise seed", min_value=0, max_value=9999, value=42, step=1,
        help="Keeps the random noise identical until a setting changes.",
    )
seed = int(seed)

st.title("imG's MRI Designer (name subject to change)")
st.caption("A portable MRI designer for the ISS.")

tab_design, tab_mission, tab_sweep = st.tabs(
    ["Engineering Design Mode", "Mission Control Mode", "Parameter sweep"]
)

with tab_design:
    st.subheader("Engineering Design Mode")
    st.caption("Move the sliders in the sidebar to design the scanner and see the result.")
    result = try_call(run_simulation, params, seed)
    if result is not None:
        show_results(result, "design")
    with st.expander("What do the parameters mean?"):
        st.dataframe(pd.DataFrame(parameter_table()))

with tab_mission:
    st.subheader("Mission Control Mode")
    st.caption(
        "Reads the latest ISS vibration data from NASA (SAMS-II) and shows the image as it "
        "would look right now. All other settings come from the sidebar."
    )

    if st.button("Fetch latest NASA telemetry"):
        try:
            st.session_state["telemetry"] = get_sams_telemetry()
            st.session_state["telemetry_error"] = None
        except NotImplementedError as err:
            st.session_state["telemetry"] = None
            st.session_state["telemetry_error"] = str(err)

    telemetry = st.session_state.get("telemetry")
    telemetry_error = st.session_state.get("telemetry_error")

    if telemetry_error:
        st.info(f"Waiting for the Physics & DSP team. {telemetry_error}")
    elif telemetry is None:
        st.caption("Press the button to load live data.")
    else:
        live_g = clamp_to_range("g_level_mg", telemetry["g_level_mg"])
        live_f = clamp_to_range("vibration_freq_hz", telemetry["vibration_freq_hz"])
        t1, t2, t3 = st.columns(3)
        t1.metric("Vibration (SAMS-II)", f"{live_g:.1f} milli-g")
        t2.metric("Frequency", f"{live_f:.1f} Hz")
        t3.metric("Recorded (UTC)", str(telemetry["timestamp_utc"]))
        st.caption(f"Source: {telemetry['source']}")

        live_params = {**params, "g_level_mg": live_g, "vibration_freq_hz": live_f}
        live_result = try_call(run_simulation, live_params, seed)
        if live_result is not None:
            show_results(live_result, "mission")

with tab_sweep:
    st.subheader("Parameter sweep")
    st.caption("Change one setting across its whole range, keep the others from the sidebar, "
               "and see how quality, size, weight and power respond.")

    sweep_name = st.selectbox(
        "Setting to sweep", [p.name for p in PARAMS],
        format_func=lambda n: PARAMS_BY_NAME[n].label,
    )
    points = st.slider("Number of points", 5, 25, 11)
    spec = PARAMS_BY_NAME[sweep_name]
    values = sweep_values(spec, points)
    axis_title = f"{spec.label} ({spec.unit})" if spec.unit else spec.label

    rows = try_call(run_sweep, params, sweep_name, values, seed)
    if rows is not None:
        df = pd.DataFrame(rows)
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