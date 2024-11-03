import requests
import os
import subprocess

# NASA API Endpoints
NASA_SEARCH_ENDPOINT = "https://images-api.nasa.gov/search"
NASA_ASSET_ENDPOINT = "https://images-api.nasa.gov/asset"

# NASA API Key
API_KEY = "CdfwBW7mA3XofhaevIXum5nVx5aKojkRe534pII1"

# Path to save the image
SAVE_PATH = "/tmp/nasa_wallpaper.jpg"

# Step 1: Search for an image from NASA

def search_nasa_images(query):
    params = {
        'q': query,
        'media_type': 'image'
    }
    response = requests.get(NASA_SEARCH_ENDPOINT, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data['collection']['items']
        if items:
            return items[0]['data'][0]['nasa_id']
        else:
            print("No items found for the query.")
            return None
    else:
        print(f"Failed to search. Status code: {response.status_code}")
        return None

# Step 2: Get the asset URL using the NASA ID

def get_asset_url(nasa_id):
    response = requests.get(f"{NASA_ASSET_ENDPOINT}/{nasa_id}")
    if response.status_code == 200:
        data = response.json()
        items = data['collection']['items']
        if items:
            return items[-1]['href']  # Typically the last item is the full resolution image
        else:
            print("No asset found.")
            return None
    else:
        print(f"Failed to retrieve asset. Status code: {response.status_code}")
        return None

# Step 3: Download the image

def download_image(image_url, save_path):
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
            print(f"Image successfully downloaded to {save_path}")
    else:
        print(f"Failed to download image. Status code: {response.status_code}")

# Step 4: Set the KDE wallpaper using qdbus

def set_wallpaper(image_path):
    command = [
        "qdbus", "org.kde.plasmashell", "/PlasmaShell",
        "org.kde.PlasmaShell.evaluateScript",
        f'''
        var Desktops = desktops();
        for (i=0;i<Desktops.length;i++) {{
            d = Desktops[i];
            d.wallpaperPlugin = "org.kde.image";
            d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General");
            d.writeConfig("Image", "file://{image_path}");
        }}
        '''
    ]
    subprocess.run(command)

# Main script execution
if __name__ == "__main__":
    query = "Mars"  # You can change this to any keyword you want
    nasa_id = search_nasa_images(query)
    if nasa_id:
        image_url = get_asset_url(nasa_id)
        if image_url:
            download_image(image_url, SAVE_PATH)
            set_wallpaper(SAVE_PATH)
