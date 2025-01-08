import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="75 Hard Tracker", layout="wide")

# Initialize session state for tracking
if 'days_completed' not in st.session_state:
    st.session_state.days_completed = 0
if 'current_streak' not in st.session_state:
    st.session_state.current_streak = 0
# Initialize checkbox states
if 'workout1' not in st.session_state:
    st.session_state.workout1 = False
if 'workout2' not in st.session_state:
    st.session_state.workout2 = False
if 'diet' not in st.session_state:
    st.session_state.diet = False
if 'water' not in st.session_state:
    st.session_state.water = False
if 'reading' not in st.session_state:
    st.session_state.reading = False
if 'picture' not in st.session_state:
    st.session_state.picture = False
if 'should_reset' not in st.session_state:
    st.session_state.should_reset = False

# If should_reset is True, reset all checkboxes
if st.session_state.should_reset:
    st.session_state.workout1 = False
    st.session_state.workout2 = False
    st.session_state.diet = False
    st.session_state.water = False
    st.session_state.reading = False
    st.session_state.picture = False
    st.session_state.should_reset = False

st.title("75 Hard Challenge Tracker")

# Sidebar for user actions
with st.sidebar:
    st.header("Daily Tasks")
    
    # Task checkboxes using session state
    workout1 = st.checkbox("First Workout (45 min)", key='workout1')
    workout2 = st.checkbox("Second Workout (45 min, outdoors)", key='workout2')
    diet = st.checkbox("Follow Diet Plan", key='diet')
    water = st.checkbox("Drink 1 Gallon Water", key='water')
    reading = st.checkbox("Read 10 Pages", key='reading')
    picture = st.checkbox("Take Progress Picture", key='picture')

    if st.button("Submit Daily Progress"):
        # Prepare data to send to API
        data = {
            "workout_1": workout1,
            "workout_2": workout2,
            "diet": diet,
            "water": water,
            "reading": reading,
            "progress_picture": picture
        }
        
        try:
            response = requests.post(
                "http://localhost:8000/day/complete",
                json=data
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
                # Update the stats even when blocked
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

# Display motivational message
if tasks_completed == 6:
    st.success("Congratulations! You've completed all tasks for today! 💪")
elif tasks_completed > 0:
    st.info("Keep going! You're making progress! 🎯")
