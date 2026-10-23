import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from collections import defaultdict

import pandas as pd
import streamlit as st

# QAOA is kept separate from the classical greedy baseline.
try:
    from qaoa_optimizer import optimize_with_qaoa
    QAOA_IMPORT_ERROR = None
except Exception as exc:
    optimize_with_qaoa = None
    QAOA_IMPORT_ERROR = str(exc)


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="ReliefQ | Disaster Relief",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------- THEME ----------------
# The background image is embedded into the CSS from assets/relief_hero.jpg,
# so it appears on every page without relying on browser-relative file paths.
import base64
BACKGROUND_PATH = Path(__file__).parent / "assets" / "relief_hero.jpg"
BACKGROUND_CSS = ""
if BACKGROUND_PATH.exists():
    encoded_background = base64.b64encode(BACKGROUND_PATH.read_bytes()).decode("utf-8")
    BACKGROUND_CSS = f"background-image: linear-gradient(rgba(247,252,255,.72), rgba(247,252,255,.78)), url('data:image/jpeg;base64,{encoded_background}');"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: Inter, sans-serif; }}
.stApp {{
  color: #23415B;
  background-color: #F4FAFF;
  {BACKGROUND_CSS}
  background-size: cover;
  background-position: center center;
  background-attachment: fixed;
}}
[data-testid="stAppViewContainer"] {{ background: transparent; }}
[data-testid="stHeader"] {{ background: rgba(245,250,255,.48); }}
[data-testid="stSidebar"] {{ display: none; background: rgba(239,248,255,.90); border-right: 1px solid rgba(116,177,220,.28); }}
[data-testid="stSidebar"] * {{ color: #23415B; }}
[data-testid="stMainBlockContainer"] {{ background: rgba(255,255,255,.34); border-radius: 24px; }}
.hero {{
  background: linear-gradient(110deg, rgba(255,255,255,.88), rgba(227,244,255,.78));
  border: 1px solid rgba(255,255,255,.92); border-radius: 22px;
  box-shadow: 0 12px 32px rgba(73,139,184,.13); backdrop-filter: blur(12px);
  padding: 28px; margin-bottom: 22px;
}}
.hero h1 {{ font-size: 38px; margin: 0; color: #246DA5; }}
.hero p {{ font-size: 16px; color: #45677F; margin-bottom: 0; }}
.option-card {{ background: rgba(255,255,255,.78); border: 1px solid rgba(255,255,255,.96); border-radius: 22px; box-shadow: 0 10px 28px rgba(68,137,183,.13); backdrop-filter: blur(14px); padding: 22px; min-height: 205px; margin-bottom: 10px; }}
.option-icon {{ font-size: 38px; margin-bottom: 8px; }}
.option-card h3 {{ color: #246DA5; font-size: 20px; margin: 4px 0 8px 0; }}
.option-card p {{ color: #55758D; font-size: 14px; min-height: 52px; }}
.metric-card, .section-card {{
  background: rgba(255,255,255,.82); border: 1px solid rgba(255,255,255,.96); border-radius: 18px;
  box-shadow: 0 8px 24px rgba(68,137,183,.12); backdrop-filter: blur(12px);
  padding: 20px; margin-bottom: 14px;
}}
.metric-label {{ color: #55758D; font-size: 13px; font-weight: 600; }}
.metric-value {{ font-size: 30px; font-weight: 800; color: #246DA5; margin-top: 7px; }}
div.stButton > button[kind="primary"] {{
  background: linear-gradient(110deg, #3F9CD5, #72C4E9); color: white; border: 0; border-radius: 12px; font-weight: 600;
}}
div.stButton > button {{ border-radius: 12px; border-color: rgba(79,153,199,.4); }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{ background: rgba(255,255,255,.88); border-radius: 14px; }}
</style>
""", unsafe_allow_html=True)


# ---------------- SAMPLE DEMO DATA ----------------
SAMPLE_RESOURCES = [
    {"donor_name":"Demo Donor 1","donor_contact":"demo1@example.com","resource_name":"Drinking Water","category":"Water","quantity":100,"unit":"litres","location":"Demo Center A, Bengaluru","notes":"Synthetic demo record","created_at":datetime.now().isoformat()},
    {"donor_name":"Demo Donor 2","donor_contact":"demo2@example.com","resource_name":"Packaged Food","category":"Food","quantity":80,"unit":"packs","location":"Demo Center B, Bengaluru","notes":"Synthetic demo record","created_at":datetime.now().isoformat()},
    {"donor_name":"Demo Donor 3","donor_contact":"demo3@example.com","resource_name":"Blankets","category":"Clothing","quantity":40,"unit":"units","location":"Demo Center C, Bengaluru","notes":"Synthetic demo record","created_at":datetime.now().isoformat()},
    {"donor_name":"Demo Donor 4","donor_contact":"demo4@example.com","resource_name":"Hygiene Kits","category":"Hygiene","quantity":30,"unit":"kits","location":"Demo Center D, Bengaluru","notes":"Synthetic demo record","created_at":datetime.now().isoformat()},
]
SAMPLE_REQUESTS = [
    {"center_name":"Demo Relief Center A","contact_person":"Demo Coordinator A","contact_info":"demo-a@example.com","location":"Bengaluru","resource_name":"Drinking Water","category":"Water","quantity":60,"unit":"litres","urgency":"Critical","notes":"Synthetic demo request","status":"Pending","created_at":datetime.now().isoformat()},
    {"center_name":"Demo Relief Center B","contact_person":"Demo Coordinator B","contact_info":"demo-b@example.com","location":"Bengaluru","resource_name":"Packaged Food","category":"Food","quantity":50,"unit":"packs","urgency":"High","notes":"Synthetic demo request","status":"Pending","created_at":datetime.now().isoformat()},
    {"center_name":"Demo Relief Center C","contact_person":"Demo Coordinator C","contact_info":"demo-c@example.com","location":"Bengaluru","resource_name":"Blankets","category":"Clothing","quantity":30,"unit":"units","urgency":"Critical","notes":"Synthetic demo request","status":"Pending","created_at":datetime.now().isoformat()},
    {"center_name":"Demo Relief Center D","contact_person":"Demo Coordinator D","contact_info":"demo-d@example.com","location":"Bengaluru","resource_name":"Hygiene Kits","category":"Hygiene","quantity":20,"unit":"kits","urgency":"Medium","notes":"Synthetic demo request","status":"Pending","created_at":datetime.now().isoformat()},
]


# ---------------- SESSION DATA ----------------
if "resources" not in st.session_state:
    st.session_state.resources = [dict(x) for x in SAMPLE_RESOURCES]
if "aid_requests" not in st.session_state:
    st.session_state.aid_requests = [dict(x) for x in SAMPLE_REQUESTS]
if "relief_offers" not in st.session_state:
    st.session_state.relief_offers = []
if "reliefq_proposal" not in st.session_state:
    st.session_state.reliefq_proposal = None
if "qaoa_result" not in st.session_state:
    st.session_state.qaoa_result = None
if "welcome_complete" not in st.session_state:
    st.session_state.welcome_complete = False


def normalize(value):
    return str(value or "").strip().casefold()


def quantity_number(value):
    try:
        return max(0.0, float(value or 0))
    except (ValueError, TypeError):
        return 0.0


def hero(title, subtitle):
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def metric_card(label, value, description=""):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div style="color:#76645B;font-size:12px;">{description}</div></div>',
        unsafe_allow_html=True,
    )


def insert_row(table, data):
    if table == "resources":
        st.session_state.resources.append(dict(data))
    elif table == "aid_requests":
        st.session_state.aid_requests.append(dict(data))
    elif table == "relief_offers":
        st.session_state.relief_offers.append(dict(data))
    st.session_state.reliefq_proposal = None
    st.session_state.qaoa_result = None


def resource_inventory(resources):
    inventory = defaultdict(float)
    for item in resources:
        key = (normalize(item.get("resource_name")), normalize(item.get("unit", "units")))
        if key[0]:
            inventory[key] += quantity_number(item.get("quantity"))
    return inventory


def greedy_allocation(resources, requests):
    """Classical baseline only. Allocates partial quantities in urgency order."""
    priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    remaining = dict(resource_inventory(resources))
    rows = []
    eligible = []
    for idx, req in enumerate(requests):
        if normalize(req.get("status")) in {"fulfilled", "completed", "cancelled"}:
            continue
        qty = quantity_number(req.get("quantity"))
        name = normalize(req.get("resource_name"))
        unit = normalize(req.get("unit", "units"))
        if name and qty > 0:
            eligible.append((idx, req, qty, name, unit))
    eligible.sort(key=lambda x: (-priority.get(normalize(x[1].get("urgency")), 1), x[0]))
    for idx, req, qty, name, unit in eligible:
        key = (name, unit)
        available = remaining.get(key, 0.0)
        allocated = min(available, qty)
        remaining[key] = available - allocated
        rows.append({
            "Request Index": idx,
            "Relief Center": req.get("center_name", "Unknown center"),
            "Location": req.get("location", ""),
            "Resource": req.get("resource_name", ""),
            "Unit": req.get("unit", "units"),
            "Urgency": str(req.get("urgency", "Low")).title(),
            "Requested": qty,
            "Available Before Allocation": available,
            "Greedy Allocation": allocated,
            "Unfilled": qty - allocated,
        })
    return rows


# ---------------- HOME / OPTION CARDS ----------------
page_options = ["Home", "Donate Resources", "Request Aid", "Help Where It's Needed Most", "Resource Optimizer", "Demo Data Tools"]
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Home"
if "pending_page" in st.session_state:
    st.session_state.selected_page = st.session_state.pop("pending_page")
page = st.session_state.selected_page

if page == "Home":
    st.markdown("""
    <div class="hero" style="text-align:center;padding:34px 24px 30px;">
      <div style="font-size:14px;letter-spacing:2px;font-weight:700;color:#5794C7;margin-bottom:12px;">🧡 RELIEFQ · DISASTER RELIEF COORDINATION</div>
      <h1 style="font-size:44px;">Welcome to <span style="color:#3195DB;">ReliefQ</span></h1>
      <p style="font-size:18px;max-width:700px;margin:12px auto;">Together we can bring hope, resources and support<br>to communities in need.</p>
      <div style="display:inline-block;margin-top:12px;padding:10px 24px;border-radius:28px;background:rgba(194,232,255,.62);color:#1684C7;font-weight:600;">💙 Connect &nbsp; • &nbsp; Donate &nbsp; • &nbsp; Rebuild</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## Choose an Option")
    st.caption("How would you like to help or get help today?")
    cards = [
        ("📦", "Donate Resources", "Register available supplies and help relief teams coordinate distribution.", "Register Donation"),
        ("📋", "Request Aid", "Tell relief coordinators what your center needs most.", "Submit Request"),
        ("📍", "Help Where It's Needed Most", "Find unmet needs and offer supplies to active requests.", "View Needs"),
        ("🧬", "Resource Optimizer", "Use QAOA and a classical baseline to explore allocation solutions.", "Run Optimization"),
        ("🗃️", "Demo Data Tools", "Export current demo data or reset the sample records.", "Manage Data"),
    ]
    for row_items, count in [([0,1,2],3), ([3,4],2)]:
        cols = st.columns(count)
        for col, card_idx in zip(cols, row_items):
            icon, title, desc, cta = cards[card_idx]
            with col:
                st.markdown(f'<div class="option-card"><div class="option-icon">{icon}</div><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
                if st.button(f"{cta}  →", key=f"home_{card_idx}", type="primary", use_container_width=True):
                    st.session_state.selected_page = title
                    st.rerun()
    st.markdown("<div style='text-align:center;color:#6C9DC4;padding:18px;'>────── &nbsp; ReliefQ &nbsp; • &nbsp; Compassion &nbsp; • &nbsp; Action &nbsp; • &nbsp; A Safer Tomorrow &nbsp; ──────</div>", unsafe_allow_html=True)
    st.stop()

if st.button("← Back to Home", key="back_home"):
    st.session_state.selected_page = "Home"
    st.rerun()

# ---------------- DONATE RESOURCES ----------------
elif page == "Donate Resources":
    resources = st.session_state.resources
    hero("Donate Resources", "Register essential supplies to help relief teams coordinate distribution.")
    with st.form("donation_form", clear_on_submit=True):
        st.markdown("### Donation Details")
        donor_name = st.text_input("Donor / Organization Name")
        donor_contact = st.text_input("Contact Information")
        resource_choice = st.selectbox("Resource", ["Rice","Packaged Food","Drinking Water","Blankets","Clothing","Hygiene Kits","First Aid Kits","Medicines","Baby Supplies","Other"])
        custom_resource = st.text_input("Specify Resource") if resource_choice == "Other" else ""
        category = st.selectbox("Category", ["Food","Water","Shelter","Hygiene","Medical","Clothing","Other"])
        quantity = st.number_input("Quantity", min_value=1, max_value=1000000, value=10, step=1)
        unit = st.selectbox("Unit", ["units","kg","litres","boxes","packs","kits"])
        location = st.text_input("Storage / Collection Location")
        notes = st.text_area("Additional Details (optional)")
        submitted = st.form_submit_button("Register Donation", type="primary", use_container_width=True)
    if submitted:
        final_resource = custom_resource.strip() if resource_choice == "Other" else resource_choice
        if not donor_name.strip() or not location.strip():
            st.error("Please enter the donor name and location.")
        elif not final_resource:
            st.error("Please specify the resource.")
        else:
            insert_row("resources", {"donor_name":donor_name.strip(),"donor_contact":donor_contact.strip(),"resource_name":final_resource,"category":category,"quantity":int(quantity),"unit":unit,"location":location.strip(),"notes":notes.strip(),"created_at":datetime.now().isoformat()})
            st.success("Donation registered in this local demo session.")
            st.rerun()
    st.markdown("### Registered Donations")
    if resources:
        df = pd.DataFrame(resources)
        cols = [c for c in ["donor_name","resource_name","category","quantity","unit","location"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
    else: st.info("Donations will appear here after registration.")

# ---------------- REQUEST AID ----------------
elif page == "Request Aid":
    requests = st.session_state.aid_requests
    hero("Request Aid", "Tell relief coordinators what your center needs most.")
    with st.form("aid_request_form", clear_on_submit=True):
        st.markdown("### Relief Center Details")
        center_name = st.text_input("Relief Center / Organization Name")
        contact_person = st.text_input("Contact Person")
        contact_info = st.text_input("Phone or Email")
        location = st.text_input("Disaster-Affected Location")
        st.markdown("### Resource Requirements")
        resource_choice = st.selectbox("Required Resource", ["Rice","Packaged Food","Drinking Water","Blankets","Clothing","Hygiene Kits","First Aid Kits","Medicines","Baby Supplies","Other"])
        custom_resource = st.text_input("Specify Required Resource") if resource_choice == "Other" else ""
        category = st.selectbox("Category", ["Food","Water","Shelter","Hygiene","Medical","Clothing","Other"])
        quantity = st.number_input("Quantity Required", min_value=1, max_value=1000000, value=10, step=1)
        unit = st.selectbox("Unit", ["units","kg","litres","boxes","packs","kits"])
        urgency = st.select_slider("Urgency Level", options=["Low","Medium","High","Critical"], value="Medium")
        notes = st.text_area("Additional Needs / Situation")
        submitted = st.form_submit_button("Submit Aid Request", type="primary", use_container_width=True)
    if submitted:
        final_resource = custom_resource.strip() if resource_choice == "Other" else resource_choice
        if not center_name.strip() or not location.strip():
            st.error("Please enter the center name and location.")
        elif not final_resource:
            st.error("Please specify the required resource.")
        else:
            insert_row("aid_requests", {"center_name":center_name.strip(),"contact_person":contact_person.strip(),"contact_info":contact_info.strip(),"location":location.strip(),"resource_name":final_resource,"category":category,"quantity":int(quantity),"unit":unit,"urgency":urgency,"notes":notes.strip(),"status":"Pending","created_at":datetime.now().isoformat()})
            st.success("Aid request registered in this local demo session.")
            st.rerun()
    st.markdown("### Registered Aid Requests")
    if requests:
        df = pd.DataFrame(requests)
        cols = [c for c in ["center_name","resource_name","quantity","unit","urgency","status","location"] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True, hide_index=True)
    else: st.info("No aid requests registered yet.")

# ---------------- HELP WHERE IT'S NEEDED MOST ----------------
elif page == "Help Where It's Needed Most":
    resources = st.session_state.resources
    requests = st.session_state.aid_requests
    hero("Help Where It's Needed Most", "Find unmet needs and offer supplies to active requests.")
    active = [(i, x) for i, x in enumerate(requests) if normalize(x.get("status")) not in {"fulfilled","completed","cancelled"}]
    if not active: st.info("There are no active requests.")
    for idx, item in active:
        name, unit = normalize(item.get("resource_name")), normalize(item.get("unit","units"))
        available = sum(quantity_number(r.get("quantity")) for r in resources if normalize(r.get("resource_name")) == name and normalize(r.get("unit","units")) == unit)
        needed = quantity_number(item.get("quantity"))
        with st.container(border=True):
            left, right = st.columns([3,1])
            with left:
                st.markdown(f"#### {item.get('center_name','Relief Center')}")
                st.write(f"**Needs:** {item.get('resource_name')} — {needed:g} {item.get('unit','units')}")
                st.write(f"**Location:** {item.get('location','Not specified')}")
                st.write(f"**Urgency:** {item.get('urgency','Medium')} · **Status:** {item.get('status','Pending')}")
            with right:
                st.metric("Matching stock", f"{available:g}")
                st.metric("Potential shortfall", f"{max(0, needed-available):g}")
            with st.expander("Offer resources to this request"):
                with st.form(f"offer_form_{idx}"):
                    offer_name = st.text_input("Your name / organization", key=f"offer_name_{idx}")
                    offer_contact = st.text_input("Contact information", key=f"offer_contact_{idx}")
                    offer_quantity = st.number_input("Quantity you can offer", min_value=1, max_value=1000000, value=1, key=f"offer_qty_{idx}")
                    offer_unit = st.text_input("Unit", value=str(item.get("unit","units")), key=f"offer_unit_{idx}")
                    offer_submitted = st.form_submit_button("Record Local Offer", type="primary")
                if offer_submitted:
                    if not offer_name.strip() or not offer_unit.strip():
                        st.error("Enter your name and offer unit.")
                    else:
                        insert_row("relief_offers", {"request_index":idx,"center_name":item.get("center_name",""),"donor_name":offer_name.strip(),"donor_contact":offer_contact.strip(),"resource_name":item.get("resource_name",""),"quantity":int(offer_quantity),"unit":offer_unit.strip(),"status":"Pending","created_at":datetime.now().isoformat()})
                        st.success("Offer recorded in this local session.")
                        st.rerun()
    st.markdown("### Recorded Offers")
    if st.session_state.relief_offers:
        st.dataframe(pd.DataFrame(st.session_state.relief_offers), use_container_width=True, hide_index=True)
    else: st.info("No offers recorded yet.")
    st.caption("Offers do not automatically add stock or fulfill requests.")

# ---------------- RESOURCE OPTIMIZER ----------------
elif page == "Resource Optimizer":
    resources = st.session_state.resources
    requests = st.session_state.aid_requests
    hero("Resource Optimizer", "Compare a QAOA request-selection prototype with a classical greedy allocation baseline.")
    st.warning("Planning/demo only. Results are suggestions, not verified needs or delivery instructions. Demo data is synthetic; no stock is reserved or changed.")

    if QAOA_IMPORT_ERROR:
        st.error("QAOA module could not be imported. Check qaoa_optimizer.py and your installed Qiskit packages.")
        st.code(QAOA_IMPORT_ERROR)

    st.markdown("### 1. QAOA — Whole-request selection")
    st.write("QAOA selects eligible whole requests that fit the aggregated matching supply. It does not split requests or plan delivery routes.")
    if st.button("Run QAOA Optimization", type="primary", disabled=(optimize_with_qaoa is None)):
        try:
            with st.spinner("Running QAOA on the local simulator..."):
                result = optimize_with_qaoa(resources=resources, requests=requests)
            st.session_state.qaoa_result = result
        except Exception as exc:
            st.error(f"QAOA failed: {exc}")
            st.session_state.qaoa_result = None

    qres = st.session_state.qaoa_result
    if qres:
        m1, m2 = st.columns(2)
        with m1: metric_card("QAOA Objective Score", f"{qres.get('objective', 0):.3f}", "Prototype objective; not a real-world impact score")
        with m2: metric_card("Runtime", f"{qres.get('runtime_seconds', 0):.2f}s", "Local simulator runtime")
        st.info(qres.get("message", "QAOA run completed."))
        if qres.get("selected"):
            st.dataframe(pd.DataFrame(qres["selected"]), use_container_width=True, hide_index=True)
        else:
            st.warning("QAOA did not select any requests. See its message above.")

    st.divider()
    st.markdown("### 2. Classical Greedy — Partial-quantity allocation")
    st.write("The baseline processes requests in urgency order and allocates as much matching stock as available, including partial quantities.")
    if st.button("Generate Greedy Allocation", type="primary"):
        st.session_state.greedy_result = greedy_allocation(resources, requests)

    gres = st.session_state.get("greedy_result")
    if gres is not None:
        if gres:
            gdf = pd.DataFrame(gres)
            st.dataframe(gdf.drop(columns=["Request Index"], errors="ignore"), use_container_width=True, hide_index=True)
            a, b, c = st.columns(3)
            with a: metric_card("Requested", f"{sum(r['Requested'] for r in gres):,.0f}")
            with b: metric_card("Greedy Allocation", f"{sum(r['Greedy Allocation'] for r in gres):,.0f}")
            with c: metric_card("Unfilled", f"{sum(r['Unfilled'] for r in gres):,.0f}")
            st.download_button("Download Greedy Allocation CSV", data=gdf.drop(columns=["Request Index"], errors="ignore").to_csv(index=False).encode("utf-8"), file_name="reliefq_greedy_allocation.csv", mime="text/csv")
        else:
            st.info("No eligible requests are available for the greedy allocation.")

    st.caption("Do not interpret QAOA objective scores and greedy allocated quantities as directly comparable metrics: they optimize different formulations.")


# ---------------- DEMO DATA TOOLS PAGE ----------------
elif page == "Demo Data Tools":
    hero("Demo Data Tools", "Export your current demo entries or reset to the sample records.")
    export_data = {"resources": st.session_state.resources, "aid_requests": st.session_state.aid_requests, "relief_offers": st.session_state.relief_offers}
    st.download_button("Download All Demo Data (JSON)", data=json.dumps(export_data, indent=2, default=str), file_name="reliefq_demo_data.json", mime="application/json", use_container_width=True)
    if st.button("Reset Demo Data", type="primary", use_container_width=True):
        st.session_state.resources = [dict(x) for x in SAMPLE_RESOURCES]
        st.session_state.aid_requests = [dict(x) for x in SAMPLE_REQUESTS]
        st.session_state.relief_offers = []
        st.session_state.reliefq_proposal = None
        st.session_state.qaoa_result = None
        st.session_state.pop("greedy_result", None)
        st.success("Demo data has been reset.")
        st.rerun()