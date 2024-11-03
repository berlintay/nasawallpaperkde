import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    width: 640
    height: 480

    NasaWallpaperPlugin {
        id: nasaWallpaper
        Component.onCompleted: {
            nasaWallpaper.update_wallpaper()
        }
    }
}
engine.load(QUrl.fromLocalFile("/home/mrkeays/github/nasawallpaperkde/main.qml"))
