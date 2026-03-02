/* ── Carrigtwohill Interactive Historical Map — map.js ── */

(function () {
  'use strict';

  // ── CONFIG ──
  var CENTER = [51.9101, -8.2612];
  var ZOOM = 14;

  var POI_ICONS = {
    castle:    '\u{1F3F0}',
    abbey:     '\u26EA',
    church:    '\u26EA',
    graveyard: '\u{1FAA6}',
    house:     '\u{1F3E0}',
    site:      '\u{1F4CD}',
    monument:  '\u{1F3DB}',
    school:    '\u{1F3EB}',
    bridge:    '\u{1F309}',
    well:      '\u{1F4A7}',
    fort:      '\u{1F6E1}',
    default:   '\u{1F4CD}'
  };

  var ERA_LABELS = {
    all:      'All Eras',
    norman:   'Norman (1177\u20131350)',
    medieval: 'Medieval (1350\u20131600)',
    tudor:    'Tudor (1500\u20131650)',
    famine:   'Famine (1845\u20131852)',
    modern:   'Modern (1900\u2013)'
  };

  // ── STATE ──
  var map, townlandsLayer, poisLayer, personsLayer;
  var currentEra = 'all';
  var wwhMode = false;
  var allTownlandsData = null;

  // ── INIT ──
  function init() {
    map = L.map('map', {
      center: CENTER,
      zoom: ZOOM,
      zoomControl: true,
      gestureHandling: true
    });

    // OSM base layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
      crossOrigin: 'anonymous'
    }).addTo(map);

    // Init layers
    townlandsLayer = L.geoJSON(null, {
      style: townlandStyle,
      onEachFeature: onEachTownland
    }).addTo(map);

    poisLayer = L.markerClusterGroup({
      maxClusterRadius: 40,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false
    });
    map.addLayer(poisLayer);

    personsLayer = L.layerGroup().addTo(map);

    // Load data
    loadTownlands();
    loadPOIs();

    // Map click for What Was Here
    map.on('click', onMapClick);

    // Build controls
    buildEraFilters();
    buildLayerControls();

    // Sidebar welcome
    showWelcome();
  }

  // ── TOWNLAND STYLE ──
  function townlandStyle() {
    return {
      color: '#c8941a',
      weight: 2,
      opacity: 0.8,
      fillColor: '#1a5c38',
      fillOpacity: 0.08,
      dashArray: '4 4'
    };
  }

  function townlandHighlight() {
    return {
      weight: 3,
      color: '#c8941a',
      fillOpacity: 0.18,
      dashArray: ''
    };
  }

  function onEachTownland(feature, layer) {
    var name = feature.properties.name || 'Unknown';
    var irish = feature.properties.name_irish;
    var label = irish ? name + ' / ' + irish : name;

    layer.bindTooltip(label, {
      className: 'townland-tooltip',
      sticky: true,
      direction: 'top'
    });

    layer.on({
      mouseover: function (e) {
        e.target.setStyle(townlandHighlight());
      },
      mouseout: function (e) {
        townlandsLayer.resetStyle(e.target);
      },
      click: function (e) {
        L.DomEvent.stopPropagation(e);
        showTownlandInfo(feature.properties);
      }
    });
  }

  // ── LOAD DATA ──
  function loadTownlands() {
    fetch('/api/map/townlands')
      .then(function (r) { return r.json(); })
      .then(function (geojson) {
        if (geojson.features && geojson.features.length > 0) {
          allTownlandsData = geojson;
          townlandsLayer.addData(geojson);
        } else {
          // Try static fallback
          fetch('/static/data/townlands.geojson')
            .then(function (r) { return r.json(); })
            .then(function (fallback) {
              allTownlandsData = fallback;
              townlandsLayer.addData(fallback);
            })
            .catch(function () {
              console.log('No townland boundary data available yet');
            });
        }
      })
      .catch(function (err) {
        console.error('Error loading townlands:', err);
      });
  }

  function loadPOIs(era) {
    var url = '/api/map/pois';
    if (era && era !== 'all') {
      url += '?era=' + encodeURIComponent(era);
    }

    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (geojson) {
        poisLayer.clearLayers();
        if (geojson.features) {
          geojson.features.forEach(function (feature) {
            var props = feature.properties;
            var coords = feature.geometry.coordinates;
            var iconChar = POI_ICONS[props.poi_type] || POI_ICONS.default;

            var icon = L.divIcon({
              html: '<span style="font-size:24px;filter:drop-shadow(0 1px 2px rgba(0,0,0,.4))">' + iconChar + '</span>',
              className: 'poi-marker',
              iconSize: [30, 30],
              iconAnchor: [15, 15],
              popupAnchor: [0, -15]
            });

            var marker = L.marker([coords[1], coords[0]], { icon: icon });

            var eraText = '';
            if (props.era_start) {
              eraText = props.era_start + (props.era_end ? '\u2013' + props.era_end : '\u2013present');
            }

            var popupHtml =
              '<h4>' + iconChar + ' ' + escapeHtml(props.name) + '</h4>' +
              (props.description ? '<p style="margin:4px 0;font-size:.88em">' + escapeHtml(props.description) + '</p>' : '') +
              '<div class="popup-meta">' +
                (props.townland ? '<span>' + escapeHtml(props.townland) + '</span>' : '') +
                (eraText ? ' &middot; <span>' + eraText + '</span>' : '') +
                ' &middot; <span>' + escapeHtml(props.poi_type) + '</span>' +
              '</div>' +
              '<span class="popup-link" onclick="CarrigMap.showPOIDetail(' + props.id + ')">View details &rarr;</span>';

            marker.bindPopup(popupHtml);
            marker.on('click', function () {
              showPOIDetail(props.id);
            });
            poisLayer.addLayer(marker);
          });
        }
      })
      .catch(function (err) {
        console.error('Error loading POIs:', err);
      });
  }

  // ── POI DETAIL ──
  function showPOIDetail(poiId) {
    var sidebar = document.getElementById('sidebar-body');
    sidebar.innerHTML = '<div class="loading-spinner">Loading...</div>';
    showSidebar('Point of Interest');

    fetch('/api/map/poi/' + poiId)
      .then(function (r) { return r.json(); })
      .then(function (poi) {
        if (poi.error) {
          sidebar.innerHTML = '<p>POI not found.</p>';
          return;
        }

        var iconChar = POI_ICONS[poi.poi_type] || POI_ICONS.default;
        var eraText = '';
        if (poi.era_start) {
          eraText = poi.era_start + (poi.era_end ? '\u2013' + poi.era_end : '\u2013present');
        }

        var html =
          '<div class="sidebar-section">' +
            '<h3>' + iconChar + ' ' + escapeHtml(poi.name) + '</h3>' +
            (poi.description ? '<p>' + escapeHtml(poi.description) + '</p>' : '') +
            '<p class="meta">' +
              '<span class="badge badge-type">' + escapeHtml(poi.poi_type) + '</span> ' +
              (poi.townland ? '<span class="badge badge-era">' + escapeHtml(poi.townland) + '</span> ' : '') +
              (eraText ? '<span class="badge badge-era">' + eraText + '</span>' : '') +
            '</p>' +
          '</div>';

        // Linked persons
        if (poi.linked_persons && poi.linked_persons.length > 0) {
          html += '<div class="sidebar-section"><h4>Connected Persons</h4><ul class="sidebar-list">';
          poi.linked_persons.forEach(function (p) {
            var dates = '';
            if (p.birth_year) dates = p.birth_year + (p.death_year ? '\u2013' + p.death_year : '');
            html += '<li><a href="/person/' + p.id + '">' + escapeHtml(p.name) + '</a>' +
              (dates ? ' <span class="meta">(' + dates + ')</span>' : '') +
              (p.relationship ? ' <span class="meta">\u2013 ' + escapeHtml(p.relationship) + '</span>' : '') +
              '</li>';
          });
          html += '</ul></div>';
        }

        // Linked articles
        if (poi.linked_articles && poi.linked_articles.length > 0) {
          html += '<div class="sidebar-section"><h4>Related Articles</h4><ul class="sidebar-list">';
          poi.linked_articles.forEach(function (a) {
            html += '<li><a href="/article/' + a.id + '">' + escapeHtml(a.title) + '</a>' +
              ' <span class="meta">' + escapeHtml(a.source) + '</span></li>';
          });
          html += '</ul></div>';
        }

        if (poi.source_url) {
          html += '<div class="sidebar-section"><a class="sidebar-link" href="' +
            escapeHtml(poi.source_url) + '" target="_blank">View source &rarr;</a></div>';
        }

        sidebar.innerHTML = html;
      })
      .catch(function () {
        sidebar.innerHTML = '<p>Error loading POI details.</p>';
      });
  }

  // ── TOWNLAND INFO ──
  function showTownlandInfo(props) {
    showSidebar('Townland');
    var sidebar = document.getElementById('sidebar-body');
    sidebar.innerHTML = '<div class="loading-spinner">Loading...</div>';

    fetch('/api/map/whatwashere?townland=' + encodeURIComponent(props.name) +
      (currentEra !== 'all' ? '&era=' + encodeURIComponent(currentEra) : ''))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var html = '<div class="sidebar-section">';
        html += '<h3>' + escapeHtml(props.name) + '</h3>';
        if (props.name_irish) {
          html += '<p style="font-style:italic;color:var(--muted)">' + escapeHtml(props.name_irish) + '</p>';
        }

        if (data.townland) {
          html += '<p class="meta">' +
            'Parish: ' + escapeHtml(data.townland.parish || 'Carrigtwohill') + ' &middot; ' +
            'Barony: ' + escapeHtml(data.townland.barony || 'Barrymore') +
            (data.townland.area_acres ? ' &middot; ' + data.townland.area_acres.toFixed(0) + ' acres' : '') +
            '</p>';
        }
        html += '</div>';

        // POIs in this townland
        if (data.pois && data.pois.length > 0) {
          html += '<div class="sidebar-section"><h4>Places of Interest</h4><ul class="sidebar-list">';
          data.pois.forEach(function (poi) {
            var iconChar = POI_ICONS[poi.poi_type] || POI_ICONS.default;
            html += '<li>' + iconChar + ' <a href="#" onclick="CarrigMap.showPOIDetail(' + poi.id + ');return false;">' +
              escapeHtml(poi.name) + '</a>' +
              ' <span class="meta">' + escapeHtml(poi.poi_type) + '</span></li>';
          });
          html += '</ul></div>';
        }

        // Persons from this townland
        if (data.persons && data.persons.length > 0) {
          html += '<div class="sidebar-section"><h4>Notable Persons</h4><ul class="sidebar-list">';
          data.persons.forEach(function (p) {
            var dates = '';
            if (p.birth_year) dates = p.birth_year + (p.death_year ? '\u2013' + p.death_year : '');
            html += '<li><a href="/person/' + p.id + '">' + escapeHtml(p.name) + '</a>' +
              (dates ? ' <span class="meta">(' + dates + ')</span>' : '') + '</li>';
          });
          html += '</ul></div>';
        }

        if (data.pois.length === 0 && data.persons.length === 0) {
          html += '<div class="sidebar-section"><p style="font-style:italic;color:var(--muted)">No records found for this townland' +
            (currentEra !== 'all' ? ' in the selected era' : '') + '.</p></div>';
        }

        sidebar.innerHTML = html;
      })
      .catch(function () {
        sidebar.innerHTML = '<p>Error loading townland data.</p>';
      });
  }

  // ── WHAT WAS HERE ──
  function onMapClick(e) {
    if (!wwhMode) return;
    if (!allTownlandsData || !allTownlandsData.features) return;
    if (typeof turf === 'undefined') return;

    var point = turf.point([e.latlng.lng, e.latlng.lat]);
    var found = null;

    for (var i = 0; i < allTownlandsData.features.length; i++) {
      var feature = allTownlandsData.features[i];
      try {
        if (turf.booleanPointInPolygon(point, feature)) {
          found = feature;
          break;
        }
      } catch (ex) {
        // Skip invalid geometries
      }
    }

    if (found) {
      showTownlandInfo(found.properties);
    } else {
      showSidebar('Location');
      var sidebar = document.getElementById('sidebar-body');
      sidebar.innerHTML =
        '<div class="sidebar-section">' +
          '<h3>Outside parish boundary</h3>' +
          '<p>This location is outside the Carrigtwohill civil parish.</p>' +
          '<p class="meta">Coordinates: ' + e.latlng.lat.toFixed(5) + ', ' + e.latlng.lng.toFixed(5) + '</p>' +
        '</div>';
    }
  }

  function toggleWWH() {
    wwhMode = !wwhMode;
    var btn = document.getElementById('wwh-btn');
    if (btn) {
      btn.classList.toggle('active', wwhMode);
      btn.textContent = wwhMode ? 'Click map to explore...' : 'What Was Here?';
    }
    if (wwhMode) {
      document.getElementById('map').style.cursor = 'crosshair';
    } else {
      document.getElementById('map').style.cursor = '';
    }
  }

  // ── ERA FILTERS ──
  function buildEraFilters() {
    var container = document.getElementById('era-filters');
    if (!container) return;

    Object.keys(ERA_LABELS).forEach(function (key) {
      var btn = document.createElement('button');
      btn.className = 'era-btn' + (key === 'all' ? ' active' : '');
      btn.textContent = ERA_LABELS[key];
      btn.setAttribute('data-era', key);
      btn.addEventListener('click', function () {
        currentEra = key;
        // Update active state
        container.querySelectorAll('.era-btn').forEach(function (b) {
          b.classList.toggle('active', b.getAttribute('data-era') === key);
        });
        loadPOIs(key);
      });
      container.appendChild(btn);
    });
  }

  // ── LAYER CONTROLS ──
  function buildLayerControls() {
    var container = document.getElementById('layer-controls');
    if (!container) return;

    var layers = [
      { id: 'townlands', label: 'Townland Boundaries', checked: true },
      { id: 'pois', label: 'Points of Interest', checked: true },
      { id: 'satellite', label: 'Satellite Imagery', checked: false },
      { id: 'historic25inch', label: 'Historic 25-inch Map', checked: false }
    ];

    layers.forEach(function (lyr) {
      var label = document.createElement('label');
      label.className = 'layer-option';
      var checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = lyr.checked;
      checkbox.addEventListener('change', function () {
        toggleLayer(lyr.id, this.checked);
      });
      label.appendChild(checkbox);
      label.appendChild(document.createTextNode(' ' + lyr.label));
      container.appendChild(label);
    });

    // Opacity slider for historic layer
    var opacityDiv = document.createElement('div');
    opacityDiv.className = 'opacity-control';
    opacityDiv.id = 'historic-opacity';
    opacityDiv.style.display = 'none';
    opacityDiv.innerHTML = '<span>Opacity</span><input type="range" min="0" max="100" value="60" id="opacity-slider">';
    container.appendChild(opacityDiv);

    var slider = document.getElementById('opacity-slider');
    if (slider) {
      slider.addEventListener('input', function () {
        var val = this.value / 100;
        Object.keys(overlays).forEach(function (key) {
          overlays[key].setOpacity(val);
        });
      });
    }
  }

  var overlays = {};

  function toggleOverlay(visible, key, url, opts) {
    if (visible) {
      if (overlays[key]) map.removeLayer(overlays[key]);
      overlays[key] = L.tileLayer(url, opts);
      overlays[key].addTo(map);
      // Show opacity slider
      var opCtrl = document.getElementById('historic-opacity');
      if (opCtrl) opCtrl.style.display = 'flex';
    } else {
      if (overlays[key]) {
        map.removeLayer(overlays[key]);
        delete overlays[key];
      }
      // Hide opacity if no overlays active
      if (Object.keys(overlays).length === 0) {
        var opCtrl2 = document.getElementById('historic-opacity');
        if (opCtrl2) opCtrl2.style.display = 'none';
      }
    }
  }

  function toggleLayer(layerId, visible) {
    switch (layerId) {
      case 'townlands':
        if (visible) map.addLayer(townlandsLayer);
        else map.removeLayer(townlandsLayer);
        break;
      case 'pois':
        if (visible) map.addLayer(poisLayer);
        else map.removeLayer(poisLayer);
        break;
      case 'satellite':
        toggleOverlay(visible, 'satellite',
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          { attribution: '&copy; <a href="https://www.esri.com">Esri</a>', maxZoom: 19, crossOrigin: 'anonymous' }
        );
        break;
      case 'historic25inch':
        // OSi 25-inch historic map via GeoHive/Tailte Eireann (public ArcGIS tile service)
        toggleOverlay(visible, 'historic25inch',
          'https://utility.arcgis.com/usrsvcs/servers/50c892d42a2c48c58d1767301b2fada9/rest/services/Historic_25inch_RasterTileServer/MapServer/tile/{z}/{y}/{x}',
          { attribution: '&copy; <a href="https://www.geohive.ie">Tailte \u00c9ireann / GeoHive</a>', maxZoom: 19, opacity: 0.7, crossOrigin: 'anonymous',
            errorTileUrl: '' }
        );
        break;
    }
  }

  // ── SIDEBAR MANAGEMENT ──
  function showSidebar(title) {
    var header = document.getElementById('sidebar-title');
    if (header) header.textContent = title || 'Details';
    var sidebar = document.querySelector('.map-sidebar');
    if (sidebar) sidebar.style.display = 'flex';
  }

  function showWelcome() {
    var sidebar = document.getElementById('sidebar-body');
    sidebar.innerHTML =
      '<div class="sidebar-welcome">' +
        '<div class="icon">\u{1F3F0}</div>' +
        '<p><strong>Carrigtwohill Parish</strong></p>' +
        '<p>Click a marker or townland boundary to explore the history of this area.</p>' +
        '<p style="margin-top:12px;font-size:.82em">Use <strong>"What Was Here?"</strong> to click anywhere on the map and discover its history.</p>' +
      '</div>';
  }

  function closeSidebar() {
    showWelcome();
  }

  // ── UTILITIES ──
  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── BOOT ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ── PUBLIC API ──
  window.CarrigMap = {
    showPOIDetail: showPOIDetail,
    toggleWWH: toggleWWH,
    closeSidebar: closeSidebar
  };

})();
