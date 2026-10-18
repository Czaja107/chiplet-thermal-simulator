Optimize a legal eight-chiplet layout to minimize worst-case GPU and HBM temperatures across five fixed workloads. Submit coordinates and optional wire paths.

# Beat the Hotspot — Autolab Hill

The submission directory must contain a `submission.json` file. Other files are ignored by scoring. The evaluator reads only that file from the submission, performs all geometry checks, and runs its own pinned HotSpot build and fixed workloads. A local baseline is `examples/baseline/submission.json`.

Routine `eval` calls use a 64 × 64 mesh and `reference_64.json`. `autolab hills eval <folder> -H beat-the-hotspot --final` uses a 128 × 128 mesh and `reference_128.json`. The primary metric is `score` to **minimize**; `worst_gpu_c` and `worst_hbm_c` are secondary tie breakers, also **minimize**. The grid is a primary configuration, so reports from different grids must not be compared on one leaderboard. A lower score is better; below 1 means both temperatures beat the seeded baseline at that same mesh. Every invalid submission has `passed: false` and does not rank.

There are no private workloads; all five are public in `workloads.json`. `agent_workloads.json` documents every field and how to feed the same maps to another simulator. The AI method is unconstrained: use an agent, surrogate, Bayesian search or autoresearch to propose `submission.json`. Only the submitted geometry is scored.

## Submission example and local use

```bash
python3 verify_submission.py examples/baseline/submission.json
python3 verify_high_accuracy.py examples/baseline/submission.json --hotspot vendor/HotSpot/hotspot --grid 64 --output example_eval.json
```

For a 128 check use `--grid 128`; this may take many minutes. The included HotSpot executable is pinned Linux x86-64; Linux or WSL is needed on the scoring machine. The bundled license covers its redistribution. The Hill package includes the source at its pinned revision. No participant code is executed during judging.

## Base workloads and traffic

All wattage below excludes interconnect additions. Each die's 16 × 16 numerical map sums to its base watts; row zero is at the **bottom** of the die. Maps are in W/cell and cover the physical die footprint. In every workload, each of the eight links has a separate utilization fraction in `workloads.json`.

| Workload | GPUs G0–G3 (W) | HBMs H0–H3 (W) | Base total (W) | Mean primary / secondary link use |
| --- | --- | --- | ---: | ---: |
| `tensor_training` | 88, 94, 86, 90 | 10, 11, 10, 10 | 399 | 39% / 17% |
| `skewed_compute` | 104, 56, 92, 48 | 12, 10, 11, 9 | 342 | 37% / 15% |
| `attention_decode` | 53, 57, 50, 55 | 24, 26, 25, 23 | 313 | 84% / 56% |
| `memory_stream` | 44, 46, 42, 48 | 51, 49, 50, 53 | 383 | 94% / 69% |
| `mixed_serving` | 72, 79, 54, 63 | 18, 15, 24, 19 | 344 | 61% / 43% |

The first two emphasize compute, the next two memory, and the last mixes asymmetric loads. The heat-map shapes vary by die and workload. These values are benchmark assumptions, not measured GPU/HBM data.

## Exact heat-source definition

For link `l` in workload `w`, let `B_l` be peak provisioned bandwidth in GB/s, `u_wl` its utilization fraction in [0,1], and `L_l` routed Manhattan length in mm, including both port-to-track accesses:

```text
active_bits_per_s = 8e9 * B_l * u_wl
P_PHY_total_W = active_bits_per_s * 0.20e-12
P_wire_W      = active_bits_per_s * L_l * 0.08e-12
```

Half of `P_PHY_total_W` belongs to the GPU endpoint and half to the HBM endpoint. **At each endpoint**, its PHY heat is uniformly distributed over a rectangle whose tangential length is the reserved port length `B_l / 150` mm, centered on that port segment, and whose perpendicular extent is **1.0 mm into the chiplet plus 1.0 mm outward** from its edge. For an edge port `(x_p,y_p)` with a right/left outward normal, the rectangle is `[x_p-1, x_p+1] × [y_p-length/2, y_p+length/2]` mm; for a top/bottom port, exchange x and y. The local area density is endpoint PHY W divided by `2 mm × length`. Exactly half its watts lie inside the chiplet and enter the **die plane**; the other half lie outside and enter the **silicon interposer layer**. Adjacent PHY rectangles on the same side are separated by at least 0.4 mm. Rasterization uses the *intersection area* with each die power pixel and each 1 × 1 mm interposer tile, conserving watts even if boundaries cut cells. The outside-port source is a simplified vertical-layer representation of the fan-out/edge region.

`P_wire_W` is uniform per mm along the specified obstacle-free **Manhattan** route; all wire watts enter the silicon interposer layer. Every track segment and each orthogonal port-access leg is split at tile boundaries by length; its tile receives its fraction of total routed wire watts. Its centerline has no width and no additional source at the die edge. Port heat and wire heat may share an interposer tile: their watts add; they represent distinct electronic losses. `power_budget.json` reports total PHY, its die/interposer halves, wire watts and endpoint rectangles for each workload. The HotSpot trace includes base + inside PHY in die pixel entries and outside PHY + wire in the interposer tile entries.

For example, a fully utilized 600 GB/s link at 4 mm generates 0.96 W PHY total (0.48 W at each endpoint, 0.24 W inside and 0.24 W outside that endpoint), plus 1.536 W along its route. A fixed W/□ cannot describe this whole bundle: Ω/□ is material sheet resistance and Joule heating depends on conductor currents and activity. The technology energy coefficients are common across links, while utilization, port locations and routed lengths create workload and layout dependence. These coefficients and the two-layer heat assignment are illustrative.

## Placement, interconnects and scoring

All eight links are compulsory. Primary `P0`–`P3` connect matching G/H indices at 600 GB/s and max 5 mm routed reach. Secondary `S0`–`S3` connect G0→H3, G1→H0, G2→H1, G3→H2 at 300 GB/s and max 6 mm. Both endpoints need nonoverlapping reserved edge length at 150 GB/s/mm: 4 mm primary, 2 mm secondary. Every die terminates one of each (900 GB/s and 6 mm reserved edge total); two ports sharing a side also need their 0.4 mm gap. The middle 60% of each die side is usable; same-side ports need 0.4 mm between them. The deterministic port allocator picks the side facing the partner from die-center displacement, then places ports by sorted link ID. Geometric separation is ≥1 mm die to die and ≥1 mm from the interposer boundary.

The router uses 0.5 mm pitch grid cells with 0.2 mm die clearance; all chosen paths must avoid occupied cells, satisfy per-link reach, and satisfy `sum(B_l × L_l) ≤ 13,500 GB/s·mm`. Coordinates are continuous, but the reference route track coordinates are cell centers `((i+0.5)*0.5,(j+0.5)*0.5)` mm. Explicit paths in `wire_routes_grid` are arrays of adjacent `[i,j]` cells with prescribed start and end access cells. If omitted, the judge uses its deterministic shortest-path router. Its `results.json` exposes accepted paths.

Objective 1 is the maximum GPU die-plane temperature across all workloads and GPU grid cells; objective 2 is the analogous HBM maximum. Keep both in results and Pareto views. For a scalar leaderboard, after rejecting illegal submissions, the reference score is

```text
score = max((T_GPU - ambient) / (T_GPU_reference - ambient),
            (T_HBM - ambient) / (T_HBM_reference - ambient))
```

The seeded random layout provides a reference at each scored resolution. The 64 × 64 values are in `challenge_spec.json` and `reference_64.json`; the finalist 128 × 128 values are in `reference_128.json`. A score below one improves **both** objectives relative to the same-grid reference. The illustrated run in `random_example/` uses 64 × 64 steady-state cells. An alternate simulator can use `agent_workloads.json` to explore designs, but final comparisons require the same judge.

## Thermal boundary and scope

The HotSpot stack is a 500 µm silicon interposer (wire and outside-port sources), a 150 µm silicon die plus passive gap plane (base and inside-port sources), and a 20 µm TIM under a fixed spreader and sink. A central 44 × 34 mm good-contact region from x=4…48 and y=4…38 mm has TIM material resistivity 0.25 **m·K/W**; the peripheral region has 2.0 m·K/W. Here `m` means metres, not milli. The cooler stays fixed as dies move. No separate side-edge or bottom convection is imposed. Cooling, gaps, PCB path, PHY losses and route energy are intentionally simplified, so the outputs are relative benchmark values, not calibrated junction predictions. The router does not model wire width, layer congestion, IR drop, latency, crosstalk, vias or signal integrity.

External simulator: https://github.com/uvahotspot/HotSpot . Illustrative short-reach energy context: https://research.nvidia.com/publication/2024-04_0190-pjbit-252-gbswire-inverter-based-ac-coupled-transceiver-short-reach-die and https://ieeexplore.ieee.org/document/10919466 . Those reports do not determine this benchmark's PHY/wire split.

## Submission verifier and two simulation resolutions

The participant submits one UTF-8 JSON file, `submission.json`, with **only** `placements_mm` and optional `wire_routes_grid`:

```json
{
  "placements_mm": {
    "G0": [7.563, 3.259], "G1": [33.272, 2.856],
    "G2": [33.072, 27.366], "G3": [7.994, 27.611],
    "H0": [20.934, 3.584], "H1": [34.12, 15.888],
    "H2": [20.77, 27.311], "H3": [8.748, 15.163]
  }
}
```

Origins are lower-left corners in mm. A path override such as `"wire_routes_grid": {"P0": [[i,j], ...]}` uses integer `[column,row]` track cells and must join the two assigned access cells with neighboring Manhattan steps. See `custom_wire_example.json` and the automatic routes in the verification report. Omit this field to let the deterministic router select all shortest paths. A submitted trace, temperature, power map, simulator setting or claimed score is never used by the judge. The workload file and challenge specification are read from the frozen evaluator.

`verify_submission.py` checks exact JSON structure, finite coordinates, chiplet identities, fixed orientations and dimensions, the 1 mm package margin, the 1 mm die separation, both endpoint port capacities, the 0.4 mm separation of same-side ports, all eight required links, legal Manhattan tracks with 0.2 mm die clearance and valid access endpoints, 5/6 mm per-link reach, and the aggregate 13,500 GB/s·mm budget. It reports the resulting port centers, routes, edge capacities and margin. Run it before spending time on thermal calculations:

```bash
python3 verify_submission.py submission.json --output feasibility.json
python3 -m unittest discover -s tests -v
```

The preview `run_simulations.py --grid 64` takes roughly 0.81 × 0.66 mm mesh cells in the interposer footprint. For routine Autolab Hill iteration, `eval.py` uses **64 × 64** cells; its `--final` mode invokes a **128 × 128** finalist check (about 0.406 × 0.328 mm). An optional manual **256 × 256** mesh diagnostic (about 0.203 × 0.164 mm) is available but expensive. Each resolution uses the same physical sources, geometry and thermal boundary; only the numerical grid changes. These are *relative* high-resolution model checks, not proof of physical junction accuracy. The two resolutions have separately calibrated random-layout denominators (`reference_64.json` and `reference_128.json`), and reports tag grid size as a primary configuration. Never mix grid resolutions or copy the 64 × 64 reference temperatures into a fine-grid score. A 256 run has no official baseline or leaderboard until the organizer calibrates it.

The organizer's direct verifier runs from a fresh temporary directory, checks the SHA-256 of a pinned Linux x86-64 HotSpot build, generates five new traces from the immutable workload maps, invokes HotSpot, extracts the maximum die-plane GPU and HBM grid cells, and computes the scalar score. It **never executes participant code or reads participant-provided power maps or thermal results**. It discards temporary grids after the report and limits each workload to 1800 seconds:

```bash
python3 verify_high_accuracy.py submission.json --hotspot vendor/HotSpot/hotspot --grid 64 --output verifier_64.json
python3 verify_high_accuracy.py submission.json --hotspot vendor/HotSpot/hotspot --grid 128 --output verifier_128.json
# Optional numerical diagnostic, without an official score:
python3 verify_high_accuracy.py submission.json --hotspot vendor/HotSpot/hotspot --grid 256 --output diagnostic_256.json
```

The 128 grid is the finalist verifier; it can take much longer than the 64 grid. The 256 grid is an optional numerical diagnostic. A verifier score below 1 improves both worst temperatures relative to its **same-grid** seeded random baseline. The score is `max((GPU_peak−25)/(GPU_ref−25), (HBM_peak−25)/(HBM_ref−25))`. Violating any hard constraint makes the submission ineligible. There is no absolute GPU or HBM temperature cap in this synthetic edition. The baseline and example traces were produced at 64; the separate 128 reference is also included.

