# Project viva: 5-minute walkthrough

## 0:00-0:40 Problem

Wireless sensor networks are battery-limited. In LEACH, cluster heads gather measurements and transmit aggregated data. Frequent or poorly selected cluster heads can deplete devices faster. Our aim is to choose better cluster heads **and** avoid needless cluster rebuilding.

## 0:40-1:30 Foundation papers

**2024 IEEE:** Residual energy is an essential selection factor. **2025 IEEE:** PSO searches over combinations of energy/distance-aware cluster heads, with adaptive inertia. **2025 Springer:** heterogeneous node energies and direct-vs-relay routing also affect lifetime.

## 1:30-2:30 Algorithm

Proposed name: **COA-APSO-LEACH**. Each candidate is mapped to actual alive sensor IDs. The adaptive PSO fitness combines modeled data energy, cluster-size imbalance, residual-energy scarcity, and CH residual-energy dispersion. Its reconfiguration decision is:

`predicted saving over H rounds > (setup cost × safety margin)`

or emergency when CH residual energy is too low. Status-reporting messages are separately accounted for. The processor running PSO is assumed to be the powered base station, not an 8-bit battery mote.

## 2:30-3:30 Simulation and metrics

`python3 run_demo.py --nodes 60 --rounds 450 --out results`

Explain the browser dashboard: alive nodes, network energy, setup/control energy, and reconfiguration count. Explain **FND** = first dead node, **HND** = half nodes dead, **LND** = all nodes dead. If not observed by the horizon, it is a *censored event*, not zero or infinity.

## 3:30-4:30 Cooja demo

Contiki-NG runs sensor and root C programs. Each sensor registers by IPv6/UDP. The root returns a policy containing a cluster-head address. Members submit modeled sensing readings to the selected head. Cluster heads aggregate observation counts and forward them to the root. Energest reports accumulated transmit/listen/CPU ticks. The policy is prepared offline using Python: not an online cross-process controller.

## 4:30-5:00 Q&A

**Why Contiki?** Embedded networking, visual motes, IPv6/RPL, communication traces, radio-time accounting.

**Why not run PSO on every sensor?** PSO is compute-intensive. The selected system uses centrally calculated CH assignments at the powered root.

**What's new?** Evaluating an explicitly modeled reconfiguration cost before accepting an APSO candidate, with safety override. Novelty must still be established against recent event-driven re-clustering literature.

**Why do energy readings differ?** Python computes Joules in the simplified first-order model; Cooja accumulates radio activity ticks under the Contiki stack. They are separate experiments unless calibrated under a common energy model.

**Can it be submitted?** Not until there is validated full experimental methodology, repeated seeds, variance / significance analysis, comparable baselines, and experimental proof of a nontrivial novel improvement.
