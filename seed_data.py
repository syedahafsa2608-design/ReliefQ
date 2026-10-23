import pandas as pd
import streamlit as st
from supabase import create_client


# Synthetic demo resources for resources_v2
resources = [
    {
        "donor_name": "Demo Donor 1",
        "donor_contact": "demo1@example.com",
        "resource_name": "Water",
        "category": "Water",
        "quantity": 100,
        "unit": "litres",
        "location": "Demo Center A, Bengaluru",
        "notes": "Synthetic demo record",
    },
    {
        "donor_name": "Demo Donor 2",
        "donor_contact": "demo2@example.com",
        "resource_name": "Food Packets",
        "category": "Food",
        "quantity": 80,
        "unit": "packets",
        "location": "Demo Center B, Bengaluru",
        "notes": "Synthetic demo record",
    },
    {
        "donor_name": "Demo Donor 3",
        "donor_contact": "demo3@example.com",
        "resource_name": "Blankets",
        "category": "Clothing",
        "quantity": 40,
        "unit": "pieces",
        "location": "Demo Center C, Bengaluru",
        "notes": "Synthetic demo record",
    },
    {
        "donor_name": "Demo Donor 4",
        "donor_contact": "demo4@example.com",
        "resource_name": "Hygiene Kits",
        "category": "Hygiene",
        "quantity": 30,
        "unit": "kits",
        "location": "Demo Center D, Bengaluru",
        "notes": "Synthetic demo record",
    },
]

# Synthetic demo aid requests for aid_requests_v2
requests = [
    {
        "center_name": "Demo Relief Center A",
        "contact_person": "Demo Coordinator A",
        "contact_info": "demo-a@example.com",
        "location": "Bengaluru",
        "resource_name": "Water",
        "category": "Water",
        "quantity": 60,
        "unit": "litres",
        "urgency": "Critical",
        "notes": "Synthetic demo request",
        "status": "Pending",
    },
    {
        "center_name": "Demo Relief Center B",
        "contact_person": "Demo Coordinator B",
        "contact_info": "demo-b@example.com",
        "location": "Bengaluru",
        "resource_name": "Food Packets",
        "category": "Food",
        "quantity": 50,
        "unit": "packets",
        "urgency": "High",
        "notes": "Synthetic demo request",
        "status": "Pending",
    },
    {
        "center_name": "Demo Relief Center C",
        "contact_person": "Demo Coordinator C",
        "contact_info": "demo-c@example.com",
        "location": "Bengaluru",
        "resource_name": "Blankets",
        "category": "Clothing",
        "quantity": 30,
        "unit": "pieces",
        "urgency": "Critical",
        "notes": "Synthetic demo request",
        "status": "Pending",
    },
    {
        "center_name": "Demo Relief Center D",
        "contact_person": "Demo Coordinator D",
        "contact_info": "demo-d@example.com",
        "location": "Bengaluru",
        "resource_name": "Hygiene Kits",
        "quantity": 20,
        "unit": "kits",
        "urgency": "Medium",
        "notes": "Synthetic demo request",
        "status": "Pending",
    },
]


def main():
    st.set_page_config(page_title="ReliefQ Demo Data", page_icon="🆘")
    st.title("ReliefQ — Load Demo Data")
    st.caption("Insert clearly labelled synthetic records into your Supabase demo tables.")

    st.warning(
        "These are synthetic records for testing only. "
        "Load them only once to avoid duplicates."
    )

    if st.button("Load Demo Data", type="primary"):
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            client = create_client(url, key)

            with st.spinner("Loading demo resources..."):
                resource_result = (
                    client.table("resources_v2").insert(resources).execute()
                )

            with st.spinner("Loading demo aid requests..."):
                request_result = (
                    client.table("aid_requests_v2").insert(requests).execute()
                )

            st.success("Demo data loaded successfully!")

            st.subheader("Resources added")
            st.dataframe(pd.DataFrame(resources), use_container_width=True)

            st.subheader("Aid requests added")
            st.dataframe(pd.DataFrame(requests), use_container_width=True)

        except KeyError as e:
            st.error(
                "Supabase configuration is missing. Check that "
                "[supabase] contains both url and key in .streamlit/secrets.toml."
            )
        except Exception as e:
            st.error(f"Could not load demo data: {e}")


if __name__ == "__main__":
    main()