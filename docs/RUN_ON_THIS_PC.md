# Demonstrate this project on this Windows PC

Validated on 14 October 2026 using Ubuntu 24.04 in WSL2 with WSLg, OpenJDK 25 and GCC 13.

## Open the demo

From PowerShell in the project folder:

```powershell
.\Launch-Cooja.ps1
Start-Process .\results\dashboard.html
```

Cooja opens the installed `demo.csc`. Maximize the window. In Simulation control,
click Start (or press Ctrl+S). Select a speed limit of 100% if you want to explain
traffic at approximately real-time speed. Allow 30–60 simulated seconds for routing
and configuration. Network shows motes; Mote output shows the application messages;
Timeline shows radio activity. Cluster membership is reported in logs, rather than
automatically drawn as colored clusters in Network.

## Explain what the audience sees

- Node 1 is the base station: it coordinates assignments and receives summaries.
- Nodes 2–9 are sensors. The replayed policy is COA-APSO-LEACH-SA (the root logs
  `ROOT ready ... policy=COA-APSO-LEACH-SA`). A new epoch starts every 90 simulated
  seconds, and the cluster heads rotate:

  | Epoch | Starts at | Cluster heads |
  |---|---|---|
  | 0, 1 | 0 s | 3, 5, 7 |
  | 2 | 180 s | 2, 7, 8 |
  | 3, 4 | 270 s | 3, 5, 7 |
  | 5 | 450 s | 5, 7, 9 |

- Only sensors whose head changes receive a new `CONFIG`; an unchanged head keeps
  its old epoch number in its log lines. If a `CONFIG` is lost, the root resends it
  after that sensor's next 15-second registration.
- `CONFIG ... role=HEAD/MEMBER` identifies each role.
- `MEMBER DATA` is a reading sent toward a cluster head.
- `CLUSTER RX` confirms that the head received a member's reading.
- `AGG head=... samples=...` confirms a summary arrived at the base station.
- `ENERGEST` reports CPU and radio activity ticks. These are not Joules.

Contiki-NG is the operating system running the C firmware on the simulated devices.
Cooja simulates the devices, radio and network. RPL provides IPv6 routes; UDP carries
our application messages. Physical routes can pass through the root even when the
application destination is a cluster head.

LEACH groups sensors around cluster heads. PSO searches candidate head selections;
APSO adapts the search. The proposed control-overhead-aware decision changes heads
only when predicted savings justify setup cost, or a safety condition requires it.
Python implements that optimization. Cooja replays the resulting schedule; it does
not execute PSO live or feed measured energy back into Python. `export_cooja_policy.py`
runs the same `simulate()` used for the research results on the 8-mote Cooja layout,
with each Cooja epoch standing for 200 model rounds. Over those 1200 model rounds the SA
policy makes 7 reconfigurations and no sensor dies; the original COA-APSO-LEACH loses a
node at round 1035. `python export_cooja_policy.py --policy coa` regenerates the original
policy for comparison (re-run the install afterwards).

## Verified results

Python: six tests passed; 60 sensors, 450 rounds, seed 42 completed. Proposed method:
60 sensors alive, 7 reconfigurations, 0.0465 J modeled control energy. APSO: 24
reconfigurations, 0.0690 J control energy. E-LEACH used less control energy still;
these results do not establish universal superiority.

Cooja: both C programs compiled and a 600-second simulated run passed the checks
in `validate_cooja.py`: all eight sensors configured and reported Energest, and
member sends, cluster receives and root aggregates were observed. The root received
114 aggregate packets containing 299 samples. Logs and parsed results are in
`results/cooja-run.txt`, `results/cooja-validation.log`, `results/cooja_report.json`
and `results/cooja_energest.csv`. This is a networking smoke test, not a measurement
of packet delivery ratio or comparative lifetime. Energest values are the latest
periodic report from each mote, not a synchronized end-of-run snapshot.

Installed repository: `/home/anish/coa-demo/contiki-ng` inside Ubuntu.
Contiki-NG commit: `7a4df8a941d552b10c730db70e934a9be10937af`.
Cooja commit: `fabff3ee41eeeb6f3de7bd11f7c9cdf0a7d7dfc4`.

## Rebuild and repeat validation after firmware edits

In Ubuntu:

```bash
cd /mnt/d/WORKSPACE/PYTHON/COA_APSO_LEACH_Demo
sh install_cooja.sh ~/coa-demo/contiki-ng
python3 validate_cooja.py ~/coa-demo/contiki-ng
cd ~/coa-demo/contiki-ng/tools/cooja
java -jar build/libs/cooja.jar --no-gui --logdir=/home/anish/coa-demo --contiki=/home/anish/coa-demo/contiki-ng ../../examples/coa-apso-leach/validation.csc
```

The headless simulation runs faster than real time and must finish with `TEST OK`.
Close and reopen the GUI after installing changed firmware.
