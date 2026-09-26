"""
Dynamic Layout & Micro-Zoning Planner Engine
Generates high-impact whiteboard layouts with adaptive scaling, micro-zones (2-3 elements),
consistent horizontal camera tracks (Y=800.0 constant), and prominent element sizing (35%-45% canvas height).
"""
import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

class DynamicLayoutPlanner:
    def __init__(self, section_dir, fixed_y=800.0, cam_zoom=0.68):
        self.section_dir = section_dir
        self.fixed_y = fixed_y
        self.cam_zoom = cam_zoom
        self.meta_path = os.path.join(section_dir, "assets", "metadata.json")
        self.layout_path = os.path.join(section_dir, "placed_elements_layout.json")

    def plan_layout(self, manifest_items):
        """
        Plans horizontal placement across micro-zones and outputs placed_elements_layout.json.
        manifest_items: list of (aid, st, en, desc, zone_name, anim_type, depth)
        """
        with open(self.meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Group elements by zone preserving order
        zone_order = []
        zone_elements = {}
        for item in manifest_items:
            aid = item[0]
            z_name = item[4]
            if z_name not in zone_elements:
                zone_elements[z_name] = []
                zone_order.append(z_name)
            zone_elements[z_name].append(aid)

        placed_elements = {}
        zones_dict = {}

        cur_zone_x = 600.0
        for z_name in zone_order:
            aids = zone_elements[z_name]
            placed_elements[z_name] = []
            num_elems = len(aids)

            # Adaptive prominent scaling
            if z_name == "zone_01":
                elem_scale = 3.8
                spacing = 100.0
            elif num_elems <= 2:
                elem_scale = 3.8
                spacing = 140.0
            elif num_elems == 3:
                elem_scale = 3.4
                spacing = 100.0
            else:
                elem_scale = 3.0
                spacing = 80.0

            cur_x = cur_zone_x
            for aid in aids:
                meta = metadata.get(aid, {})
                orig_size = meta.get("orig_size", [150, 150])

                if aid == "r0_00_title_banner":
                    w_px = 1100.0
                    h_px = 242.0
                    x_px = cur_zone_x + 100.0
                    y_px = 180.0
                elif z_name == "zone_01" and aid != "r0_00_title_banner":
                    w_px = float(orig_size[0]) * elem_scale
                    h_px = float(orig_size[1]) * elem_scale
                    x_px = cur_zone_x + 150.0
                    y_px = 880.0 - (h_px / 2.0)
                    cur_x = max(cur_x, x_px + w_px + spacing)
                else:
                    w_px = float(orig_size[0]) * elem_scale
                    h_px = float(orig_size[1]) * elem_scale
                    y_px = self.fixed_y - (h_px / 2.0)
                    x_px = cur_x
                    cur_x += w_px + spacing

                placed_elements[z_name].append({
                    "aid": aid,
                    "file": f"{aid}.png",
                    "x": round(x_px, 1),
                    "y": round(y_px, 1),
                    "w": round(w_px, 1),
                    "h": round(h_px, 1),
                    "cx": round(x_px + w_px / 2.0, 1),
                    "cy": round(y_px + h_px / 2.0, 1),
                    "zone": z_name
                })

            non_banner = [e for e in placed_elements[z_name] if e["aid"] != "r0_00_title_banner"]
            if non_banner:
                min_x = min(e["x"] for e in non_banner)
                max_x = max(e["x"] + e["w"] for e in non_banner)
                mid_x = (min_x + max_x) / 2.0
            else:
                mid_x = cur_zone_x + 650.0

            if z_name == "zone_01":
                for el in placed_elements[z_name]:
                    if el["aid"] == "r0_00_title_banner":
                        el["x"] = round(mid_x - (el["w"] / 2.0), 1)
                        el["cx"] = round(mid_x, 1)

            zones_dict[z_name] = {
                "cam_pos": [round(mid_x, 1), self.fixed_y],
                "zoom": self.cam_zoom
            }

            cur_zone_x = max(cur_x, mid_x + 1200.0) + 1600.0

        layout_data = {
            "section_id": os.path.basename(self.section_dir),
            "fixed_y": self.fixed_y,
            "cam_zoom": self.cam_zoom,
            "zones": zones_dict,
            "elements": placed_elements
        }

        with open(self.layout_path, "w", encoding="utf-8") as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Layout planned with {len(zone_order)} micro-zones saved to: {self.layout_path}")
        return layout_data
