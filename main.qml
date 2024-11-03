import requests
import os
import subprocess
from typing import Optional
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NASA API Endpoints
NASA_SEARCH_ENDPOINT = "https://images-api.nasa.gov/search"
NASA_ASSET_ENDPOINT = "https://images-api.nasa.gov/asset"

# NASA API Key
API_KEY = "CdfwBW7mA3XofhaevIXum5nVx5aKojkRe534pII1"

# Path to save the image
SAVE_PATH = os.path.expanduser("~/Pictures/nasa_wallpaper.jpg")

def search_nasa_images(query: str, max_retries: int = 3) -> Optional[str]:
    """
    Search NASA images using the NASA API with retry mechanism and error handling.

    This function searches for NASA images based on the provided query. It implements
    a retry mechanism with exponential backoff to handle potential network issues.

    Parameters:
    query (str): The search query to find NASA images.
    max_retries (int, optional): The maximum number of retry attempts. Defaults to 3.

    Returns:
    Optional[str]: The NASA ID of the first image found, or None if no images are found
                   or if all retry attempts fail.
    """
    params = {
        'q': query,
        'media_type': 'image',
        'api_key': API_KEY
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(NASA_SEARCH_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get('collection', {}).get('items', [])

            if items:
                return items[0]['data'][0]['nasa_id']
            logger.warning("No items found for the query.")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue

    return None

def get_asset_url(nasa_id: str) -> Optional[str]:
    """Get asset URL with error handling."""
    try:
        response = requests.get(f"{NASA_ASSET_ENDPOINT}/{nasa_id}", timeout=10)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('collection', {}).get('items', [])
        
        if items:
            return items[-1]['href']
        logger.warning("No asset found.")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve asset: {e}")
        return None

def download_image(image_url: str, save_path: str) -> bool:
    """Download image with proper error handling and directory creation."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        with open(save_path, 'wb') as file:
            file.write(response.content)
        logger.info(f"Image successfully downloaded to {save_path}")
        return True
        
    except (requests.exceptions.RequestException, IOError) as e:
        logger.error(f"Failed to download image: {e}")
        return False

def set_wallpaper(image_path: str) -> bool:
    """Set KDE wallpaper with error handling."""
    if not os.path.exists(image_path):
        logger.error(f"Image file not found: {image_path}")
        return False

    try:
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
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info("Wallpaper set successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to set wallpaper: {e}")
        logger.error(f"Command output: {e.output}")
        return False

def main():
    """Main function with proper error handling."""
    query = "Mars"
    
    nasa_id = search_nasa_images(query)
    if not nasa_id:
        logger.error("Failed to find NASA image")
        return
    
    image_url = get_asset_url(nasa_id)
    if not image_url:
        logger.error("Failed to get image URL")
        return
    
    if not download_image(image_url, SAVE_PATH):
        logger.error("Failed to download image")
        return
    
    if not set_wallpaper(SAVE_PATH):
        logger.error("Failed to set wallpaper")
        return

if __name__ == "__main__":
    main()
