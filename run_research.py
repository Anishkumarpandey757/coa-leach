#!/usr/bin/env python3
"""Repeated paired-seed experiment for descriptive mean ± standard deviation.
FND/HND/LND events not observed are kept as censored (missing), not treated as 0.
"""
import argparse,csv
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from simulator.engine import Config, simulate, PROTOCOLS

METHODS=PROTOCOLS

def run_one(job):
    cfg,name=job
    return simulate(cfg,name)['summary']

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--seeds',type=int,default=5)
    ap.add_argument('--nodes',type=int,default=60)
    ap.add_argument('--rounds',type=int,default=600)
    ap.add_argument('--out',default='results')
    ap.add_argument('--workers',type=int,default=None)
    ap.add_argument('--legacy',action='store_true',help='original rules: weak nodes may stay heads, E-LEACH pays no status cost')
    opt=ap.parse_args()
    jobs=[(Config(nodes=opt.nodes,rounds=opt.rounds,seed=seed,pso_particles=9,pso_iterations=10,
                  exclude_weak_heads=not opt.legacy,eleach_status_cost=not opt.legacy),name)
          for seed in range(1,opt.seeds+1) for name in METHODS]
    records=[]
    with ProcessPoolExecutor(max_workers=opt.workers) as pool:
        for (cfg,name),rec in zip(jobs,pool.map(run_one,jobs)):
            print(f'Seed {cfg.seed}/{opt.seeds}: {name} FND={rec["fnd"]} HND={rec["hnd"]}',flush=True)
            records.append(rec)
    out=Path(opt.out);out.mkdir(parents=True,exist_ok=True)
    with (out/'multiseed_raw.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=records[0].keys())
        writer.writeheader();writer.writerows(records)
    with (out/'multiseed_summary.csv').open('w',newline='') as file:
        writer=csv.writer(file)
        writer.writerow(['protocol','n','mean_alive','sd_alive','mean_control_energy_j','sd_control_energy_j',
                         'mean_reconfigurations','sd_reconfigurations','mean_packets','sd_packets',
                         'fnd_observed_count','mean_fnd_observed_only','sd_fnd',
                         'hnd_observed_count','mean_hnd_observed_only','sd_hnd'])
        for name in METHODS:
            rows=[r for r in records if r['protocol']==name]
            def stats(col):
                a=np.array([r[col] for r in rows],dtype=float)
                return float(a.mean()),float(a.std(ddof=1) if len(a)>1 else 0)
            def event(col):
                v=[r[col] for r in rows if r[col] is not None]
                if not v: return [0,'censored','']
                return [len(v),float(np.mean(v)),float(np.std(v,ddof=1)) if len(v)>1 else 0.]
            writer.writerow([name,len(rows),*stats('final_alive'),*stats('control_energy_j'),
                             *stats('reconfigurations'),*stats('data_packets_generated'),
                             *event('fnd'),*event('hnd')])
    print('Saved:',out/'multiseed_raw.csv',out/'multiseed_summary.csv')

if __name__=='__main__':main()
