[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=flat&logo=github&logoColor=white)](https://github.com/mz-analytics/vrp-logistics-optimizer)
# 🚚 Vehicle Routing Problem (VRP) Logistics Optimizer

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![OSMnx](https://img.shields.io/badge/OSMnx-GIS%20Routing-blue?style=flat)
![NetworkX](https://img.shields.io/badge/NetworkX-Graph%20Theory-orange?style=flat)
![Folium](https://img.shields.io/badge/Folium-Interactive%20Maps-77B829?style=flat&logo=leaflet&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

Capacitated Vehicle Routing Problem (CVRP) solver with fleet capacity and travel-time constraints, optimized over real-world road networks (Warsaw, Poland).

---

## 🗺️ Visual Results

### Input: Retail Distribution Network (50 Nodes + Depot)
![Distribution Network](cvrp_nodes.jpg)

### Output: Optimized Vehicle Routes (Tabu Search)
![Optimized Routes](f569ac65-8385-4844-b01d-f927a254421a.jpg)

---

## ⚙️ Key Features
* **Real-World Graph Engine:** Street network topology extraction and traversal using `OSMnx` & `NetworkX`.
* **Heuristic Routing:** Nearest Neighbor (NN), Sweep Algorithm, Clarke-Wright Savings (CW).
* **Metaheuristic Optimization:** Tabu Search (Relocate, Swap, 2-opt moves) with dynamic tenure.
* **GIS Visualizations:** Multi-layer interactive HTML route maps generated with `Folium`.

---

## 📊 Benchmark Comparison

| Strategy | Fleet Distance | Travel Time Compliance (< 4.0h) |
| :--- | :---: | :---: |
| **Tabu Search + Clarke-Wright** | **Optimal** | **100% OK** |
| **Tabu Search + Sweep** | +4.2% | 100% OK |
| **Tabu Search + Nearest Neighbor** | +8.1% | 100% OK |

---

## 🚀 Installation & Usage

### 1. Clone repository & install dependencies:
```bash
git clone [https://github.com/mz-analytics/vrp-logistics-optimizer.git](https://github.com/mz-analytics/vrp-logistics-optimizer.git)
cd vrp-logistics-optimizer
pip install -r requirements.txt
# Vehicle Routing Problem (VRP) Logistics Optimizer

Optimization tool solving multi-vehicle routing problems with capacity and driving time constraints using real road networks.

# Features
- Real-world road routing with `OSMnx` and `NetworkX` (Warsaw network).
- Heuristics: Nearest Neighbor (NN), Sweep, Clarke-Wright (CW).
- Metaheuristic: Tabu Search (Relocate, Swap, 2-opt).
- Interactive route maps generated with `Folium`.

# Tech Stack
`Python` `OSMnx` `NetworkX` `Folium`
