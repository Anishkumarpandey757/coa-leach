# COA-APSO-LEACH: Energy Optimization in Wireless Sensor Networks

**Demo project, 2026**. The package contains a reproducible Python energy-model experiment and a companion Contiki-NG/Cooja application-level WSN demo. The two are **not** identical energy models; no real hardware testing is claimed.

**Local validation update, 14 October 2026:** The Cooja firmware now compiles and passes a 600-second nine-mote networking smoke test in Ubuntu WSL2. All eight sensors received configuration and reported Energest; the root received 114 aggregates containing 299 samples. Run `.\Launch-Cooja.ps1` from PowerShell to reopen the scenario. See [this PC's demo guide](docs/RUN_ON_THIS_PC.md) and `results/cooja-run.txt`. Older statements below that Cooja execution was unverified describe the original package; comparative Cooja energy/lifetime experiments remain outstanding.

## Research idea

**Title:** Control-Overhead-Aware Adaptive PSO-LEACH with Hybrid Routing for Energy-Efficient Wireless Sensor Networks.

Research question: Can a cost-benefit test suppress needless PSO-LEACH cluster-head reconfiguration while preserving network lifetime?

Combines (i) energy-aware cluster-head choice from LEACH variants, (ii) adaptive particle swarm optimization (APSO), (iii) heterogeneity and optional CH-to-CH relay, and (iv) proposed control-energy break-even test.

`PSO candidate benefits over H rounds > margin * setup energy cost` or CH below safety energy => change CH. Otherwise retain existing clusters.

## WHAT IS IMPLEMENTED

| Module | Actual implemented functionality | Status |
| --- | --- | --- |
| Python WSN simulator | 1st-order radio Tx/Rx; energy per node; heterogeneity; node death; baseline LEACH; energy-first LEACH; standard PSO; adaptive PSO; proposed cost-benefit-gated APSO | Python run & tests passed |
| Baseline comparison | Same initial topology, seed settings, radio model, simulation horizon; CSV and graph outputs | Python run completed |
| Charts | Nodes alive, residual energy, control energy, reconfiguration counts, network topology | Generated |
| Repeated seeds | Paired network seeds and CSV mean/SD; survival censoring tracked | Script included |
| Cooja motes | Root and eight Contiki-NG sensor motes using RPL + IPv6/UDP; policy assignment, CH role, member payload collection, aggregate summaries, Energest tick logs | **Source prepared; Cooja compilation and execution NOT verified here** |
| Policy exchange | Python writes a 6-epoch COA-APSO-LEACH-SA assignment table `policy.h` used by Cooja (`--policy coa` for the original) | Generator executed; this is *offline policy replay*, not live Python-to-Cooja control |
| Paper submission | No experimental Cooja measurements, formal novel-paper validation or significance testing yet | **Not publication-ready** |

**Important:** The Cooja firmware replays a policy calculated *before* the Cooja run. It does not compute PSO on 8-bit motes. Python has a global view of the simulation state, and measured Contiki routing can be different from the idealized energy model. The physical RPL path of an application-layer sensor-to-CH datagram may go via the DAG root. Do not describe this as hardware-level LEACH MAC routing.

## 1. Fastest demo (macOS / Windows / Linux)

Install Python 3.10+; open Terminal/PowerShell in this unzipped folder and run:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests -q
python3 run_demo.py --nodes 60 --rounds 450 --out results
```

On Windows PowerShell use `py` instead of `python3` if necessary:

```powershell
py -m pip install -r requirements.txt
py -m pytest tests -q
py run_demo.py --nodes 60 --rounds 450 --out results
```

Open `results/dashboard.html` in a browser. All plots and summary CSV are in `results/`. The supplied archive already includes one illustrative run. Different network sizes/seeds may show different outcomes; some FND/HND events may not occur within the chosen number of rounds.

More demanding experiment:

```bash
python3 run_research.py --seeds 5 --nodes 60 --rounds 600 --out results
```

**Note:** Results here are model-generated numerical simulations. Energy units J come from an explicit idealized radio model; not from Energest/hardware. Packet delivery ratio is NOT computed because the idealized simulation does not model collisions, packet loss or MAC retransmissions.

## 2. Why your professor recommends Contiki-NG / Cooja

The Python experiment can compare mathematical WSN algorithms but does not prove that a real low-power radio stack can carry the messages. Contiki-NG is an embedded IoT operating system and Cooja is its visual wireless-network simulator. Together they provide simulated devices, routing and neighbor behaviors, packet handling, and **Energest** TX/RX/CPU-time accounting. A Cooja demo is stronger than a graph alone for showing how nodes actually exchange data.

Use the newer **Contiki-NG**, not legacy Contiki 2.x. The official modern Cooja launcher is `tools/cooja/./gradlew run`, not the old Ant-only procedure. Official current documentation recommends JDK 25 (as of Oct 2026).

## 3. Contiki/Cooja reproducible setup

**Easiest reliable GUI:** Ubuntu Desktop (native x86_64 or VM), a working JDK 25, and Contiki-NG. On Windows use an Ubuntu VM or WSL with GUI support; on Apple Silicon a supported Linux VM or carefully configured Docker/XQuartz environment may be easier than native 32-bit Cooja mote compilation. Official Contiki-NG docs warn that native Cooja motes have 32-bit toolchain constraints. **Do not assume `pip install contiki` installs it.**

### Ubuntu Desktop (recommended)

```bash
sudo apt update
sudo apt install -y git build-essential python3 python3-pip
# Install/configure JDK 25 using your Ubuntu distribution's package source.
# If available:
sudo apt install openjdk-25-jdk
java -version

git clone https://github.com/contiki-ng/contiki-ng.git
cd contiki-ng
git submodule update --init --recursive
```

If your distro has no `openjdk-25-jdk` package, consult the current Contiki-NG toolchain instructions to install a JDK 25 distribution. For 32-bit native Cooja motes, use the documented Docker image/toolchain if a native compile reports architecture incompatibility.

In **another terminal** enter this extracted project folder, then run:

```bash
python3 export_cooja_policy.py
sh install_cooja.sh /absolute/path/to/contiki-ng
```

Then:

```bash
cd /absolute/path/to/contiki-ng/tools/cooja
./gradlew run
```

In Cooja select **File > Open Simulation** and open:

`contiki-ng/examples/coa-apso-leach/demo.csc`

Select **Start**. Watch **Network** and **Mote output**. Look for `ROOT ready`, `ASSIGN node=`, `CONFIG id=`, `MEMBER DATA`, `CLUSTER RX`, `AGG head=`, and `ENERGEST id=`.

`demo.csc` is generated from the official installed `rpl-udp-cooja.csc` template, preserving mote platform configuration. It requires that upstream example to exist. Compile **root.c** as the root mote type, **node.c** as the eight sensor motes. The first few tens of seconds are for RPL formation and registration.

### macOS (Python first)

The *Python* demo works directly on a Mac. To use Contiki GUI natively you need current Xcode command-line tools, Homebrew packages, and **JDK 25** (see official macOS toolchain documentation). But current Cooja native mote toolchains can require 32-bit support unavailable directly on modern macOS, especially Apple Silicon. The recommended path for the Cooja GUI is an x86_64 Ubuntu virtual machine or a compatible Contiki-NG Docker/X11 setup, not an unsupported native assumption.

### Windows

Python demo works from PowerShell. For Cooja, Ubuntu Desktop in a VM is the simplest fallback. WSL2 with WSLg or a GUI-enabled Linux environment may also work, but architecture and display configuration affect Cooja. Use an Ubuntu shell for cloning and compiling Contiki-NG.

## 4. What to show during the 5-minute live demo

1. Show the **topology.png**: blue sensor nodes, star cluster heads, base station outside sensing area.
2. Show **alive_nodes.png**: compare lifetime trends and explain FND/HND/LND. If not observed say 'censored within the horizon'.
3. Show **control_overhead.png**: demonstrate effect of cluster setup and telemetry messages. Note fewer changes does *not automatically* mean lower total energy.
4. Open **dashboard.html** and discuss table values from the actual saved simulation run.
5. Start Cooja scenario: show nine motes joining RPL, the root assigning heads, members sending packets to heads, aggregation to base station and Energest counters.
6. Explain the **research gap and limitations**: externally computed adaptive PSO, offline Cooja replay, idealized first-order energy model vs actual radio-time ticks, importance of repeated random seeds.

Detailed explanation: `docs/DEMO_SCRIPT.md`.

## 5. Ablation controls / reproducibility

- In `simulator/engine.py`, `Config.hybrid_routing=False` removes the optional CH relay selection.
- `Config.setup_margin` controls how conservative the proposed break-even decision is.
- `Config.check_period` controls how frequently the proposed method gathers node-status information. Defaults to 15, matching APSO's 15-round periodic reporting, so differences are not driven just by polling frequency.
- `Config.ch_min_fraction` sets the emergency energy threshold. Nodes below it are not eligible as cluster heads while enough healthier nodes remain (`Config.exclude_weak_heads`), so an emergency cannot re-elect the same weak head round after round.
- `Config.eleach_status_cost` charges E-LEACH the same status-report energy that the PSO controllers pay, since residual-energy election needs that information too.
- `--legacy` (on `run_demo.py` and `run_research.py`) turns both of the above off and reproduces the original results exactly.
- `COA-APSO-LEACH-SA` is the survival-aware variant; the original `COA-APSO-LEACH` is kept unchanged as a baseline. SA reviews heads on the regular check schedule and re-clusters early only if a head is predicted to die within `guard_rounds`. At a check it switches when the energy saving pays for setup **or** a current head is at risk: below `ch_min_fraction`, predicted to die within `lookahead` rounds, or drained more than `drain_tolerance` below the network's average residual fraction. Its PSO fitness adds `survival_weight` × (fraction of heads predicted to die within `survival_horizon` rounds).
- `Config.pso_particles` and `Config.pso_iterations` control search cost (computational cost on base station, **not** currently converted into Joules).
- `Config.hetero=False` tests homogeneous energy sources.
- For an illustrative *periodically rotating* Cooja policy, run `python3 generate_baseline_policy.py`, re-run the install and recompile. This is **not canonical randomized LEACH**; it is a demonstration of the cost of repeated cluster changes. Restore COA policy using `python3 export_cooja_policy.py`.

## 6. Limitations you must disclose in viva/paper

- Not an experimentally validated conference paper. Running code does not independently establish research novelty.
- Baseline 'E-LEACH' is *our residual-energy-priority implementation*, not an exact reproduction of IMP-RES-EL from the 2024 paper.
- The first-order model includes message transmission/reception for setup, but not overhearing beyond chosen receiver, idle listening, MAC collisions, interference, retransmissions, energy harvesting, channel noise, CPU PSO energy, or control packet acknowledgement.
- Controller is assumed powered at the BS, not a tiny sensor mote. Exclude BS CPU energy from sensor lifetime only if that architecture is explicitly stated.
- Control energy reported by Python is modeling, not directly measured from Contiki Energest. In Cooja, Energest returns radio/CPU activity **ticks**; converting ticks to Joules requires a device/platform current profile and voltage.
- Single-run results are insufficient for publication. Repeat seeds, disclose censored lifetimes, and compare your decision rule with existing adaptive re-clustering methods.

## 7. Three foundation papers (all 2016-2026)

1. Abose et al., **Optimized Cluster Routing Protocol With Energy-Sustainable Mechanisms for Wireless Sensor Networks**, IEEE Access (2024), https://doi.org/10.1109/ACCESS.2024.3429645
2. Haris & Nam, **Enhancing Energy Efficiency in IoT-WSNs Through Optimized PSO Cluster Head Selection**, IEEE Access (2025), https://doi.org/10.1109/ACCESS.2025.3583922
3. Zhang et al., **Energy-efficient adaptive routing in heterogeneous wireless sensor networks via hybrid PSO and dynamic clustering**, Journal of Cloud Computing (Springer, 2025), https://doi.org/10.1186/s13677-025-00768-3

Official docs: https://docs.contiki-ng.org/en/master/doc/tutorials/Running-Contiki-NG-in-Cooja.html ; https://docs.contiki-ng.org/en/master/doc/programming/Energest.html ; https://docs.contiki-ng.org/en/master/doc/getting-started/Toolchain-installation-on-macOS.html

## Directory layout

```
run_demo.py                 # Python single-run comparison, CSV and plots
run_research.py             # multi-seed repetitions
simulator/engine.py         # complete energy + PSO + proposed trigger model
tests/test_engine.py        # reproducibility and energy-model checks
export_cooja_policy.py      # compute replayed assignments for Contiki nodes
cooja/root.c                # RPL root, assignment control, aggregation counts
cooja/node.c                # sensor/cluster-head firmware, UDP, Energest
cooja/message.h             # consistent packet framing
cooja/policy.h              # generated PSO schedule
make_cooja_scenario.py      # builds .csc from official upstream template
install_cooja.sh            # install into Contiki-NG examples folder
results/                     # generated CSV, static HTML dashboard, plots
docs/DEMO_SCRIPT.md         # oral presentation guide
```

## 8. Optional: Summarize an actual Cooja run

In Cooja, export or copy the **Mote output** log to a plain text file such as `cooja-run.txt`. Analyze it using:

```bash
python3 parse_cooja_log.py cooja-run.txt --out results
```

This produces `results/cooja_energest.csv` and `cooja_report.json`: per-mote accumulated TX/RX/CPU ticks, assignment-message counts and aggregated sample counts. Compare equal-duration runs. Do **not** label the tick count as energy in Joules until calibrated with per-mode current draw, voltage, and `ENERGEST_SECOND` for the selected platform.
