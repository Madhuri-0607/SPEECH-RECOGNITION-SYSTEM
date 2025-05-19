import speech_recognition as sr
import time
import os
import streamlit as st
from datetime import datetime
import pyperclip
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from gtts import gTTS
import base64

def setup_recognizer():
    """Initialize and configure the speech recognizer."""
    r = sr.Recognizer()
    r.energy_threshold = st.session_state.energy_threshold
    r.dynamic_energy_threshold = st.session_state.dynamic_energy
    r.dynamic_energy_adjustment_damping = 0.15
    r.pause_threshold = st.session_state.pause_threshold
    r.non_speaking_duration = st.session_state.non_speaking_duration
    return r

def visualize_audio():
    """Show real-time audio visualization."""
    duration = 1  # seconds
    fs = 44100  # sample rate
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    
    fig, ax = plt.subplots(figsize=(10, 2))
    ax.plot(np.arange(len(recording[0])), recording[0], color='cyan')
    ax.axis('off')
    fig.patch.set_facecolor('#000000')
    ax.set_facecolor('#000000')
    st.pyplot(fig)

def recognize_speech(api_choice):
    """Handle speech recognition based on selected API."""
    response = {
        "success": True,
        "error": None,
        "transcription": None,
        "api": api_choice
    }

    try:
        with st.session_state.microphone as source:
            st.session_state.status = "Adjusting for ambient noise..."
            st.session_state.recognizer.adjust_for_ambient_noise(
                source, 
                duration=st.session_state.adjustment_duration
            )
            st.session_state.status = "Listening... Speak now!"
            
            if st.session_state.show_visualization:
                visualize_audio()
                
            audio = st.session_state.recognizer.listen(
                source, 
                timeout=st.session_state.timeout,
                phrase_time_limit=st.session_state.phrase_limit
            )

        try:
            if api_choice == "Google":
                response["transcription"] = st.session_state.recognizer.recognize_google(audio, language=st.session_state.language)
            elif api_choice == "Wit.ai":
                response["transcription"] = st.session_state.recognizer.recognize_wit(
                    audio, 
                    key=st.session_state.wit_ai_key
                )
            elif api_choice == "Sphinx":
                response["transcription"] = st.session_state.recognizer.recognize_sphinx(audio)
        except sr.UnknownValueError:
            response["success"] = False
            response["error"] = "Could not understand audio"
        except sr.RequestError as e:
            response["success"] = False
            if api_choice == "Wit.ai":
                if "quota" in str(e).lower():
                    response["error"] = "Wit.ai quota exceeded"
                elif "invalid" in str(e).lower():
                    response["error"] = "Invalid Wit.ai API key"
                else:
                    response["error"] = f"Wit.ai error: {str(e)}"
            else:
                response["error"] = f"API error: {str(e)}"

    except Exception as e:
        response["success"] = False
        response["error"] = f"Recording error: {str(e)}"

    return response

def save_transcription(filename, text):
    """Save transcription to markdown file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"- {timestamp}: {text}\n")

def clear_transcriptions():
    """Clear all transcriptions from session state."""
    st.session_state.transcriptions = []
    if os.path.exists(st.session_state.output_filename):
        os.remove(st.session_state.output_filename)
    st.session_state.status = "Ready"
    st.success("Transcriptions cleared!")

def delete_transcription(index):
    """Delete a specific transcription by index."""
    if 0 <= index < len(st.session_state.transcriptions):
        deleted_text = st.session_state.transcriptions.pop(index)
        
        # Update the markdown file
        if os.path.exists(st.session_state.output_filename):
            with open(st.session_state.output_filename, "w", encoding="utf-8") as f:
                for idx, (timestamp, text, api) in enumerate(st.session_state.transcriptions):
                    f.write(f"- {timestamp}: {text}\n")
        
        st.success(f"Deleted transcription: {deleted_text[1][:50]}...")
    else:
        st.error("Invalid transcription index")

def text_to_speech(text, lang='en'):
    """Convert text to speech and provide audio player."""
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save("output.mp3")
    
    audio_file = open("output.mp3", "rb")
    audio_bytes = audio_file.read()
    
    st.audio(audio_bytes, format='audio/mp3')
    
    # Create download link
    b64 = base64.b64encode(audio_bytes).decode()
    href = f'<a href="data:audio/mp3;base64,{b64}" download="speech_output.mp3" style="color: cyan;">Download Audio</a>'
    st.markdown(href, unsafe_allow_html=True)

def main():
    # App configuration
    st.set_page_config(
        page_title="SPEECH RECOGNITION SYSTEM",
        page_icon="🎤",
        layout="centered"
    )

    # Custom CSS with dark theme
    st.markdown("""
    <style>
    :root {
        --primary: #3182bd;
        --background: #121212;
        --secondary: #1a1a1a;
        --text: #ffffff;
        --accent: #00ffff;
    }
    
    body {
        color: var(--text);
        background-color: var(--background);
    }
    
    .stApp {
        background-color: var(--background);
    }
    
    .stButton>button {
        width: 100%;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        background-color: var(--secondary);
        color: var(--text);
        border: 1px solid var(--primary);
    }
    
    .stButton>button:hover {
        background-color: var(--primary);
        color: white;
    }
    
    .transcription-box {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        background-color: #000000;
        border-left: 5px solid var(--accent);
        color: var(--text);
        font-family: monospace;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid;
        background-color: var(--secondary);
        color: var(--text);
    }
    
    .api-tag {
        font-size: 0.8rem;
        color: black;
        background-color: var(--accent);
        padding: 0.2rem 0.5rem;
        border-radius: 0.5rem;
        display: inline-block;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    
    .settings-expander {
        background-color: var(--secondary);
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        color: var(--text);
    }
    
    .stTextInput>div>div>input {
        color: var(--text);
        background-color: var(--secondary);
        border-radius: 0.5rem;
    }
    
    .stSelectbox>div>div>select {
        color: var(--text);
        background-color: var(--secondary);
    }
    
    .stSlider>div>div>div>div {
        color: var(--text);
    }
    
    .stCheckbox>label {
        color: var(--text);
    }
    
    .stSuccess {
        color: var(--accent);
    }
    
    .stInfo {
        background-color: var(--secondary) !important;
    }
    
    .delete-btn {
        background-color: #ff5555 !important;
        border-color: #ff0000 !important;
    }
    
    .delete-btn:hover {
        background-color: #ff0000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🎤 SPEECH RECOGNITION SYSTEM")
    st.markdown("Convert speech to text with professional dark interface")

    # Initialize session state with default values
    defaults = {
        'transcriptions': [],
        'is_listening': False,
        'stop_phrase': "stop recording",
        'output_filename': "transcriptions.md",
        'status': "Ready",
        'wit_ai_key': "",
        'api_choice': "Google",
        'energy_threshold': 300,
        'dynamic_energy': True,
        'pause_threshold': 1.5,
        'non_speaking_duration': 0.3,
        'adjustment_duration': 1.5,
        'timeout': 8,
        'phrase_limit': 20,
        'show_visualization': False,
        'auto_scroll': True,
        'language': 'en-US',
        'save_to_file': True
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize recognizer and microphone
    if 'recognizer' not in st.session_state:
        st.session_state.recognizer = setup_recognizer()
    if 'microphone' not in st.session_state:
        st.session_state.microphone = sr.Microphone()

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # API selection
        st.session_state.api_choice = st.selectbox(
            "Speech Recognition API",
            ["Google", "Wit.ai", "Sphinx"],
            index=["Google", "Wit.ai", "Sphinx"].index(st.session_state.api_choice)
        )
        
        if st.session_state.api_choice == "Wit.ai":
            st.session_state.wit_ai_key = st.text_input(
                "Wit.ai API Key",
                value=st.session_state.wit_ai_key,
                type="password"
            )
        
        # Advanced settings
        with st.expander("🔧 Advanced Settings"):
            st.session_state.energy_threshold = st.slider(
                "Energy Threshold",
                0, 4000, st.session_state.energy_threshold
            )
            st.session_state.dynamic_energy = st.checkbox(
                "Dynamic Energy Threshold",
                value=st.session_state.dynamic_energy
            )
            st.session_state.pause_threshold = st.slider(
                "Pause Threshold (seconds)",
                0.5, 3.0, st.session_state.pause_threshold,
                step=0.1
            )
            st.session_state.language = st.selectbox(
                "Language",
                ['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-BR'],
                index=['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-BR'].index(st.session_state.language)
            )
        
        st.session_state.stop_phrase = st.text_input(
            "Stop Phrase",
            value=st.session_state.stop_phrase
        )
        
        st.session_state.show_visualization = st.checkbox(
            "Show Audio Visualization",
            value=st.session_state.show_visualization
        )
        
        if st.button("🧹 Clear All Transcripts"):
            clear_transcriptions()

    # Main interface
    status_col, btn_col = st.columns([3, 1])
    
    with status_col:
        status_color = "#3182bd"  # Blue
        if "error" in st.session_state.status.lower():
            status_color = "#ff5555"  # Red
        elif "listening" in st.session_state.status.lower():
            status_color = "#55ff55"  # Green
        
        st.markdown(
            f"""<div class="status-box" style="border-left-color: {status_color}">
                <strong>Status:</strong> {st.session_state.status}
                </div>""",
            unsafe_allow_html=True
        )
    
    with btn_col:
        if st.session_state.is_listening:
            if st.button("⏹️ Stop"):
                st.session_state.is_listening = False
                st.session_state.status = "Stopped manually"
                st.rerun()
        else:
            if st.button("🎤 Start"):
                if st.session_state.api_choice == "Wit.ai" and not st.session_state.wit_ai_key:
                    st.error("Please enter your Wit.ai API key")
                else:
                    st.session_state.is_listening = True
                    st.session_state.status = "Starting..."
                    st.rerun()

    # Recording logic
    if st.session_state.is_listening:
        result = recognize_speech(st.session_state.api_choice)
        
        if result["success"]:
            if result["transcription"]:
                text = result["transcription"]
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.transcriptions.insert(0, (timestamp, text, result["api"]))
                
                if st.session_state.save_to_file:
                    save_transcription(st.session_state.output_filename, text)
                
                # Check for stop phrase
                if st.session_state.stop_phrase.lower() in text.lower():
                    st.session_state.is_listening = False
                    st.session_state.status = f"Stopped (heard '{st.session_state.stop_phrase}')"
                    st.rerun()
                else:
                    st.session_state.status = f"Listening... Last heard: {text[:30]}..."
            else:
                st.session_state.status = "Listening..."
        else:
            st.session_state.status = result["error"]
            st.session_state.is_listening = False
        
        time.sleep(0.1)
        st.rerun()

    # Display transcriptions
    st.subheader("📜 Transcripts")
    
    # Text-to-speech for latest transcription
    if st.session_state.transcriptions:
        latest_text = st.session_state.transcriptions[0][1]
        with st.expander("🔊 Text-to-Speech"):
            text_to_speech(latest_text, lang=st.session_state.language[:2])
    
    if not st.session_state.transcriptions:
        st.info("No transcriptions yet. Click 'Start' to begin recording.")
    else:
        transcript_container = st.container()
        
        with transcript_container:
            for idx, (timestamp, text, api) in enumerate(st.session_state.transcriptions):
                col1, col2, col3 = st.columns([8, 1, 1])
                
                with col1:
                    st.markdown(
                        f"""<div class="transcription-box">
                            <small style="color: #aaaaaa;">{timestamp}</small>
                            <div class="api-tag">{api}</div>
                            <p>{text}</p>
                            </div>""",
                        unsafe_allow_html=True
                    )
                
                with col2:
                    if st.button("📋", key=f"copy_{idx}"):
                        pyperclip.copy(text)
                        st.success("Copied!")
                
                with col3:
                    if st.button("🗑️", key=f"delete_{idx}", help="Delete this transcription"):
                        delete_transcription(idx)
                        st.rerun()
            
            if st.session_state.auto_scroll:
                st.markdown(
                    """
                    <script>
                    window.addEventListener('load', function() {
                        window.parent.document.querySelector('section.main').scrollTo(0, 0);
                    });
                    </script>
                    """,
                    unsafe_allow_html=True
                )

        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if os.path.exists(st.session_state.output_filename):
                with open(st.session_state.output_filename, "rb") as f:
                    st.download_button(
                        "📥 Download Markdown",
                        f,
                        file_name=st.session_state.output_filename,
                        mime="text/markdown"
                    )
        
        with col2:
            all_text = "\n\n".join([f"[{t[0]}] {t[1]}" for t in st.session_state.transcriptions])
            st.download_button(
                "📝 Export as Text",
                data=all_text,
                file_name="transcriptions.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()