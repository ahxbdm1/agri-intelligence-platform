"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import type { Farm } from "@/types/api";

const colors: Record<string, string> = {
  高: "#f16d73",
  中: "#f7bd57",
  低: "#42d99a"
};

function buildPopup(farm: Farm) {
  const wrapper = document.createElement("div");
  wrapper.style.minWidth = "190px";
  const title = document.createElement("div");
  title.style.fontWeight = "600";
  title.style.color = "#effcf7";
  title.textContent = farm.name;
  const meta = document.createElement("div");
  meta.style.cssText = "margin-top:6px;font-size:12px;color:#8ba8a2";
  meta.textContent = `${farm.town} · ${farm.crop} · ${farm.area_mu}亩`;
  const score = document.createElement("div");
  score.style.cssText = "margin-top:10px;padding:7px 9px;border:1px solid rgba(151,206,194,.12);border-radius:5px;background:rgba(255,255,255,.035);font-size:12px";
  score.textContent = `当前风险评分 ${farm.current_risk_score}`;
  wrapper.append(title, meta, score);
  return wrapper;
}

export function RiskMap({ farms, onSelect }: { farms: Farm[]; onSelect: (farm: Farm) => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layersRef = useRef<L.LayerGroup | null>(null);
  const selectRef = useRef(onSelect);

  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || mapRef.current) return;

    const map = L.map(container, { zoomControl: true, attributionControl: true }).setView([34.99, 116.68], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 18
    }).addTo(map);
    const layers = L.layerGroup().addTo(map);
    mapRef.current = map;
    layersRef.current = layers;

    const resizeObserver = new ResizeObserver(() => map.invalidateSize({ animate: false }));
    resizeObserver.observe(container);
    const timer = window.setTimeout(() => map.invalidateSize({ animate: false }), 120);

    return () => {
      window.clearTimeout(timer);
      resizeObserver.disconnect();
      layers.clearLayers();
      map.remove();
      mapRef.current = null;
      layersRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layers = layersRef.current;
    if (!map || !layers) return;
    layers.clearLayers();

    const bounds: L.LatLngExpression[] = [];
    farms.forEach((farm) => {
      const color = colors[farm.risk_level] || "#47d7dd";
      const polygon = L.polygon(farm.polygon, {
        color,
        fillColor: color,
        fillOpacity: 0.28,
        opacity: 0.92,
        weight: 1.5
      }).addTo(layers);
      polygon.bindPopup(buildPopup(farm));
      polygon.on("click", () => selectRef.current(farm));

      const marker = L.circleMarker([farm.lat, farm.lng], {
        radius: 4,
        color: "#dffbf3",
        fillColor: color,
        fillOpacity: 0.95,
        weight: 1
      }).addTo(layers);
      marker.on("click", () => selectRef.current(farm));
      bounds.push([farm.lat, farm.lng]);
    });

    if (bounds.length > 1) map.fitBounds(L.latLngBounds(bounds), { padding: [28, 28], maxZoom: 13, animate: false });
    if (bounds.length === 1) map.setView(bounds[0], 13, { animate: false });
  }, [farms]);

  return <div ref={containerRef} className="h-full w-full" aria-label="县域农田风险地图" />;
}
