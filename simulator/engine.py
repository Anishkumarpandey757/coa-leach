"""COA-APSO-LEACH: reproducible research *simulation*, not measured hardware.

Radio model: first-order E_elec + amplifier, as commonly used in WSN simulation.
No claims about empirical hardware energy or radio reliability are made.
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np

E_ELEC = 50e-9
E_DA = 5e-9
EPS_FS = 10e-12
EPS_MP = 0.0013e-12
D0 = np.sqrt(EPS_FS / EPS_MP)
DATA_BITS = 4000
CTRL_BITS = 128


def tx(bits, d):
    d = np.asarray(d, dtype=float)
    return bits * (E_ELEC + np.where(d < D0, EPS_FS * d**2, EPS_MP * d**4))


def rx(bits):
    return bits * E_ELEC


@dataclass
class Config:
    nodes: int = 100
    rounds: int = 500
    area: float = 100.0
    seed: int = 42
    bs_x: float = 50.0
    bs_y: float = 125.0
    hetero: bool = True
    clusters: int = 5
    pso_particles: int = 10
    pso_iterations: int = 12
    period: int = 15
    check_period: int = 15
    lookahead: int = 15
    setup_margin: float = 1.15
    ch_min_fraction: float = .22
    hybrid_routing: bool = True
    # False/False reproduces the original (pre-fix) behaviour of every protocol
    exclude_weak_heads: bool = True
    eleach_status_cost: bool = True
    # COA-APSO-LEACH-SA (survival-aware) parameters
    guard_rounds: int = 3
    drain_tolerance: float = .10
    survival_weight: float = .20
    survival_horizon: int = 30
    sa_above_average: bool = True


def topology(c: Config):
    rng = np.random.default_rng(c.seed)
    xy = rng.uniform(0, c.area, size=(c.nodes, 2))
    initial = np.full(c.nodes, .5)
    if c.hetero:
        kinds = rng.choice([0, 1, 2], size=c.nodes, p=[.70, .23, .07])
        initial = np.select([kinds == 0, kinds == 1, kinds == 2], [.5, 1., 2.])
    return xy, initial.astype(float)


def decode_cluster_heads(position, eligible, xy, k):
    """Map continuous PSO positions to k distinct *existing* sensor nodes."""
    chosen = []
    for point in position.reshape(k, 2):
        dsq = np.sum((xy[eligible] - point)**2, axis=1)
        for idx in np.argsort(dsq):
            candidate = int(eligible[idx])
            if candidate not in chosen:
                chosen.append(candidate)
                break
    if len(chosen) < k:
        for node in eligible:
            if int(node) not in chosen:
                chosen.append(int(node))
                if len(chosen) == k: break
    return np.asarray(chosen, dtype=int)


def assign_nodes(xy, alive, ch):
    ids = np.flatnonzero(alive)
    dist2 = np.sum((xy[ids, None, :] - xy[ch][None, :, :])**2, axis=2)
    nearest = np.argmin(dist2, axis=1)
    assignment = np.full(len(xy), -1, dtype=int)
    assignment[ids] = ch[nearest]
    assignment[ch] = ch
    return assignment


def cluster_energy(xy, energy, initial, ch, bs, hybrid):
    """Energy vector for one data-gathering round, given alive nodes."""
    alive = energy > 0
    out = np.zeros(len(xy))
    if len(ch) == 0 or not alive.any(): return out, np.full(len(xy), -1)
    assignment = assign_nodes(xy, alive, ch)
    member_ids = np.flatnonzero(alive & ~np.isin(np.arange(len(xy)), ch))
    if member_ids.size:
        ds = np.linalg.norm(xy[member_ids] - xy[assignment[member_ids]], axis=1)
        out[member_ids] += tx(DATA_BITS, ds)
        np.add.at(out, assignment[member_ids], rx(DATA_BITS) + DATA_BITS * E_DA)
    out[ch] += DATA_BITS * E_DA  # aggregate each CH's own measurement
    for source in ch:
        direct_d = np.linalg.norm(xy[source] - bs)
        direct = float(tx(DATA_BITS, direct_d))
        choice = -1
        best = direct
        if hybrid and len(ch) > 1:
            for dest in ch:
                if dest == source or energy[dest] < .12 * initial[dest]: continue
                first = np.linalg.norm(xy[source] - xy[dest])
                second = np.linalg.norm(xy[dest] - bs)
                cost = float(tx(DATA_BITS, first)) + rx(DATA_BITS) + float(tx(DATA_BITS, second))
                if cost < best:
                    best, choice = cost, int(dest)
        if choice == -1:
            out[source] += direct
        else:
            out[source] += float(tx(DATA_BITS, np.linalg.norm(xy[source] - xy[choice])))
            out[choice] += rx(DATA_BITS) + float(tx(DATA_BITS, np.linalg.norm(xy[choice] - bs)))
    return out, assignment


def setup_energy(xy, alive, ch, assignment):
    """Cluster formation: CH advertisement + join request + schedule broadcast.

    All estimates are energy-model accounting, not Contiki packet measurements.
    """
    out = np.zeros(len(xy))
    ids = np.flatnonzero(alive)
    for head in ch:
        members = ids[assignment[ids] == head]
        other = members[members != head]
        # two cluster-head advertisements/schedules (broadcast model)
        range_m = max([np.linalg.norm(xy[head] - xy[m]) for m in other], default=1.)
        out[head] += 2 * float(tx(CTRL_BITS, range_m))
        out[other] += 2 * rx(CTRL_BITS)
        # Each member joins its head
        if len(other):
            ds = np.linalg.norm(xy[other] - xy[head], axis=1)
            out[other] += tx(CTRL_BITS, ds)
            out[head] += len(other) * rx(CTRL_BITS)
    return out


def status_energy(xy, alive, bs):
    """Status reporting overhead when controller obtains current energies."""
    out = np.zeros(len(xy))
    ids = np.flatnonzero(alive)
    out[ids] += tx(CTRL_BITS, np.linalg.norm(xy[ids] - bs, axis=1))
    return out


def healthy_candidates(energy, initial, c):
    """Alive nodes above the CH energy floor, or None when too few remain to fill k heads."""
    eligible = np.flatnonzero(energy > 0)
    healthy = eligible[energy[eligible] / initial[eligible] >= c.ch_min_fraction]
    return healthy if len(healthy) >= min(c.clusters, len(eligible)) else None


def score_heads(xy, energy, initial, ch, bs, hybrid, survival_weight=0., horizon=30):
    vals, assignment = cluster_energy(xy, energy, initial, ch, bs, hybrid)
    ids = np.flatnonzero(energy > 0)
    loads = np.array([np.count_nonzero(assignment[ids] == h) for h in ch])
    k = max(len(ch), 1)
    relative = energy[ch] / initial[ch]
    # Numerical magnitudes normalized for straightforward weight interpretation.
    norm_energy = float(vals.sum()) / max(len(ids) * float(tx(DATA_BITS, 35)), 1e-9)
    imbalance = float(np.std(loads)) / max(len(ids) / k, 1.)
    scarcity = float(np.mean(1 - relative))
    dispersion = float(np.std(relative))
    score = .65 * norm_energy + .16 * imbalance + .14 * scarcity + .05 * dispersion
    if survival_weight:
        # fraction of heads predicted to exhaust their battery within the horizon
        rounds_left = energy[ch] / np.maximum(vals[ch], 1e-12)
        score += survival_weight * float(np.mean(rounds_left < horizon))
    return score


def pso_heads(xy, energy, initial, bs, c, rng, adaptive=True, previous=None, survival=False):
    eligible = np.flatnonzero(energy > 0)
    k = min(c.clusters, len(eligible))
    if c.exclude_weak_heads:
        healthy = healthy_candidates(energy, initial, c)
        if healthy is not None:
            eligible = healthy
    if survival and c.sa_above_average:
        relative = energy[eligible] / initial[eligible]
        strong = eligible[relative >= relative.mean()]
        if len(strong) >= k:
            eligible = strong
    if previous is not None and not np.all(np.isin(previous, eligible)):
        previous = None
    sw = c.survival_weight if survival else 0.
    if k == 0: return np.asarray([], dtype=int)
    n = c.pso_particles
    particles = rng.uniform(0, c.area, (n, k * 2))
    if previous is not None and len(previous) == k:
        particles[0] = xy[previous].reshape(-1)
    velocities = rng.uniform(-1, 1, particles.shape) * (c.area / 10)
    local_best = particles.copy()
    local_score = np.full(n, np.inf)
    global_score = np.inf
    global_best = particles[0].copy()
    for iteration in range(c.pso_iterations):
        for j in range(n):
            heads = decode_cluster_heads(particles[j], eligible, xy, k)
            fitness = score_heads(xy, energy, initial, heads, bs, c.hybrid_routing, sw, c.survival_horizon)
            if fitness < local_score[j]:
                local_score[j] = fitness
                local_best[j] = particles[j].copy()
            if fitness < global_score:
                global_score = fitness
                global_best = particles[j].copy()
        progress = iteration / max(1, c.pso_iterations - 1)
        inertia = .45 + .45 * .5 * (1 + np.cos(np.pi * progress)) if adaptive else .70
        velocities = inertia * velocities + 1.6 * rng.random(particles.shape) * (local_best - particles) + 1.6 * rng.random(particles.shape) * (global_best - particles)
        velocities = np.clip(velocities, -c.area / 4, c.area / 4)
        particles = np.clip(particles + velocities, 0, c.area)
    return decode_cluster_heads(global_best, eligible, xy, k)


def leach_heads(energy, last_ch, rnd, c, rng):
    eligible = np.flatnonzero(energy > 0)
    if len(eligible) == 0: return np.asarray([], dtype=int)
    k = min(c.clusters, len(eligible))
    epoch = max(1, int(round(len(eligible) / k)))
    period = rnd % epoch
    valid = eligible[last_ch[eligible] <= rnd - epoch]
    if len(valid) == 0: valid = eligible
    # Canonical LEACH threshold approximation for fixed-p node election
    p = 1.0 / epoch
    threshold = min(1., p / max(1e-8, 1. - p * period))
    heads = valid[rng.random(len(valid)) < threshold]
    if len(heads) == 0: heads = rng.choice(valid, size=1, replace=False)
    last_ch[heads] = rnd
    return np.asarray(heads, dtype=int)


PROTOCOLS = ('LEACH', 'E-LEACH', 'PSO-LEACH', 'APSO-LEACH', 'COA-APSO-LEACH', 'COA-APSO-LEACH-SA')


def simulate(c: Config, protocol: str, capture=False, layout=None):
    """layout: optional (positions, initial_energy) replacing the random topology, e.g. the Cooja motes."""
    if protocol not in PROTOCOLS:
        raise ValueError('Unknown protocol: ' + protocol)
    if layout is None:
        xy, initial = topology(c)
    else:
        xy, initial = np.asarray(layout[0], dtype=float), np.asarray(layout[1], dtype=float)
    energy = initial.copy()
    bs = np.array([c.bs_x, c.bs_y])
    # Same geographic and battery topology across protocols, distinct stochastic stream
    rng = np.random.default_rng(c.seed + 2000 + {'LEACH':0,'E-LEACH':1,'PSO-LEACH':2,'APSO-LEACH':3,'COA-APSO-LEACH':3,'COA-APSO-LEACH-SA':3}[protocol])
    ch = np.asarray([], dtype=int)
    last_used = np.zeros(c.nodes)
    assignment = np.full(c.nodes, -1, dtype=int)
    last_ch = np.full(c.nodes, -1000000, dtype=int)
    cumulative_overhead = 0.
    overhead_messages = 0
    reconfigurations = 0
    rejected = 0
    packets = 0
    total_data_bits = 0
    trace = []
    changes = []
    initial_ch = None
    fnd = hnd = lnd = None
    initial_snapshot = None
    for rnd in range(c.rounds):
        alive = energy > 0
        count = int(alive.sum())
        if count == 0: break
        if count < c.nodes and fnd is None: fnd = rnd
        if count <= c.nodes // 2 and hnd is None: hnd = rnd
        keep = len(ch) > 0 and bool(np.all(energy[ch] > 0))
        healthy = healthy_candidates(energy, initial, c) if c.exclude_weak_heads else None
        weak = bool(len(ch)) and bool(np.any((energy[ch] / initial[ch]) < c.ch_min_fraction))
        if c.exclude_weak_heads and healthy is None:
            weak = False  # no healthy replacement exists, so re-clustering cannot fix it
        emergency = not keep or weak
        updated = False
        if protocol == 'LEACH':
            ch_new = leach_heads(energy, last_ch, rnd, c, rng)
            updated = True
        elif protocol == 'E-LEACH':
            # Prioritize residual energy, still rotate cluster heads every period
            if rnd % c.period == 0 or emergency:
                if c.eleach_status_cost:
                    # residual-energy election needs the same status reports the PSO controllers pay for
                    overhead = status_energy(xy, alive, bs)
                    energy = np.maximum(energy - overhead, 0)
                    cumulative_overhead += float(overhead.sum())
                    overhead_messages += count
                    alive = energy > 0
                eligible = np.flatnonzero(alive)
                if healthy is not None:
                    eligible = eligible[np.isin(eligible, healthy)]
                k = min(c.clusters, len(eligible))
                # Energy-first non-PSO baseline (not a verbatim implementation of IMP-RES-EL)
                ch_new = np.asarray(eligible[np.argsort(-energy[eligible])[:k]], dtype=int)
                updated = True
        elif protocol in ('PSO-LEACH','APSO-LEACH'):
            if rnd % c.period == 0 or emergency:
                overhead = status_energy(xy, alive, bs)
                energy = np.maximum(energy - overhead, 0)
                cumulative_overhead += float(overhead.sum())
                overhead_messages += count
                new = pso_heads(xy, energy, initial, bs, c, rng, adaptive=protocol == 'APSO-LEACH', previous=ch if keep else None)
                ch_new = new
                updated = True
        elif protocol == 'COA-APSO-LEACH':
            if rnd % c.check_period == 0 or emergency:
                status = status_energy(xy, alive, bs)
                energy = np.maximum(energy - status, 0)
                cumulative_overhead += float(status.sum())
                overhead_messages += count
                alive = energy > 0
                prospective = pso_heads(xy, energy, initial, bs, c, rng, adaptive=True, previous=ch if keep else None)
                if not keep or len(prospective) == 0:
                    ch_new, updated = prospective, True
                else:
                    # Current clustering may be aging; compare identical lookahead windows.
                    current_cost = float(cluster_energy(xy, energy, initial, ch, bs, c.hybrid_routing)[0].sum())
                    candidate_cost = float(cluster_energy(xy, energy, initial, prospective, bs, c.hybrid_routing)[0].sum())
                    candidate_a = assign_nodes(xy, alive, prospective)
                    new_setup = setup_energy(xy, alive, prospective, candidate_a)
                    estimated_saving = (current_cost - candidate_cost) * c.lookahead
                    required_saving = c.setup_margin * float(new_setup.sum())
                    # Suppress switches with no actual effect
                    worth_it = set(prospective.tolist()) != set(ch.tolist()) and estimated_saving > required_saving
                    if worth_it or emergency:
                        ch_new, updated = prospective, True
                    else:
                        rejected += 1
        elif protocol == 'COA-APSO-LEACH-SA':
            # Immediate recovery only when a head is predicted to die within guard_rounds;
            # otherwise heads are reviewed on the regular check schedule.
            dying = keep and bool(np.any(energy[ch] < c.guard_rounds * last_used[ch]))
            if rnd % c.check_period == 0 or not keep or dying:
                status = status_energy(xy, alive, bs)
                energy = np.maximum(energy - status, 0)
                cumulative_overhead += float(status.sum())
                overhead_messages += count
                alive = energy > 0
                keep = keep and bool(np.all(energy[ch] > 0))
                prospective = pso_heads(xy, energy, initial, bs, c, rng, adaptive=True,
                                        previous=ch if keep else None, survival=True)
                if not keep or len(prospective) == 0:
                    ch_new, updated = prospective, True
                else:
                    current_used = cluster_energy(xy, energy, initial, ch, bs, c.hybrid_routing)[0]
                    candidate_cost = float(cluster_energy(xy, energy, initial, prospective, bs, c.hybrid_routing)[0].sum())
                    new_setup = setup_energy(xy, alive, prospective, assign_nodes(xy, alive, prospective))
                    estimated_saving = (float(current_used.sum()) - candidate_cost) * c.lookahead
                    worth_it = estimated_saving > c.setup_margin * float(new_setup.sum())
                    relative = energy / initial
                    rounds_left = energy[ch] / np.maximum(current_used[ch], 1e-12)
                    at_risk = (dying or weak
                               or bool(np.any(rounds_left < c.lookahead))
                               or bool(np.any(relative[ch] < relative[alive].mean() - c.drain_tolerance)))
                    changed = set(prospective.tolist()) != set(ch.tolist())
                    if changed and (worth_it or at_risk):
                        ch_new, updated = prospective, True
                    else:
                        rejected += 1
        if updated:
            new_heads = np.asarray(ch_new, dtype=int)
            if not np.array_equal(np.sort(new_heads), np.sort(ch)):
                ch = new_heads
                alive = energy > 0
                if len(ch) > 0:
                    assignment = assign_nodes(xy, alive, ch)
                    setup = setup_energy(xy, alive, ch, assignment)
                    energy = np.maximum(energy - setup, 0)
                    cumulative_overhead += float(setup.sum())
                    overhead_messages += 2 * len(ch) + max(0, count - len(ch))
                    reconfigurations += 1
                    changes.append({'round':rnd, 'heads':[int(x) for x in ch]})
            else:
                ch = new_heads
        # node deaths due to setup may invalidate CHs before data phase
        active_heads = ch[energy[ch] > 0] if len(ch) else ch
        if len(active_heads) > 0:
            used, assignment = cluster_energy(xy, energy, initial, active_heads, bs, c.hybrid_routing)
            active = energy > 0
            packets += int(active.sum())
            total_data_bits += int(active.sum()) * DATA_BITS
            energy = np.maximum(0, energy - used)
        else:
            used = np.zeros(c.nodes)
        last_used = used
        if initial_snapshot is None and len(ch) > 0:
            initial_snapshot = {'ch': ch.tolist(), 'assignment': assignment.tolist()}
        remain = int(np.sum(energy > 0))
        trace.append({'round': rnd+1, 'alive': remain, 'total_energy_j': float(energy.sum()),
                      'round_data_energy_j': float(used.sum()),
                      'cumulative_control_energy_j': cumulative_overhead,
                      'control_messages': overhead_messages, 'reconfigurations': reconfigurations,
                      'rejected_reconfigs': rejected, 'packets_generated': packets})
        if remain == 0:
            lnd = rnd+1
            break
    if trace:
        if fnd is None and trace[-1]['alive'] < c.nodes: fnd = trace[-1]['round']
        if hnd is None and trace[-1]['alive'] <= c.nodes // 2: hnd = trace[-1]['round']
    summary = {'protocol':protocol, 'seed':c.seed, 'nodes':c.nodes, 'rounds_simulated':len(trace),
               'fnd': fnd, 'hnd': hnd, 'lnd': lnd,
               'final_alive': int(np.sum(energy>0)),
               'final_energy_j':float(energy.sum()), 'control_energy_j':cumulative_overhead,
               'control_messages':overhead_messages, 'reconfigurations':reconfigurations,
               'reconfigs_rejected': rejected, 'data_packets_generated':packets,
               'optimization_calls': None}  # PSO compute profiling not measured here
    return {'summary':summary, 'trace':trace, 'xy':xy if capture else None,
            'initial':initial if capture else None, 'snapshot':initial_snapshot,
            'changes':changes if capture else None}
