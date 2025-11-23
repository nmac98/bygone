function initLeafletMap(mapId, center, locationData) {
    const map = L.map(mapId, {
        scrollWheelZoom: false, // nicer UX
    }).setView(center, 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19
    }).addTo(map);

    const markers = [];

    locationData.forEach(loc => {
        const marker = L.marker([loc.lat, loc.lon]).addTo(map);

        const popupHtml = `
            <b>${loc.name}</b><br>
            <img src="/static/images/${loc.main_image}" width="140"><br>
            <a href="/gallery/${loc.id}" class="pop-link">View Photos</a>
        `;

        marker.bindPopup(popupHtml);
        markers.push(marker);
    });

    if (markers.length > 0) {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.2));
    }

    return map;
}
