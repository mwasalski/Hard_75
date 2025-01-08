import streamlit as st
import requests
from datetime import datetime
import io
from PIL import Image
import base64
import os

# Initialize session state for tracking
if 'days_completed' not in st.session_state:
    st.session_state.days_completed = 0
if 'current_streak' not in st.session_state:
    st.session_state.current_streak = 0
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'token' not in st.session_state:
    st.session_state.token = None
if 'should_reset' not in st.session_state:
    st.session_state.should_reset = False

API_URL = "http://localhost:8000"

def load_image(image_data):
    if image_data:
        return Image.open(io.BytesIO(base64.b64decode(image_data)))
    return None

def login(username, password):
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={
                "username": username,
                "password": password
            }
        )
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.token = token_data["access_token"]
            st.session_state.logged_in = True
            return True
        return False
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return False

def register(username, password):
    try:
        response = requests.post(
            f"{API_URL}/register",
            json={
                "username": username,
                "password": password
            }
        )
        if response.status_code == 200:
            st.success("Registration successful! Please log in.")
            return True
        else:
            error_detail = "Registration failed"
            try:
                response_json = response.json()
                if isinstance(response_json, dict):
                    if "detail" in response_json:
                        if isinstance(response_json["detail"], dict):
                            error_detail = response_json["detail"].get("message", error_detail)
                        else:
                            error_detail = response_json["detail"]
            except:
                pass
            st.error(error_detail)
            return False
    except Exception as e:
        st.error(f"Registration failed: {str(e)}")
        return False

st.title("75 Hard Challenge Tracker")

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.header("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            if login(login_username, login_password):
                st.success("Logged in successfully!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        st.header("Register")
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        if st.button("Register", key="register_button"):
            register(reg_username, reg_password)

else:
    # Sidebar for user actions
    with st.sidebar:
        # Logout button at the top
        if st.button("Logout", key="sidebar_logout"):  # Changed key name
            st.session_state.logged_in = False
            st.session_state.token = None
            st.experimental_rerun()

        st.header("Daily Tasks")
        
        # Task checkboxes using session state
        workout1 = st.checkbox("First Workout (45 min)", key='workout1')
        workout2 = st.checkbox("Second Workout (45 min, outdoors)", key='workout2')
        diet = st.checkbox("Follow Diet Plan", key='diet')
        water = st.checkbox("Drink 1 Gallon Water", key='water')
        reading = st.checkbox("Read 10 Pages", key='reading')
        
        # Add image upload
        uploaded_file = st.file_uploader("Upload Progress Picture", type=['png', 'jpg', 'jpeg'], key='picture_upload')
        if uploaded_file is not None:
            picture = True
            img_bytes = uploaded_file.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
        else:
            picture = False
            img_base64 = None

        if st.button("Submit Daily Progress", key="submit_button"):
            data = {
                "workout_1": workout1,
                "workout_2": workout2,
                "diet": diet,
                "water": water,
                "reading": reading,
                "progress_picture": picture,
                "image_data": img_base64 if picture else None
            }
            
            try:
                response = requests.post(
                    f"{API_URL}/day/complete",
                    json=data,
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.days_completed = result.get('total_days', 0)
                    st.session_state.current_streak = result.get('current_streak', 0)
                    st.success(result.get('message', "Progress saved!"))
                    if all(data.values()):
                        st.balloons()
                    st.session_state.should_reset = True
                    st.experimental_rerun()
                elif response.status_code == 400:
                    result = response.json()
                    st.warning(f"{result['detail']['message']} Next available submission: {result['detail']['next_available']}")
                    st.session_state.days_completed = result['detail']['total_days']
                    st.session_state.current_streak = result['detail']['current_streak']
                else:
                    st.error(f"Failed to save progress: {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                st.error(f"Could not connect to the server: {str(e)}")

    # Main content area
    col1, col2 = st.columns(2)

    with col1:
        st.header("Your Progress")
        st.metric(label="Days Completed", value=f"{st.session_state.days_completed}/75")
        st.metric(label="Current Streak", value=f"{st.session_state.current_streak} days")
    
    with col2:
        st.header("Today's Status")
        tasks_completed = sum([workout1, workout2, diet, water, reading, picture])
        progress = tasks_completed / 6
        st.progress(progress)
        st.write(f"Tasks Completed Today: {tasks_completed}/6")

    # Progress Pictures Comparison
    st.header("Progress Pictures")
    pic_col1, pic_col2 = st.columns(2)

    try:
        response = requests.get(
            f"{API_URL}/progress-pictures",
            headers={"Authorization": f"Bearer {st.session_state.token}"}
        )
        if response.status_code == 200:
            pictures = response.json()
            with pic_col1:
                if pictures.get('first_picture'):
                    st.subheader(f"Day 1 - {pictures['first_date']}")
                    first_image = load_image(pictures['first_picture'])
                    if first_image:
                        st.image(first_image, use_column_width=True)
                else:
                    st.info("No starting picture available")

            with pic_col2:
                if pictures.get('latest_picture'):
                    st.subheader(f"Day {pictures['latest_day']} - {pictures['latest_date']}")
                    latest_image = load_image(pictures['latest_picture'])
                    if latest_image:
                        st.image(latest_image, use_column_width=True)
                else:
                    st.info("No recent picture available")
    except Exception as e:
        st.error(f"Failed to load progress pictures: {str(e)}")

    # Display motivational message
    if tasks_completed == 6:
        st.success("Congratulations! You've completed all tasks for today! 💪")
    elif tasks_completed > 0:
        st.info("Keep going! You're making progress! 🎯")
