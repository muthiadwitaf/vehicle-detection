# Vehicle Classification Taxonomy
## Business-Level Vehicle Classification for Indonesian Traffic Monitoring

**Document Type:** Technical Design Document  
**Version:** 1.0  
**Status:** Design Specification  

---

## 1. Executive Summary

This document defines a structured vehicle classification taxonomy designed for traffic monitoring systems in Indonesia. It establishes a clear separation between **AI Detection Classes** (model output) and **Business Categories** (dashboard presentation), enabling realistic implementation while acknowledging technical constraints.

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VIDEO INPUT                                  │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AI DETECTION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  YOLOv8 / YOLO-NAS (COCO Pretrained)                        │    │
│  │  Generic Classes: car, motorcycle, bus, truck, bicycle      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  CLASSIFICATION MAPPING LAYER                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Rule-Based Mapping + Contextual Logic                       │    │
│  │  Size Estimation | Color Analysis | Regional Context         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   BUSINESS CATEGORY LAYER                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Indonesian Vehicle Taxonomy (5 Categories, 25+ Subtypes)   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DASHBOARD OUTPUT                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Indonesian Vehicle Classification Taxonomy

### 3.1 Category Overview

| Code | Category | Description | Subtypes |
|------|----------|-------------|----------|
| **PMV** | Private Motorized | Personal vehicles for private use | 7 |
| **PTV** | Public Transport | Commercial passenger transport | 6 |
| **FTV** | Freight Transport | Goods and cargo hauling | 6 |
| **SPV** | Special Vehicles | Industrial, agricultural, military | 4 |
| **NMV** | Non-Motorized | Human/animal powered vehicles | 4 |

---

### 3.2 Detailed Classification Table

#### 🚗 PMV - Private Motorized Vehicles

| Subcode | Indonesian Term | English | AI Detection | Mapping Confidence |
|---------|-----------------|---------|--------------|-------------------|
| PMV-01 | Sedan | Sedan | car | ⚠️ Medium |
| PMV-02 | Hatchback | Hatchback | car | ⚠️ Medium |
| PMV-03 | MPV | Multi-Purpose Vehicle | car | ⚠️ Medium |
| PMV-04 | SUV | Sport Utility Vehicle | car | ⚠️ Medium |
| PMV-05 | Motor Bebek | Underbone Motorcycle | motorcycle | ❌ Low |
| PMV-06 | Motor Matic | Automatic Scooter | motorcycle | ❌ Low |
| PMV-07 | Motor Sport | Sport Motorcycle | motorcycle | ❌ Low |

---

#### 🚌 PTV - Public Transport Vehicles

| Subcode | Indonesian Term | English | AI Detection | Mapping Confidence |
|---------|-----------------|---------|--------------|-------------------|
| PTV-01 | Angkot | Minibus (Public) | car/bus | ⚠️ Medium |
| PTV-02 | Bus Kota | City Bus | bus | ✅ High |
| PTV-03 | Bus AKAP/AKDP | Intercity Bus | bus | ✅ High |
| PTV-04 | Taksi | Taxi | car | ❌ Low* |
| PTV-05 | Ojek | Motorcycle Taxi | motorcycle | ❌ Low* |
| PTV-06 | Bajaj | Three-Wheeler | motorcycle | ⚠️ Medium |

*Requires color/livery detection or ride-hailing API integration

---

#### 🚚 FTV - Freight Transport Vehicles

| Subcode | Indonesian Term | English | AI Detection | Mapping Confidence |
|---------|-----------------|---------|--------------|-------------------|
| FTV-01 | Pickup | Pickup Truck | truck | ⚠️ Medium |
| FTV-02 | Engkel/CDD | Light Truck | truck | ⚠️ Medium |
| FTV-03 | Truk Sedang | Medium Truck | truck | ⚠️ Medium |
| FTV-04 | Truk Besar | Heavy Truck | truck | ⚠️ Medium |
| FTV-05 | Truk Box | Box Truck | truck | ⚠️ Medium |
| FTV-06 | Trailer | Articulated Truck | truck | ✅ High |
| FTV-07 | Truk Tangki | Tank Truck | truck | ⚠️ Medium |

---

#### 🚜 SPV - Special Vehicles

| Subcode | Indonesian Term | English | AI Detection | Mapping Confidence |
|---------|-----------------|---------|--------------|-------------------|
| SPV-01 | Alat Berat | Heavy Equipment | truck* | ❌ Low |
| SPV-02 | Forklift | Forklift | truck* | ❌ Low |
| SPV-03 | Traktor | Agricultural Tractor | truck* | ❌ Low |
| SPV-04 | Kendaraan Militer | Military Vehicle | truck/car | ❌ Low |

*COCO model has no specific class for these vehicles

---

#### 🚲 NMV - Non-Motorized Vehicles

| Subcode | Indonesian Term | English | AI Detection | Mapping Confidence |
|---------|-----------------|---------|--------------|-------------------|
| NMV-01 | Sepeda | Bicycle | bicycle | ✅ High |
| NMV-02 | Becak | Pedicab | bicycle* | ⚠️ Medium |
| NMV-03 | Andong/Delman | Horse Cart | - | ❌ None |
| NMV-04 | Gerobak | Hand Cart | - | ❌ None |

*May be detected as bicycle due to similar features

---

## 4. AI Detection vs Business Layer

### 4.1 Detection Layer (Model Output)

The AI detection layer uses pretrained models that recognize **generic COCO classes**:

| COCO Class | COCO ID | Detectable | Notes |
|------------|---------|------------|-------|
| car | 2 | ✅ Yes | No body type distinction |
| motorcycle | 3 | ✅ Yes | No engine type distinction |
| bus | 5 | ✅ Yes | No size distinction |
| truck | 7 | ✅ Yes | No cargo type distinction |
| bicycle | 1 | ✅ Yes | Includes pedicabs |

**Key Limitation:** Pretrained models output only **5 vehicle-related classes**. They cannot distinguish between:
- Sedan vs SUV vs Taxi
- Bebek vs Matic vs Sport motorcycle
- City bus vs Intercity bus
- Light truck vs Heavy truck

---

### 4.2 Business Layer (Dashboard Output)

The business layer presents **Indonesian-specific categories** to end users:

```
Dashboard Display Example:
┌────────────────────────────────────────────────┐
│           TRAFFIC COMPOSITION                  │
├────────────────────────────────────────────────┤
│  Private Motorized    │████████████│ 45%       │
│  Public Transport     │████        │ 18%       │
│  Freight Transport    │██████      │ 25%       │
│  Special Vehicles     │█           │  4%       │
│  Non-Motorized        │██          │  8%       │
└────────────────────────────────────────────────┘
```

---

## 5. Mapping Strategy

### 5.1 Direct Mapping (High Confidence)

| AI Output | Business Category | Condition |
|-----------|-------------------|-----------|
| bus | PTV (Public Transport) | Default |
| bicycle | NMV (Non-Motorized) | Default |
| truck (large bbox) | FTV-06 Trailer | Bounding box width > threshold |

### 5.2 Contextual Mapping (Medium Confidence)

| AI Output | Business Category | Context Required |
|-----------|-------------------|------------------|
| car | PMV (Private) | Default assumption |
| car | PTV-04 (Taxi) | Yellow/blue color detected |
| car | PTV-01 (Angkot) | Green/orange + small bus shape |
| motorcycle | PMV-05/06/07 | Cannot distinguish type |
| motorcycle | PTV-05 (Ojek) | Green jacket detected (future) |

### 5.3 Size-Based Mapping (Freight Vehicles)

| AI Output | Bounding Box Size | Business Category |
|-----------|-------------------|-------------------|
| truck | Small (< 20% frame) | FTV-01 Pickup |
| truck | Medium (20-40% frame) | FTV-02/03 Light-Medium Truck |
| truck | Large (> 40% frame) | FTV-04/06 Heavy/Trailer |

---

## 6. Implementation Approach

### 6.1 Phase 1: Current Implementation ✅

**Status:** Deployed

| Feature | Implementation |
|---------|----------------|
| AI Detection | YOLOv8 Nano (COCO pretrained) |
| Classes | 4 generic classes (car, motorcycle, bus, truck) |
| Mapping | Direct 1:1 to business categories |
| Dashboard | Generic vehicle counts |

### 6.2 Phase 2: Enhanced Mapping 📋

**Status:** Planned

| Feature | Implementation |
|---------|----------------|
| Size Estimation | Bounding box analysis for truck subclasses |
| Aspect Ratio | Distinguish bus types by shape |
| Rule Engine | JSON-based mapping rules |

### 6.3 Phase 3: Fine-Tuned Model 🔮

**Status:** Future Enhancement

| Feature | Implementation |
|---------|----------------|
| Custom Dataset | Indonesian vehicle images |
| Fine-Tuning | YOLOv8 training on local classes |
| New Classes | Angkot, Bajaj, Becak, etc. |

---

## 7. Limitations & Constraints

### 7.1 Current Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No fine-grained car types | Cannot distinguish sedan/SUV/MPV | Treat all as "Private Car" |
| No motorcycle subtypes | Cannot distinguish bebek/matic/sport | Treat all as "Motorcycle" |
| No taxi detection | Cannot identify taxis | Placeholder for color analysis |
| No ojek detection | Cannot identify motorcycle taxis | Requires ride-hailing integration |
| No becak class | Detected as bicycle | Aspect ratio analysis (future) |
| No andong/gerobak | Not detectable | Requires custom training |

### 7.2 Accuracy Expectations

| Category | Expected Accuracy | Notes |
|----------|-------------------|-------|
| Existence Detection | 85-95% | "Is there a vehicle?" |
| Generic Classification | 75-85% | "Is it car/motorcycle/bus/truck?" |
| Business Subcategory | 40-60% | "Is it sedan or SUV?" |
| Specific Indonesian Type | 20-30% | "Is it angkot or taxi?" |

---

## 8. Recommendation

For production deployment of Indonesian traffic monitoring:

1. **Short Term:** Use current 4-class detection with business category rollup
2. **Medium Term:** Implement size-based rules for truck subclassification  
3. **Long Term:** Collect Indonesian vehicle dataset and fine-tune custom model

---

## Appendix A: COCO to Indonesian Mapping Table

```
┌──────────────┬────────────────────┬─────────────────────────────────┐
│ COCO Class   │ Default Mapping    │ Potential Mappings              │
├──────────────┼────────────────────┼─────────────────────────────────┤
│ car          │ PMV (Private)      │ PTV-01 Angkot (context)         │
│              │                    │ PTV-04 Taxi (color)             │
├──────────────┼────────────────────┼─────────────────────────────────┤
│ motorcycle   │ PMV-05/06/07       │ PTV-05 Ojek (context)           │
│              │                    │ PTV-06 Bajaj (3-wheel shape)    │
├──────────────┼────────────────────┼─────────────────────────────────┤
│ bus          │ PTV-02/03          │ Size-based city/intercity split │
├──────────────┼────────────────────┼─────────────────────────────────┤
│ truck        │ FTV (Freight)      │ Size-based subclassification    │
│              │                    │ SPV (if unusual shape)          │
├──────────────┼────────────────────┼─────────────────────────────────┤
│ bicycle      │ NMV-01 Bicycle     │ NMV-02 Becak (aspect ratio)     │
└──────────────┴────────────────────┴─────────────────────────────────┘
```

---

*Document End*
