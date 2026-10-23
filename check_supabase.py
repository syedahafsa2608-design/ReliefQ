import streamlit as st
from supabase import create_client

st.title("ReliefQ — Supabase Connection Test")

try:
    url = st.secrets["supabase"]["url"].strip()
    key = st.secrets["supabase"]["key"].strip()

    st.write("URL format:", url.startswith("https://"))
    st.write("Project URL ends correctly:", url.endswith(".supabase.co"))

    client = create_client(url, key)

    result = client.table("resources").select("id").limit(1).execute()

    st.success("Connected! The resources table is reachable.")
    st.write("Test completed successfully.")

except Exception as e:
    st.error(f"Connection test failed: {e}")