# Import necessary libraries
import os
import base64
import requests
import pickle
import shutil
from PIL import Image
import piexif
import openai
from dotenv import load_dotenv
from iptcinfo3 import IPTCInfo

# Load environment variables from the specified path
load_dotenv('/etc/secrets/OPENAI_API_KEY')

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")

openai.api_key = api_key

# Function to encode the image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to check image dimensions
def check_image_dimensions(image_path, max_width=510, max_height=510):
    with Image.open(image_path) as img:
        return img.size[0] <= max_width and img.size[1] <= max_height

# Function to resize the image to 510x510 pixels
def resize_image(image_path, output_path, target_size=(510, 510)):
    with Image.open(image_path) as img:
        img_resized = img.resize(target_size)
        img_resized.save(output_path)

# Function to convert PNG to JPG
def convert_png_to_jpg(image_path):
    with Image.open(image_path) as img:
        jpg_path = image_path.replace('.png', '.jpg')
        rgb_image = img.convert('RGB')
        rgb_image.save(jpg_path, 'JPEG')
    return jpg_path

# Function to update image title in EXIF data
def update_image_title(image_path, new_title):
    img = Image.open(image_path)
    try:
        exif_dict = piexif.load(img.info["exif"])
    except (KeyError, TypeError, piexif.InvalidImageDataError):
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = new_title
    exif_bytes = piexif.dump(exif_dict)
    img.save(image_path, "jpeg", quality="keep", exif=exif_bytes)

# Function to update keywords in EXIF data
def update_image_keywords(image_path, keywords):
    img = Image.open(image_path)
    try:
        exif_dict = piexif.load(img.info["exif"])
    except (KeyError, TypeError, piexif.InvalidImageDataError):
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    exif_dict["0th"][piexif.ImageIFD.XPKeywords] = ','.join(keywords).encode('utf-16')
    exif_bytes = piexif.dump(exif_dict)
    img.save(image_path, "jpeg", quality="keep", exif=exif_bytes)

# Define input and output folders
input_folder = "input"
output_folder = "output"

# Create the output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Load existing results if available
if os.path.exists("results.pkl"):
    with open("results.pkl", "rb") as f:
        results = pickle.load(f)
else:
    results = {}

# Process each image in the input folder
for image_file in os.listdir(input_folder):
    original_image_path = os.path.join(input_folder, image_file)
    if image_file.lower().endswith('.png'):
        jpg_image_path = convert_png_to_jpg(original_image_path)
        image_file = os.path.basename(jpg_image_path)
    else:
        jpg_image_path = original_image_path

    resized_image_path = os.path.join(output_folder, f"resized_{image_file}")

    if image_file not in results:
        # Encode the image to base64
        if not check_image_dimensions(jpg_image_path):
            # Resize the image if it exceeds the allowed dimensions
            resize_image(jpg_image_path, resized_image_path)
            base64_image = encode_image(resized_image_path)
        else:
            base64_image = encode_image(jpg_image_path)

        # Define the API endpoint and headers
        api_endpoint = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Get the existing keywords for the image
        existing_kws = results.get(f"{image_file}_original_kws", [])

        # Define the payload for the API request
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"I want thirty keywords to describe this image for Adobe Stock, targeted towards discoverability. These keywords are already present: {existing_kws}, please include the ones that are relevant or location specific. Please output them comma separated. Please as the first entry, output an editorialized title, also separated by commas. Don't output any other characters.",
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

        # Debugging: Print the response JSON
        response_json = response.json()
        print(response_json)  # Add this line

        # Process API response and store results
        if "choices" in response_json:
            result = response_json["choices"][0]["message"]["content"]
        else:
            print("Error: 'choices' key not found in the response")
            print(response_json)  # Print the full response for debugging
            continue

        results[image_file] = result
        results[f"{image_file}_original_kws"] = existing_kws
    else:
        result = results[image_file]

    # Extract title and keywords from API response
    result_entries = result.split(", ")
    title = result_entries[0]
    kws = result_entries[1:]

    # Define the path for the new processed image
    new_image_path = os.path.join(output_folder, image_file)

    # Move the JPG image to the output folder (if it's not already there)
    if jpg_image_path != new_image_path:
        shutil.move(jpg_image_path, new_image_path)

    # Update image title and keywords in IPTC data
    update_image_title(new_image_path, title)
    info = IPTCInfo(new_image_path)
    info["keywords"] = kws
    info.save()

    # Remove the backup file if it exists
    backup_file = f"{new_image_path}~"
    if os.path.exists(backup_file):
        os.remove(backup_file)

    # Save results after each iteration
    with open("results.pkl", "wb") as f:
        pickle.dump(results, f)

    # Delete the resized image if it exists
    if os.path.exists(resized_image_path):
        os.remove(resized_image_path)

    # If a PNG file was converted, delete the resulting JPG in the input folder
    if original_image_path.lower().endswith('.png'):
        jpg_path_in_input = original_image_path.replace('.png', '.jpg')
        if os.path.exists(jpg_path_in_input):
            os.remove(jpg_path_in_input)
