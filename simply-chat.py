import os
import streamlit as st
from dataclasses import asdict
from streamlit_keycloak import login
import streamlit as st
import requests
from dataclasses import dataclass
from PIL import Image

st.set_page_config(
    page_title="AIGW Simply Chat",
    layout="centered"
)

# Authentication function
def authenticate():
    st.markdown("<h2 style='text-align: center; font-size: 28px; color: #4CAF50;'>Welcome to Corporate AI Services {TAG} </h2>", unsafe_allow_html=True)
    keycloak = login(
        url="https://idp.example.com/",
        realm="corp-ai",
        client_id=f"{AI_MODEL}",
    )

    # Use custom CSS for larger font size
    st.markdown(
    f"""
    <style>
    .custom-header {{
        font-size: 20px;  /* Slightly larger size */
        color: #333;  /* Optional: Change color */
    }}
    </style>
    """,
    unsafe_allow_html=True
    )


    if keycloak.authenticated:
        st.header(f"Welcome {keycloak.user_info['preferred_username']}")
        st.markdown(f"<div class='custom-header'>Status: {keycloak.user_info['groups']}</div>", unsafe_allow_html=True)

        return keycloak
    else:
        st.error("Authentication failed. Please try again.")
        return None

# Helper function to make requests with Bearer token and user group header
def request_with_token(method, url, token, user_group=None, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    if user_group:
        headers["X-User-Role-Token"] = user_group  # Add the user group header
    kwargs["headers"] = headers
    response = requests.request(method, url, **kwargs)
    return response

# Main application function
def main(keycloak):
    # Define your constants
    USER = "user"
    ASSISTANT = "ai"
    MESSAGES = "messages"
    API_URL = os.getenv("AIGW_API_URL")
    AI_MODEL = os.getenv("AI_MODEL")
    AI_TEMP = float(os.getenv("AI_TEMP", 0.7))
    OAUTH_CLIENTID = os.getenv("OAUTH_CLIENTID")
    TAG  = os.getenv("TAG")

    token = keycloak.access_token

    # JSON template for API request
    json_template = {
        "models": f"{AI_MODEL}",
        "messages": [],
        "temperature": AI_TEMP
    }

    # Load avatar images from local files
    USER_AVATAR = Image.open("./user.png")  # Replace with the actual path to the user avatar image
    ASSISTANT_AVATAR = Image.open("./ai.png")  # Replace with the actual path to the assistant avatar image

    # Hide Streamlit UI elements
    hide_streamlit_style = """
                <style>
                div[data-testid="stToolbar"], div[data-testid="stDecoration"], div[data-testid="stStatusWidget"],
                #MainMenu, header, footer {
                    visibility: hidden;
                    height: 0%;
                    position: fixed;
                }
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    @dataclass
    class Message:
        role: str
        content: str

    # Initialize session state messages
    if MESSAGES not in st.session_state:
        st.session_state[MESSAGES] = [Message(
            role=ASSISTANT,
            content="Services are governed under Corporate AI Governance. Use it responsibly. How can I help?"
        )]

    # Display existing messages
    for msg in st.session_state[MESSAGES]:
        avatar = ASSISTANT_AVATAR if msg.role == ASSISTANT else USER_AVATAR
        st.chat_message(msg.role, avatar=avatar).write(msg.content)

    # Take user input
    prompt = st.text_area("Enter a prompt here:", key="input_field", max_chars=300, height=180)

    # If user submits input
    if st.button("Submit"):
        if prompt:
            # Update messages list in JSON template with user input
            json_template["messages"].append({
                "role": USER,
                "content": prompt
            })

            # Append user message to session state
            st.session_state[MESSAGES].append(Message(role=USER, content=prompt))
            st.chat_message(USER, avatar=USER_AVATAR).write(prompt)

            # Add spinner while waiting for response
            with st.spinner("Waiting for response..."):
                try:
                    headers = {"Authorization": f"Bearer {token}"}
                    # Send POST request to API endpoint with updated JSON template
                    user_group = keycloak.user_info.get("groups", "admin-role")  # Adjust key as needed

                    response = request_with_token("POST",API_URL,token,user_group=user_group, json=json_template, verify=False)

                    # Display response from API
                    if response.status_code == 200:
                        response_data = response.json()
                        model_name = response_data.get("model", "Unknown Model")

                        # Extract and display assistant's response from choices
                        if "choices" in response_data:
                            for choice in response_data["choices"]:
                                if "message" in choice and "content" in choice["message"]:
                                    assistant_response = choice["message"]["content"]
                                    st.session_state[MESSAGES].append(Message(role=ASSISTANT, content=assistant_response))
                                    escaped_response = assistant_response.replace("*", "\*")
                                    st.chat_message(ASSISTANT, avatar=ASSISTANT_AVATAR).markdown(escaped_response)

                                    #st.chat_message(ASSISTANT, avatar=ASSISTANT_AVATAR).write(assistant_response)
                                    st.markdown(f"<div style='text-align: right; font-style: italic; font-size: 12px;'>LLM Model Used: {model_name}</div>", unsafe_allow_html=True)
                                else:
                                    st.warning("Invalid format in API response: 'message' or 'content' not found.")
                        else:
                            st.warning("Invalid format in API response: 'choices' not found.")
                    else:
                        st.error(f"Unfortunately, I don't quite like your question. Please try again. My mood: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error sending request: {e}")

# Run the application
keycloak = authenticate()
if keycloak:
    main(keycloak)
