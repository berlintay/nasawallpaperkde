import QtQuick 2.15
import org.kde.plasma.core 2.0 as PlasmaCore

Item {
    width: 1920
    height: 1080

    Image {
        id: nasaImage
        anchors.fill: parent
        source: "file:///path/to/your/downloaded/nasa_image.jpg"
        fillMode: Image.PreserveAspectCrop
    }
}
