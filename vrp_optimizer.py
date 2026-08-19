import math
import os
import random
import csv
from collections import defaultdict
import osmnx as ox
import networkx as nx
import folium

# Magazyn + 50 punktow
ALL_POINTS = [
    (0, 52.2154162, 20.9613842),
    (1, 52.2310, 21.1500), (2, 52.15404, 21.0738861), (3, 52.2024, 20.9658),
    (4, 52.2774572, 21.0857759), (5, 52.2050, 21.1760), (6, 52.2678, 21.1558),
    (7, 52.1295516, 21.0572439), (8, 52.2413, 21.1827), (9, 52.2433, 21.1004),
    (10, 52.2651328, 20.9905943), (11, 52.2254483, 21.0389501), (12, 52.2648, 21.1358),
    (13, 52.1639749, 20.9313646), (14, 52.2761, 21.1501), (15, 52.2396894, 21.0295861),
    (16, 52.2739, 21.1620), (17, 52.1474, 21.0452), (18, 52.1650, 20.9207),
    (19, 52.1514452, 21.0060388), (20, 52.1451048, 21.0184316), (21, 52.2065635, 21.0631386),
    (22, 52.1697503, 21.0746016), (23, 52.2751786, 21.1173748), (24, 52.1921, 20.9983),
    (25, 52.2593244, 21.1613127), (26, 52.2636, 21.1771), (27, 52.2775, 21.0412),
    (28, 52.2788, 21.1456), (29, 52.2021808, 21.0471747), (30, 52.2274, 21.1033),
    (31, 52.1917862, 20.9185965), (32, 52.1682, 21.0792), (33, 52.1599122, 20.9926071),
    (34, 52.1334063, 21.0744757), (35, 52.2443844, 21.1347033), (36, 52.2036, 21.1583),
    (37, 52.2139, 20.9486), (38, 52.2022, 20.9297), (39, 52.150644, 21.1888858),
    (40, 52.1886, 20.9908), (41, 52.2594713, 21.1570143), (42, 52.2921909, 21.0805996),
    (43, 52.2607, 21.1142), (44, 52.1417225, 21.0462337), (45, 52.2740146, 21.0631625),
    (46, 52.1935529, 20.9387009), (47, 52.2521, 21.1190), (48, 52.1667647, 21.1084379),
    (49, 52.2747277, 20.9658828), (50, 52.2897952, 21.0707694)
]

DEPOT_ID = 0
DEPOT_LAT, DEPOT_LON = ALL_POINTS[0][1], ALL_POINTS[0][2]

# Parametry
MAX_TRUCKS = 5
CAPACITY = 10
AVG_SPEED_KMH = 33.5
TIME_WINDOW_H = 4.0
ALGO = "compare-ts"

# Tabu search
MAX_ITERS = 800
MAX_NO_IMPROVE = 120
TABU_TENURE_BASE = 12
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

def build_graph(cache_file="warsaw_drive.graphml"):
    if os.path.exists(cache_file):
        print(f"Wczytywanie grafu z pliku: {cache_file}")
        return ox.load_graphml(cache_file)
    print("Pobieranie sieci drogowej (Warszawa)...")
    G = ox.graph_from_place("Warsaw, Poland", network_type="drive")
    ox.save_graphml(G, cache_file)
    return G

def map_points_to_nodes(G, points):
    return {pid: ox.distance.nearest_nodes(G, X=lon, Y=lat) for pid, lat, lon in points}

def compute_network_distance_matrix_km(G, id2node, ids):
    dist = {}
    nodes = {pid: id2node[pid] for pid in ids}
    for i in ids:
        lengths_m = nx.single_source_dijkstra_path_length(G, nodes[i], weight="length")
        for j in ids:
            if i == j:
                dist[(i, j)] = 0.0
            else:
                d_m = lengths_m.get(nodes[j])
                if d_m is None:
                    lat1, lon1 = next((la, lo) for pid, la, lo in ALL_POINTS if pid == i)
                    lat2, lon2 = next((la, lo) for pid, la, lo in ALL_POINTS if pid == j)
                    R = 6371.0
                    d_lat = math.radians(lat2 - lat1)
                    d_lon = math.radians(lon2 - lon1)
                    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(d_lon/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    dist[(i, j)] = R * c
                else:
                    dist[(i, j)] = d_m / 1000.0
    return dist

def route_drive_km(route, dist_km):
    if not route:
        return 0.0
    s = dist_km[(DEPOT_ID, route[0])]
    for a, b in zip(route, route[1:]):
        s += dist_km[(a, b)]
    s += dist_km[(route[-1], DEPOT_ID)]
    return s

def route_drive_time_h(route, dist_km):
    return route_drive_km(route, dist_km) / AVG_SPEED_KMH

def feasible_route(route, dist_km):
    return len(route) <= CAPACITY and route_drive_time_h(route, dist_km) <= TIME_WINDOW_H

def total_km(routes, dist_km):
    return sum(route_drive_km(r, dist_km) for r in routes)

def cover_ok(routes):
    served = sorted(x for r in routes for x in r)
    return served == list(range(1, 51))

def two_opt(route, dist_km):
    best = route[:]
    best_cost = route_drive_km(best, dist_km)
    n = len(best)
    improved = True
    while improved:
        improved = False
        for i in range(n-2):
            for j in range(i+2, n):
                cand = best[:i+1] + best[i+1:j+1][::-1] + best[j+1:]
                c = route_drive_km(cand, dist_km)
                if c + 1e-9 < best_cost:
                    best, best_cost, improved = cand, c, True
    return best

def nn_initial(dist_km):
    customers = set(range(1, 51))
    cur = min(customers, key=lambda p: dist_km[(DEPOT_ID, p)])
    giant = [cur]
    customers.remove(cur)
    while customers:
        nxt = min(customers, key=lambda p: dist_km[(cur, p)])
        giant.append(nxt)
        customers.remove(nxt)
        cur = nxt
    blocks = [giant[i:i+CAPACITY] for i in range(0, len(giant), CAPACITY)]
    routes = [two_opt(b, dist_km) for b in blocks[:MAX_TRUCKS]]
    for i, r in enumerate(routes):
        if route_drive_time_h(r, dist_km) > TIME_WINDOW_H and len(r) >= 3:
            best_r, best_t = r, route_drive_time_h(r, dist_km)
            for k in range(1, len(r)):
                cand = two_opt(r[k:] + r[:k], dist_km)
                t = route_drive_time_h(cand, dist_km)
                if t + 1e-9 < best_t:
                    best_r, best_t = cand, t
            routes[i] = best_r
    return routes

def polar_angle(lat, lon):
    dx, dy = lon - DEPOT_LON, lat - DEPOT_LAT
    a = math.atan2(dy, dx)
    return a if a >= 0 else a + 2*math.pi

def sweep_initial(dist_km):
    id2coord = {pid: (lat, lon) for pid, lat, lon in ALL_POINTS}
    customers = list(range(1, 51))
    by_angle = sorted(customers, key=lambda p: polar_angle(*id2coord[p]))
    groups, cur = [], []
    for p in by_angle:
        if len(cur) < CAPACITY:
            cur.append(p)
        else:
            groups.append(cur)
            cur = [p]
    if cur:
        groups.append(cur)
    groups = groups[:MAX_TRUCKS]

    def tsp_nn(group):
        start = min(group, key=lambda p: dist_km[(DEPOT_ID, p)])
        unv = set(group)
        unv.remove(start)
        r, c = [start], start
        while unv:
            nxt = min(unv, key=lambda p: dist_km[(c, p)])
            r.append(nxt)
            unv.remove(nxt)
            c = nxt
        return r

    routes = []
    for g in groups:
        r = two_opt(tsp_nn(g), dist_km)
        if route_drive_time_h(r, dist_km) > TIME_WINDOW_H and len(r) >= 3:
            best_r, best_t = r, route_drive_time_h(r, dist_km)
            for k in range(1, len(r)):
                cand = two_opt(r[k:] + r[:k], dist_km)
                t = route_drive_time_h(cand, dist_km)
                if t + 1e-9 < best_t:
                    best_r, best_t = cand, t
            r = best_r
        routes.append(r)
    return routes

def cw_initial(dist_km):
    customers = list(range(1, 51))
    routes = {c: [c] for c in customers}
    route_of = {c: c for c in customers}
    savings = []
    for i in customers:
        for j in customers:
            if i < j:
                savings.append((dist_km[(DEPOT_ID, i)] + dist_km[(DEPOT_ID, j)] - dist_km[(i, j)], i, j))
    savings.sort(reverse=True, key=lambda x: x[0])

    def try_merge(A, B):
        for m in (A+B, B+A, A+list(reversed(B)), list(reversed(A))+B):
            if feasible_route(m, dist_km):
                return m
        return None

    for s, i, j in savings:
        Ai, Aj = route_of[i], route_of[j]
        if Ai == Aj:
            continue
        A, B = routes[Ai], routes[Aj]
        if (i not in (A[0], A[-1])) or (j not in (B[0], B[-1])):
            continue
        m = try_merge(A, B)
        if m is None:
            continue
        new_id = max(routes.keys(), default=0) + 1
        routes[new_id] = m
        for k in m:
            route_of[k] = new_id
        del routes[Ai]
        del routes[Aj]

    work = [r[:] for r in routes.values()]
    def best_pair(work):
        best_gain, best = -1e9, None
        for a in range(len(work)):
            for b in range(a+1, len(work)):
                r1, r2 = work[a], work[b]
                if len(r1)+len(r2) > CAPACITY:
                    continue
                for m in (r1+r2, r2+r1, r1+list(reversed(r2)), list(reversed(r1))+r2):
                    if feasible_route(m, dist_km):
                        gain = route_drive_km(r1, dist_km) + route_drive_km(r2, dist_km) - route_drive_km(m, dist_km)
                        if gain > best_gain:
                            best_gain, best = gain, (a, b, m)
        return best

    while len(work) > MAX_TRUCKS:
        pick = best_pair(work)
        if pick is None:
            break
        a, b, m = pick
        work = [r for i, r in enumerate(work) if i not in (a, b)] + [m]
    return work

def relocate_moves(routes, dist_km):
    K = len(routes)
    for r1 in range(K):
        for i in range(len(routes[r1])):
            cust = routes[r1][i]
            for r2 in range(K):
                for pos in range(0, len(routes[r2]) + (0 if r2 == r1 else 1)):
                    if r1 == r2 and (pos == i or pos == i+1):
                        continue
                    new = [rt[:] for rt in routes]
                    new[r1].pop(i)
                    if len(new[r1]) == 0:
                        continue
                    if r2 == r1:
                        insert_pos = pos if pos <= i else pos-1
                        new[r1].insert(insert_pos, cust)
                    else:
                        if len(new[r2]) + 1 > CAPACITY:
                            continue
                        new[r2].insert(pos, cust)
                    if route_drive_time_h(new[r1], dist_km) <= TIME_WINDOW_H and route_drive_time_h(new[r2], dist_km) <= TIME_WINDOW_H:
                        yield ("relocate", cust), new

def swap_moves(routes, dist_km):
    K = len(routes)
    for a in range(K):
        for b in range(a+1, K):
            for i in range(len(routes[a])):
                for j in range(len(routes[b])):
                    new = [rt[:] for rt in routes]
                    new[a][i], new[b][j] = new[b][j], new[a][i]
                    if route_drive_time_h(new[a], dist_km) <= TIME_WINDOW_H and route_drive_time_h(new[b], dist_km) <= TIME_WINDOW_H:
                        yield ("swap", tuple(sorted((routes[a][i], routes[b][j])))), new

def two_opt_moves(routes, dist_km):
    K = len(routes)
    for r in range(K):
        R = routes[r]
        n = len(R)
        for i in range(n-2):
            for j in range(i+2, n):
                cand = R[:i+1] + R[i+1:j+1][::-1] + R[j+1:]
                if route_drive_time_h(cand, dist_km) <= TIME_WINDOW_H:
                    new = [rt[:] for rt in routes]
                    new[r] = cand
                    touched = tuple(sorted(R[i+1:j+1]))
                    yield ("2opt", touched), new

def tabu_search(initial_routes, dist_km):
    assert cover_ok(initial_routes), "Start nie pokrywa wszystkich punktow."
    assert len(initial_routes) == MAX_TRUCKS, f"Wymagane {MAX_TRUCKS} tras."
    for r in initial_routes:
        assert feasible_route(r, dist_km), "Trasa startowa przekracza ograniczenia."

    current = [r[:] for r in initial_routes]
    best = [r[:] for r in current]
    best_cost = total_km(best, dist_km)

    tabu_until = defaultdict(int)
    iteration, no_imp = 0, 0
    print(f"[TS] Start = {best_cost:.2f} km")

    while iteration < MAX_ITERS and no_imp < MAX_NO_IMPROVE:
        iteration += 1
        neighborhood = []
        neighborhood.extend(relocate_moves(current, dist_km))
        neighborhood.extend(swap_moves(current, dist_km))
        neighborhood.extend(two_opt_moves(current, dist_km))

        if not neighborhood:
            break

        best_cand, best_cand_cost, best_move_key = None, float("inf"), None
        for (mkey, cand) in neighborhood:
            cand_cost = total_km(cand, dist_km)
            touched = mkey[1]
            touched_iterables = touched if isinstance(touched, (tuple, list)) else (touched,)
            is_tabu = any(tabu_until.get(x, 0) > iteration for x in touched_iterables)
            if is_tabu and cand_cost + 1e-9 >= best_cost:
                continue
            if cand_cost + 1e-9 < best_cand_cost:
                best_cand, best_cand_cost, best_move_key = cand, cand_cost, mkey

        if best_cand is None:
            neighborhood.sort(key=lambda x: total_km(x[1], dist_km))
            mkey, best_cand = neighborhood[0]
            best_cand_cost = total_km(best_cand, dist_km)
            best_move_key = mkey

        current = [r[:] for r in best_cand]

        tenure = TABU_TENURE_BASE + random.randint(0, 5)
        touched = best_move_key[1]
        for x in (touched if isinstance(touched, (tuple, list)) else (touched,)):
            tabu_until[x] = iteration + tenure

        if best_cand_cost + 1e-9 < best_cost:
            best, best_cost, no_imp = [r[:] for r in current], best_cand_cost, 0
        else:
            no_imp += 1

        if iteration % 50 == 0:
            print(f"[TS] iter={iteration} | best={best_cost:.2f} km | cur={total_km(current, dist_km):.2f} km | no_imp={no_imp}")

    print(f"[TS] Koniec: best={best_cost:.2f} km, iter={iteration}, no_imp={no_imp}")
    return best

def report_and_draw(G, routes, dist_km, filename):
    id_to_point = {pid: (lat, lon) for pid, lat, lon in ALL_POINTS}
    m = folium.Map(location=[DEPOT_LAT, DEPOT_LON], zoom_start=11, tiles="cartodbpositron")
    colors = ["red", "blue", "green", "purple", "orange"]

    tot_km, tot_h = 0.0, 0.0
    print("\nWyniki tras:")
    for idx, r in enumerate(routes, start=1):
        km = route_drive_km(r, dist_km)
        h = route_drive_time_h(r, dist_km)
        ok = h <= TIME_WINDOW_H
        tot_km += km
        tot_h += h
        print(f"Ciezarowka {idx}: {len(r)} punktow | {km:.2f} km | {h:.2f} h -> {'OK' if ok else 'PRZEKROCZENIE'}")

        color = colors[(idx - 1) % len(colors)]
        full = [DEPOT_ID] + r + [DEPOT_ID]
        latlons = [id_to_point[p] for p in full]
        nodes = [ox.distance.nearest_nodes(G, X=lon, Y=lat) for (lat, lon) in latlons]

        route_line = []
        for a, b in zip(nodes, nodes[1:]):
            try:
                path = nx.shortest_path(G, a, b, weight="length")
                coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path]
                if route_line and coords and route_line[-1] == coords[0]:
                    coords = coords[1:]
                route_line += coords
            except Exception as e:
                print(f"Blad wyznaczania sciezki: {e}")

        folium.PolyLine(route_line, color=color, weight=4, opacity=0.8, tooltip=f"Trasa {idx} ({km:.1f} km)").add_to(m)

        for pid in r:
            lat, lon = id_to_point[pid]
            folium.CircleMarker(
                location=[lat, lon],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                popup=f"Sklep #{pid}"
            ).add_to(m)

    folium.Marker([DEPOT_LAT, DEPOT_LON], popup="Magazyn (Depot)", icon=folium.Icon(color="black", icon="home")).add_to(m)
    m.save(filename)
    print(f"Suma: {tot_km:.2f} km | Czas: {tot_h:.2f} h | Zapisano mape do {filename}")

def main():
    G = build_graph()
    ids = [pid for pid, *_ in ALL_POINTS]
    id2node = map_points_to_nodes(G, ALL_POINTS)
    dist_km = compute_network_distance_matrix_km(G, id2node, ids)

    algo = ALGO.lower()

    if algo == "compare-ts":
        rows = []
        modes = [
            ("ts-nn", nn_initial, "ts_nn"),
            ("ts-sweep", sweep_initial, "ts_sweep"),
            ("ts-cw", cw_initial, "ts_cw"),
        ]
        for label, init_fun, suffix in modes:
            print(f"\n--- Uruchomienie: {label} ---")
            start = init_fun(dist_km)
            if len(start) < MAX_TRUCKS:
                for _ in range(MAX_TRUCKS - len(start)):
                    start.append([0])
            elif len(start) > MAX_TRUCKS:
                start = start[:MAX_TRUCKS-1] + [sum(start[MAX_TRUCKS-1:], [])]

            routes = tabu_search(start, dist_km)
            report_and_draw(G, routes, dist_km, filename=f"trasy_ciezarowek_{suffix}_osm.html")
            sum_km = total_km(routes, dist_km)
            sum_h = sum(route_drive_time_h(r, dist_km) for r in routes)
            max_h = max(route_drive_time_h(r, dist_km) for r in routes)
            rows.append([label, f"{sum_km:.2f}", f"{sum_h:.2f}", f"{max_h:.2f}"])

        with open("porownanie_tabu.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Algorytm", "Suma km", "Suma h", "Max czas trasy [h]"])
            w.writerows(rows)
        print("\nZapisano plik porownanie_tabu.csv")
        return

    if algo == "nn":
        routes, suffix = nn_initial(dist_km), "nn"
    elif algo == "sweep":
        routes, suffix = sweep_initial(dist_km), "sweep"
    elif algo == "cw":
        routes, suffix = cw_initial(dist_km), "cw"
    elif algo == "ts-nn":
        start = nn_initial(dist_km)
        routes, suffix = tabu_search(start, dist_km), "ts_nn"
    elif algo == "ts-sweep":
        start = sweep_initial(dist_km)
        routes, suffix = tabu_search(start, dist_km), "ts_sweep"
    elif algo == "ts-cw":
        start = cw_initial(dist_km)
        if len(start) < MAX_TRUCKS:
            for _ in range(MAX_TRUCKS - len(start)):
                start.append([0])
        elif len(start) > MAX_TRUCKS:
            start = start[:MAX_TRUCKS-1] + [sum(start[MAX_TRUCKS-1:], [])]
        routes, suffix = tabu_search(start, dist_km), "ts_cw"
    else:
        raise ValueError("Niepoprawny ALGO")

    assert len(routes) == MAX_TRUCKS
    assert cover_ok(routes)
    for r in routes:
        assert feasible_route(r, dist_km)

    report_and_draw(G, routes, dist_km, filename=f"trasy_ciezarowek_{suffix}_osm.html")

if __name__ == "__main__":
    main()