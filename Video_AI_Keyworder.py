# Import necessary libraries
import os
import base64
import requests
import pickle
import shutil
import moviepy.editor as mp
from PIL import Image
from io import BytesIO
import openai
import csv

# Get the API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")

openai.api_key = api_key

# Function to encode the image to base64
def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Function to resize the image while keeping the aspect ratio
def resize_image(image, target_size=(510, 510)):
    image.thumbnail(target_size, Image.LANCZOS)
    return image

# Function to extract frames from a video
def extract_frames(video_path, timestamps):
    clip = mp.VideoFileClip(video_path)
    frames = []
    for timestamp in timestamps:
        frame = clip.get_frame(timestamp)
        frame_image = Image.fromarray(frame)
        frames.append(frame_image)
    return frames

# Function to merge two images side by side
def merge_images(image1, image2):
    (width1, height1) = image1.size
    (width2, height2) = image2.size

    result_width = width1 + width2
    result_height = max(height1, height2)

    result = Image.new('RGB', (result_width, result_height))
    result.paste(im=image1, box=(0, 0))
    result.paste(im=image2, box=(width1, 0))

    return result

# Define input and output folders
input_folder = "H:/coding/input"
output_folder = "H:/coding/output"

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Load existing results if available
if os.path.exists("results.pkl"):
    with open("results.pkl", "rb") as f:
        results = pickle.load(f)
else:
    results = {}

# Path to the CSV file
csv_file_path = os.path.join(output_folder, "results.csv")

# Check if the CSV file already exists
csv_file_exists = os.path.exists(csv_file_path)

# Process each video in the input folder
for video_file in os.listdir(input_folder):
    video_path = os.path.join(input_folder, video_file)

    if video_file.lower().endswith(('.mp4', '.mov', '.avi')):
        if video_file not in results:
            # Extract frames at 25% and 75% of the video
            clip = mp.VideoFileClip(video_path)
            duration = clip.duration
            timestamps = [duration * 0.25, duration * 0.75]
            frames = extract_frames(video_path, timestamps)

            # Resize frames
            resized_frames = [resize_image(frame) for frame in frames]

            # Merge frames into one image
            merged_image = merge_images(*resized_frames)

            # Encode the image to base64
            base64_image = encode_image(merged_image)

            # Define the API endpoint and headers
            api_endpoint = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # Define the payload for the API request
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "I want thirty keywords to describe this video for Adobe Stock, targeted towards discoverability. Please output them comma separated. Please as the first entry, output an editorialized title, also separated by commas. Don't output any other characters.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 300,
            }

            # Make the API request
            response = requests.post(api_endpoint, headers=headers, json=payload)

            # Process API response and store results
            response_json = response.json()
            if "choices" in response_json:
                result = response_json["choices"][0]["message"]["content"]
            else:
                print("Error: 'choices' key not found in the response")
                print(response_json)  # Print the full response for debugging
                continue

            results[video_file] = result
        else:
            result = results[video_file]

        # Extract title and keywords from API response
        result_entries = result.split(", ")
        title = result_entries[0]
        kws = result_entries[1:]

        # Save results to CSV file
        with open(csv_file_path, mode='a', newline='') as csv_file:
            writer = csv.writer(csv_file)
            
            # Write header only if the file didn't exist before
            if not csv_file_exists:
                writer.writerow(["Filename", "Title", "Keywords"])
                csv_file_exists = True  # Update flag after writing the header
            
            writer.writerow([video_file, title, ', '.join(kws)])

        # Save results after each iteration
        with open("results.pkl", "wb") as f:
            pickle.dump(results, f)
