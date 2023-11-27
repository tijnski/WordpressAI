import requests
import json
import openai
import base64
import pandas as pd
import os
import csv

# Define a mapping of category names to IDs
CATEGORY_NAME_TO_ID = {
    "Finance": 27,
    "Technology": 11,
    "Cryptocurrency": 15,
    "Investing": 46,
    # ... (other categories)
}

def read_csv_file(filename):
    with open(filename, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        rows = list(reader)
    return rows

internal_links = read_csv_file('categories_and_slugs.csv')

# Fetch Topics from CSV
def fetch_topics_from_csv(filename):
    print("Fetching topics from the CSV file...")

    df = pd.read_csv(filename)
    urls = df['URL-SLUG'].tolist()
    titles = df['TOPIC-TITLE'].tolist()
    descriptions = df['TOPIC-DESCRIPTION'].tolist()
    categories = df['CATEGORY'].tolist()

    print(f"Found {len(titles)} topics from the CSV file.")
    return titles, descriptions, categories, urls  # Include urls in the return statement

# Function to append category and URL-slug to a CSV file
def append_to_csv(category, url):
    print(f"Appending to CSV: {category}, {url}")  # Debugging print statement
    with open('categories_and_slugs.csv', mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([f"/{category}/{url}"])

# Generate Content using GPT-4
openai.api_key = 'sk-YOUR-API-KEY'

def generate_content(topic, internal_links):
    print(f"Generating content for topic: {topic}...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai.api_key}"
    }

    internal_links_prompt = " Ensure to include relevant internal links such as " + ', '.join([f'[{link[0]}]({link[0]})' for link in internal_links]) + " within the article."

    data = {
        "model": "gpt-3.5-turbo-16k",
        "messages": [
            {"role": "system", "content": "you are a blogger named Philip Moore that writes articles for https://capitalcoinage.com"},
            {"role": "user", "content": f"Write an article about {topic}. Internal are a MUST for SEO, external links are also VITAL for the article for example wikipedia or an other blog/ article. ALWAYS WRITE ALL THE ARTICLE IN FULL. Output in HTML is a MUST. Write an article with 7 headings and 8 paragraphs per heading, the word heading should not be used in the heading. EACH heading of the article should have at least one list or table (with a small black border, and border between the rows and columns) Please always include ahref internal links or external links, contextually in the article not just at the end. NEVER USE PLACEHOLDERS {internal_links_prompt} "}
        ]
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(data))
    response_data = response.json()

    return response_data["choices"][0]["message"]["content"].strip()

# Fetch Image from STABILITY API
STABILITY_API_KEY = 'sk-YOUR-API-KEY'

def generate_featured_image(text, title):
    print(f"Generating Image...")
    api_host = 'https://api.stability.ai'
    engine_id = 'stable-diffusion-xl-1024-v1-0'
    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {STABILITY_API_KEY}"
        },
        json={
            "text_prompts": [
                {
                    "text": f' a image about {title} make sure to not use any text and make it realistic',
                    "weight": 1
                },
                {
                    "text": "blurry, bad",
                    "weight": -1
                }
            ],
            "cfg_scale": 8,
            "style_preset": "photographic",
            "height": 768,
            "width": 1344,
            "samples": 1,
            "steps": 40,
        },
    )
    if response.status_code != 200:
        print(f"Failed to generate image for meta_title: {title}. Response: {response.text}")
        return None

    data = response.json()
    image_base64 = data["artifacts"][0]["base64"]
    image_filename = f"./out/{text.replace(' ', '_').replace('/', '_')}.png"
    if not os.path.exists('./out'):
        os.makedirs('./out')
    with open(image_filename, "wb") as f:
        f.write(base64.b64decode(image_base64))
    return image_filename

# Function to add Focus keyphrase to WordPress post using custom plugin endpoint
def add_focus_keyphrase(post_id, keyphrase):
    print(f"Adding Focus Keyphrase: {keyphrase} to post ID: {post_id}...")
    username = "YOUR-ISERNAME"
    app_password = "YOUR-PASSWORD"
    credentials = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    headers = {"Authorization": f"Basic {credentials}"}
    
    keyphrase_data = {
        "keyphrase": keyphrase
    }
    
    keyphrase_response = requests.post(
        f"https://YOURWEBSITE.com/wp-json/custom-yoast/v1/update-keyphrase/{post_id}",
        headers=headers,
        json=keyphrase_data
    )
    
    if keyphrase_response.status_code == 200:  # Assuming your plugin returns a 200 status code on success
        print(f"Successfully added Focus Keyphrase to post ID: {post_id}")
    else:
        print(f"Failed to add Focus Keyphrase to post ID: {post_id}. Response: {keyphrase_response.text}")

# Example Usage:
# Replace 123 with the actual post ID and "Your Focus Keyphrase" with the actual focus keyphrase
# add_focus_keyphrase(123, "Your Focus Keyphrase")

# Post to WordPress with Featured Image
def post_to_wordpress(title, content, image_path, category_name):
    print(f"Posting content for topic: {title} to WordPress...")
    username = "YOUR-USERNAME"
    app_password = "YOUR-PASSWORD"
    credentials = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    headers = {"Authorization": f"Basic {credentials}"}

    category_id = CATEGORY_NAME_TO_ID.get(category_name, None)
    if category_id is None:
        print(f"Unknown category: {category_name}")
        return None
    
    with open(image_path, "rb") as image_file:
        media_response = requests.post(
            "https://YOURWEBSITE.com/wp-json/wp/v2/media",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Disposition": f'attachment; filename="{title}.png"',
                "Content-Type": "image/png"
            },
            data=image_file
        )
    
        if media_response.status_code != 201:
            print(f"Failed to upload image for topic: {title}. Response: {media_response.text}")
            return None

        media_id = media_response.json()['id']

        post_data = {
            "title": title,
            "content": content,
            "status": "publish",
            "featured_media": media_id,
            "categories": [category_id]  # Use the category ID here
        }
    
        post_response = requests.post(
            "https://YOURWEBSITE.com/wp-json/wp/v2/posts",
            headers=headers,
            json=post_data
        )
    
        if post_response.status_code == 201:
            print(f"Successfully posted content for topic: {title}")
            post_response_data = post_response.json()
            post_id = post_response_data['id']
            add_focus_keyphrase(post_id, title)  # Add focus keyphrase as custom field
        else:
            print(f"Failed to post content for topic: {title}. Response: {post_response.text}")

        return post_response.json()
# Main Routine
if __name__ == "__main__":
    titles, descriptions, categories, urls = fetch_topics_from_csv('input.csv')  # Include urls in the unpacking statement
    internal_links = read_csv_file('categories_and_slugs.csv')
    
    for i, title in enumerate(titles):
        category_name = categories[i]
        url_slug = urls[i]  # Now urls list is properly defined and obtained from fetch_topics_from_csv
        description = descriptions[i]
        content = generate_content(description, internal_links)
        image_path = generate_featured_image(title, title)
        if image_path:
            post_to_wordpress(title, content, image_path, category_name)
        
        # Call to append_to_csv
        append_to_csv(category_name, url_slug)