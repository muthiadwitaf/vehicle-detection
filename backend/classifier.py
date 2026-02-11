"""
classifier.py — Business-Level Vehicle Classification for Indonesian Traffic Monitoring

Maps generic YOLO detection classes (car, motorcycle, bus, truck, bicycle) into
a structured Indonesian vehicle taxonomy using rule-based heuristics (bbox size,
aspect ratio, relative frame coverage).

All sub-categories are ESTIMATED — fine-grained classification requires custom
model training on Indonesian vehicle datasets.
"""

# ============================================================================
# TAXONOMY DEFINITION
# ============================================================================

BUSINESS_CATEGORIES = {
    "private_motorized": {
        "label": "Kendaraan Pribadi",
        "icon": "🚗",
        "subcategories": {
            "passenger_car": "Mobil Penumpang",
            "motorcycle": "Sepeda Motor",
        }
    },
    "public_transport": {
        "label": "Angkutan Umum",
        "icon": "🚌",
        "subcategories": {
            "angkot": "Angkot",
            "city_bus": "Bus Kota",
            "intercity_bus": "Bus AKAP/AKDP",
        }
    },
    "freight": {
        "label": "Angkutan Barang",
        "icon": "🚚",
        "subcategories": {
            "pickup": "Pickup",
            "light_truck": "Truk Ringan (CDD)",
            "heavy_truck": "Truk Besar",
            "trailer": "Trailer",
        }
    },
    "special": {
        "label": "Kendaraan Khusus",
        "icon": "⚙️",
        "subcategories": {
            "special_vehicle": "Kendaraan Khusus",
        }
    },
    "non_motorized": {
        "label": "Tidak Bermotor",
        "icon": "🚲",
        "subcategories": {
            "bicycle": "Sepeda",
        }
    },
}

# Flat lookup: subcategory_id → (category_id, label)
_SUBCAT_LOOKUP = {}
for cat_id, cat in BUSINESS_CATEGORIES.items():
    for sub_id, sub_label in cat["subcategories"].items():
        _SUBCAT_LOOKUP[sub_id] = (cat_id, sub_label)


def empty_business_counts():
    """Return a fresh zero-filled business counts dict."""
    return {
        # Category totals
        "categories": {
            "private_motorized": 0,
            "public_transport": 0,
            "freight": 0,
            "special": 0,
            "non_motorized": 0,
        },
        # Sub-category totals
        "subcategories": {
            "passenger_car": 0,
            "motorcycle": 0,
            "angkot": 0,
            "city_bus": 0,
            "intercity_bus": 0,
            "pickup": 0,
            "light_truck": 0,
            "heavy_truck": 0,
            "trailer": 0,
            "special_vehicle": 0,
            "bicycle": 0,
        },
    }


# ============================================================================
# CLASSIFICATION LOGIC
# ============================================================================

def classify_detection(det, frame_width, frame_height):
    """
    Classify a single YOLO detection into a business sub-category.

    Args:
        det: dict with keys class_name, x1, y1, x2, y2
        frame_width: width of the video frame in pixels
        frame_height: height of the video frame in pixels

    Returns:
        tuple: (category_id, subcategory_id)
    """
    cls = det["class_name"]
    x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]

    bbox_w = x2 - x1
    bbox_h = y2 - y1
    bbox_area = bbox_w * bbox_h
    frame_area = frame_width * frame_height

    # Fraction of frame covered by the bounding box
    coverage = bbox_area / frame_area if frame_area > 0 else 0
    aspect = bbox_w / bbox_h if bbox_h > 0 else 1.0

    if cls == "car":
        return "private_motorized", "passenger_car"

    elif cls == "motorcycle":
        return "private_motorized", "motorcycle"

    elif cls == "bus":
        # Heuristic: small bus → angkot, large → city/intercity
        if coverage < 0.08:
            return "public_transport", "angkot"
        elif coverage < 0.20:
            return "public_transport", "city_bus"
        else:
            return "public_transport", "intercity_bus"

    elif cls == "truck":
        # Heuristic by bbox coverage of frame
        if coverage < 0.05:
            return "freight", "pickup"
        elif coverage < 0.12:
            return "freight", "light_truck"
        elif coverage < 0.25:
            return "freight", "heavy_truck"
        else:
            return "freight", "trailer"

    elif cls == "bicycle":
        return "non_motorized", "bicycle"

    else:
        return "special", "special_vehicle"


def classify_frame_detections(detections, frame_width, frame_height):
    """
    Classify all detections in a single frame.

    Returns:
        list of dicts, each with added keys: category, subcategory
    """
    enriched = []
    for det in detections:
        cat_id, subcat_id = classify_detection(det, frame_width, frame_height)
        enriched.append({
            **det,
            "category": cat_id,
            "subcategory": subcat_id,
        })
    return enriched


def accumulate_business_counts(business_counts, enriched_detections):
    """
    Add enriched detections to running business counts (in-place).
    """
    for det in enriched_detections:
        cat = det["category"]
        sub = det["subcategory"]
        business_counts["categories"][cat] = business_counts["categories"].get(cat, 0) + 1
        business_counts["subcategories"][sub] = business_counts["subcategories"].get(sub, 0) + 1


def get_taxonomy_metadata():
    """Return category/subcategory labels and icons for the frontend."""
    return BUSINESS_CATEGORIES
