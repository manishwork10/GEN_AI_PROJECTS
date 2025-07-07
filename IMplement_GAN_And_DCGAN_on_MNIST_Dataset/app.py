import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import load_model

# Load trained generator model
generator = load_model("dcgan_generator.keras")

st.title("🎨 DCGAN MNIST Generator")

if st.button("Generate Digit"):
    noise = tf.random.normal([1, 100])
    generated_image = generator(noise, training=False)[0, :, :, 0]
    
    # Normalize to display
    generated_image = (generated_image + 1.0) / 2.0

    st.image(generated_image.numpy(), caption="Generated Digit", width=200, clamp=True)
