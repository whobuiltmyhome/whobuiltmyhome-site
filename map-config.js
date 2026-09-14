// Background-map provider only. Property matching and filtering stay local.
// OSM's public tiles are best-effort, with attribution and normal browser caching.
export const mapConfig = Object.freeze({
  tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
  maxZoom: 19,
});
