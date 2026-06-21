import streamlit as st
import requests
import os

st.set_page_config(page_title="Multi-Tenant Chatbot", page_icon="🤖")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Sidebar for tenant authentication
with st.sidebar:
    st.title("Tenant Configuration")
    tenant_id = st.text_input("Enter Tenant ID", type="password")
    if tenant_id:
        if "tenant_id" not in st.session_state or st.session_state["tenant_id"] != tenant_id:
            st.session_state["tenant_id"] = tenant_id
            if "messages" in st.session_state:
                del st.session_state["messages"]
        st.success(f"Authenticated as Tenant: {tenant_id}")
    else:
        st.warning("Please enter your Tenant ID to proceed.")

# Chat Interface
st.title("Gemini Multi-Tenant Chatbot")

if "tenant_id" in st.session_state and st.session_state["tenant_id"]:
    headers = {"X-Tenant-ID": st.session_state["tenant_id"]}
    
    # Initialize chat history if empty in session state, but fetch from backend first
    if "messages" not in st.session_state:
        try:
            response = requests.get(f"{BACKEND_URL}/history", headers=headers)
            if response.status_code == 200:
                st.session_state["messages"] = response.json()
            elif response.status_code == 401:
                st.error("Invalid Tenant ID. Please check the sidebar.")
                st.stop()
            else:
                st.error("Failed to load chat history.")
                st.session_state["messages"] = []
        except Exception as e:
            st.error(f"Error connecting to backend: {e}")
            st.session_state["messages"] = []
            st.stop()

    # Display chat messages from history on app rerun
    for message in st.session_state["messages"]:
        role = "user" if message["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # Send to backend
        try:
            with st.spinner("Thinking..."):
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    headers=headers,
                    json={"message": prompt}
                )
            
            if response.status_code == 200:
                response_text = response.json().get("response", "")
                # Display assistant response in chat message container
                with st.chat_message("assistant"):
                    st.markdown(response_text)
                # Add assistant response to chat history
                st.session_state["messages"].append({"role": "model", "content": response_text})
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error connecting to backend: {e}")
else:
    st.info("Please enter a Tenant ID in the sidebar to start chatting.")
