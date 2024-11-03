import requests
import json
import os
import sys
from datetime import datetime
import time
import schedule
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil
import subprocess
from dbus import SessionBus, Interface
import dbus
import random

class KDENASAWallpaper:
    def __init__(self, api_key: str):
        """
        Initialize the NASA Wallpaper Plugin for KDE

        Args:
            api_key (str): NASA API key for authentication
        """
        self.api_key = api_key
        self.base_url = "https://images-api.nasa.gov"

        # Set up KDE-specific paths
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / '.config' / 'plasma-nasa-wallpaper'
        self.cache_dir = self.home_dir / '.cache' / 'plasma-nasa-wallpaper'
        self.wallpaper_dir = self.home_dir / 'Pictures' / 'NASA-Wallpapers'

        # Create necessary directories with proper permissions
        for directory in [self.config_dir, self.cache_dir, self.wallpaper_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o755)

        # Setup logging
        log_file = self.config_dir / 'wallpaper.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.RotatingFileHandler(
                    log_file,
                    maxBytes=1024*1024,
                    backupCount=3
                ),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Initialize DBus connection for KDE
        self.session_bus = SessionBus()
        self.init_kde_interface()

    def init_kde_interface(self):
        """Initialize KDE's DBus interface for wallpaper management"""
        try:
            plasma = self.session_bus.get_object('org.kde.plasmashell', '/PlasmaShell')
            self.plasma_interface = Interface(plasma, dbus_interface='org.kde.PlasmaShell')

            # Get current screen configuration
            self.update_screen_config()

            self.logger.info("Successfully connected to KDE Plasma interface")
        except Exception as e:
            self.logger.error(f"Failed to initialize KDE interface: {str(e)}")
            sys.exit(1)

    def update_screen_config(self):
        """Update current screen configuration"""
        try:
            kscreen = self.session_bus.get_object('org.kde.KScreen', '/backend')
            config = Interface(kscreen, dbus_interface='org.kde.KScreen').GetConfig()
            self.screen_config = config
        except Exception as e:
            self.logger.error(f"Failed to get screen config: {str(e)}")

    def set_wallpaper(self, image_path: str, screen_id: int = -1):
        """
        Set wallpaper for specified screen using KDE's DBus interface

        Args:
            image_path (str): Path to wallpaper image
            screen_id (int): Screen ID (-1 for all screens)
        """
        try:
            script = f"""
                var allDesktops = desktops();
                for (var i = 0; i < allDesktops.length; i++) {{
                    var desktop = allDesktops[i];
                    desktop.wallpaperPlugin = "org.kde.image";
                    desktop.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
                    desktop.writeConfig("Image", "file://{image_path}");
                    desktop.writeConfig("FillMode", "6");
                }}
            """
            self.plasma_interface.evaluateScript(script)
            self.logger.info(f"Successfully set wallpaper: {image_path}")

            # Save wallpaper history
            self.save_wallpaper_history(image_path)

        except Exception as e:
            self.logger.error(f"Failed to set wallpaper: {str(e)}")

    def save_wallpaper_history(self, image_path: str):
        """Save wallpaper history to JSON file"""
        history_file = self.config_dir / 'wallpaper_history.json'
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []

            history.append({
                'path': str(image_path),
                'date': datetime.now().isoformat(),
            })

            # Keep only last 50 entries
            history = history[-50:]

            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save wallpaper history: {str(e)}")

    def search_images(self, query: str = "space", min_width: int = 1920, min_height: int = 1080) -> Optional[Dict[str, Any]]:
        """Search for NASA images suitable for wallpapers"""
        try:
            params = {
                "q": query,
                "media_type": "image",
                "api_key": self.api_key,
                "keywords": "hd,space,astronomy",
            }
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            return None

    def download_wallpaper(self, image_url: str, nasa_id: str) -> Optional[str]:
        """Download and prepare wallpaper image"""
        try:
            # Create temporary file for downloading
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                temp_path = Path(tmp_file.name)

            # Download image
            response = requests.get(image_url, params={"api_key": self.api_key})
            response.raise_for_status()

            with open(temp_path, 'wb') as f:
                f.write(response.content)

            # Create final filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = image_url.split('.')[-1].lower()
            filename = f"nasa_{nasa_id}_{timestamp}.{file_extension}"
            file_path = self.wallpaper_dir / filename

            # Move file to final location
            shutil.move(temp_path, file_path)
            os.chmod(file_path, 0o644)

            return str(file_path)

        except Exception as e:
            self.logger.error(f"Download error: {str(e)}")
            if 'temp_path' in locals():
                temp_path.unlink(missing_ok=True)
            return None

    def fetch_and_set_wallpaper(self, query: str = "space"):
        """Fetch new NASA image and set as wallpaper"""
        try:
            # Search for images
            results = self.search_images(query)
            if not results or 'collection' not in results:
                return

            items = results['collection'].get('items', [])
            if not items:
                return

            # Randomly select an image
            item = random.choice(items)
            nasa_id = item.get('data', [{}])[0].get('nasa_id')
            if not nasa_id:
                return

            # Get image URL
            asset_url = f"{self.base_url}/asset/{nasa_id}"
            response = requests.get(asset_url, params={"api_key": self.api_key})
            response.raise_for_status()

            manifest = response.json()
            image_url = None
            for asset in manifest.get('collection', {}).get('items', []):
                if asset['href'].lower().endswith(('.jpg', '.jpeg', '.png')):
                    image_url = asset['href']
                    break

            if not image_url:
                return

            # Download and set wallpaper
            wallpaper_path = self.download_wallpaper(image_url, nasa_id)
            if wallpaper_path:
                self.set_wallpaper(wallpaper_path)

        except Exception as e:
            self.logger.error(f"Failed to fetch and set wallpaper: {str(e)}")

def create_plasma_plugin():
    """Create KDE Plasma wallpaper plugin files"""
    plugin_dir = Path.home() / '.local' / 'share' / 'plasma' / 'wallpapers' / 'nasa'
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Create metadata.desktop file
    metadata_content = """
[Desktop Entry]
Name=NASA Image of the Day
Comment=Automatically fetches and displays NASA images
Type=Service
ServiceTypes=Plasma/Wallpaper
Icon=preferences-desktop-wallpaper
X-Plasma-MainScript=ui/main.qml
X-KDE-PluginInfo-Name=org.kde.plasma.nasa-wallpaper
X-KDE-PluginInfo-Author=Your Name
X-KDE-PluginInfo-Email=your.email@example.com
X-KDE-PluginInfo-License=GPL-3.0
X-KDE-PluginInfo-Version=1.0
"""

    with open(plugin_dir / 'metadata.desktop', 'w') as f:
        f.write(metadata_content.strip())

    # Create main.qml file
    qml_dir = plugin_dir / 'contents' / 'ui'
    qml_dir.mkdir(parents=True, exist_ok=True)

    qml_content = """
import QtQuick 2.1
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.0 as Controls
import org.kde.plasma.core 2.0 as PlasmaCore

ColumnLayout {
    id: root
    property string cfg_Image
    property int cfg_FillMode
    property var cfg_Color: "black"

    Controls.Label {
        text: "NASA Image of the Day Wallpaper"
    }

    Controls.ComboBox {
        Layout.fillWidth: true
        model: ["Space", "Earth", "Mars", "Jupiter", "Saturn"]
        onCurrentTextChanged: {
            // Signal to update wallpaper
        }
    }
}
"""

    with open(qml_dir / 'main.qml', 'w') as f:
        f.write(qml_content.strip())

def main():
    API_KEY = "CdfwBW7mA3XofhaevIXum5nVx5aKojkRe534pII1"

    # Create KDE Plasma plugin files
    create_plasma_plugin()

    # Initialize wallpaper manager
    wallpaper = KDENASAWallpaper(API_KEY)

    # Schedule wallpaper updates
    schedule.every(6).hours.do(wallpaper.fetch_and_set_wallpaper)

    # Initial wallpaper
    wallpaper.fetch_and_set_wallpaper()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
