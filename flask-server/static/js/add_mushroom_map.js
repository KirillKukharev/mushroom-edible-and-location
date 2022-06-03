var marker;
var infowindow;


// Initialize and add the map
function initMap() {
  // The location of Uluru
  const uluru = { lat: 57.413948, lng: 40.346977 };

  // The map, centered at Uluru
  const map = new google.maps.Map(document.getElementById("map"), {
    zoom: 6,
    center: uluru,
  });

  google.maps.event.addListener(map, 'click', function(event) {
            placeMarker(map, event.latLng);
        });
  // // The marker, positioned at Uluru
  // const marker = new google.maps.Marker({
  //   // position: uluru,
  //   map: map,
  // });
}

function placeMarker(map, location) {
        if (!marker || !marker.setPosition) {
            marker = new google.maps.Marker({
                position: location,
                map: map,
            });
        } else {
            marker.setPosition(location);
        }
        if (!!infowindow && !!infowindow.close) {
            infowindow.close();
        }
        infowindow = new google.maps.InfoWindow({
            content: 'Latitude: ' + location.lat() + '<br>Longitude: ' + location.lng()
        });
        infowindow.open(map,marker);
        document.getElementById("lat").value = location.lat();
        document.getElementById("lng").value = location.lng();
}