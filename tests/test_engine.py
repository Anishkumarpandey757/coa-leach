import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from simulator.engine import Config, topology, tx, rx, simulate, D0, pso_heads, setup_energy, assign_nodes, PROTOCOLS

def test_radio_model():
    assert tx(1000,10) > rx(1000)
    assert tx(1000,100)>tx(1000,50)
    assert 0 < D0 < 100

def test_fair_topology():
    c=Config(nodes=20,seed=8)
    a,b=topology(c); x,y=topology(c)
    np.testing.assert_array_equal(a,x)
    np.testing.assert_array_equal(b,y)

def test_protocols_energy_nonnegative():
    for method in PROTOCOLS:
        for legacy in (False, True):
            r=simulate(Config(nodes=15,rounds=20,pso_iterations=3,pso_particles=3,clusters=3,
                              exclude_weak_heads=not legacy,eleach_status_cost=not legacy),method)
            vals=[t['total_energy_j'] for t in r['trace']]
            assert all(x >= 0 for x in vals)
            assert all(b <= a + 1e-9 for a,b in zip(vals,vals[1:]))
            assert r['summary']['reconfigurations'] >= 1

def test_weak_nodes_excluded_from_heads():
    c=Config(nodes=30,clusters=3,pso_iterations=3,pso_particles=4,seed=3)
    xy,init=topology(c)
    energy=init.copy(); energy[:20]=init[:20]*.05
    heads=pso_heads(xy,energy,init,np.array([50.,125.]),c,np.random.default_rng(1))
    assert np.all(energy[heads]/init[heads] >= c.ch_min_fraction)

def test_eleach_pays_status_cost():
    base=dict(nodes=15,rounds=30,clusters=3)
    paid=simulate(Config(**base),'E-LEACH')['summary']['control_energy_j']
    free=simulate(Config(**base,eleach_status_cost=False),'E-LEACH')['summary']['control_energy_j']
    assert paid > free

def test_reclustering_cost_positive():
    c=Config(nodes=12,seed=4)
    xy, energy=topology(c)
    heads=np.array([0,1,2]); assign=assign_nodes(xy,energy>0,heads)
    setup=setup_energy(xy,energy>0,heads,assign)
    assert setup.sum()>0
    assert np.all(setup>=0)

def test_pso_heads_are_actual_nodes():
    c=Config(nodes=15,clusters=3,pso_iterations=3,pso_particles=4)
    xy,init=topology(c)
    heads=pso_heads(xy,init,init,np.array([50.,125.]),c,np.random.default_rng(5))
    assert len(heads)==3 and len(set(heads))==3
    assert all(0<=int(x)<c.nodes for x in heads)


def test_parse_cooja_logs():
    from parse_cooja_log import parse
    s='1 INFO ASSIGN node=2 head=8 epoch=1\n2 INFO ENERGEST id=2 tx_ticks=234 rx_ticks=1103 cpu_ticks=66\n1 INFO AGG head=8 epoch=1 samples=3\n'
    out=parse(s)
    assert out['assignments_sent']==1
    assert out['samples_aggregated']==3
    assert out['tx_ticks_sum']==234
