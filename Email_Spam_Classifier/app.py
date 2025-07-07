import streamlit as st
import joblib

# Load the saved model and vectorizer
model = joblib.load("spam_detector.pkl")
vectorizer = joblib.load("vectorizer.pkl")

st.title("📧 Spam Email Classifier")
st.write("Enter a message below to check if it's spam or not.")

user_input = st.text_area("Type your message:")

if st.button("Check"):
    if user_input.strip():
        # Preprocess using the saved vectorizer
        input_vector = vectorizer.transform([user_input])
        prediction = model.predict(input_vector)[0]
        
        if prediction == 1:
            st.success("✅ It's a **HAM** (not spam) message.")
        else:
            st.error("🚨 It's a **SPAM** message.")
    else:
        st.warning("Please enter a message.")
