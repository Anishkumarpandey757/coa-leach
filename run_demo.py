#!/usr/bin/env python3
"""Run energy model comparisons and export publication-preparation figures."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulator.engine import Config, simulate, PROTOCOLS


def csv_write(path, rows):
    if not rows: return
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def figures(results, out):
    plots = [('alive','Alive sensor nodes','alive_nodes.png'),
             ('total_energy_j','Residual network energy (J)','residual_energy.png'),
             ('cumulative_control_energy_j','Cumulative control energy (J)','control_overhead.png'),
             ('reconfigurations','Cluster reconfiguration count','reconfigurations.png')]
    for key, ylabel, filename in plots:
        fig, ax = plt.subplots(figsize=(9,4.8))
        for name, res in results.items():
            if name.startswith("_"): continue
            ax.plot([x['round'] for x in res['trace']], [x[key] for x in res['trace']], label=name, lw=2)
        ax.set(xlabel='Network round', ylabel=ylabel)
        ax.grid(alpha=.2); ax.legend(fontsize=8, ncol=2, loc='best'); fig.tight_layout()
        fig.savefig(out / filename, dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8,4.8))
    names = [x for x in results if not x.startswith("_")]
    vals = [results[x]['summary']['control_energy_j'] for x in names]
    ax.bar(names, vals)
    ax.set(ylabel='Control-message energy (J)', title='Re-clustering and status-report cost')
    ax.tick_params(axis='x', labelrotation=20); fig.tight_layout()
    fig.savefig(out/'comparison.png',dpi=160); plt.close(fig)
    # Snapshot for selected method
    c = results['COA-APSO-LEACH']
    pos, snap = c['xy'], c['snapshot']
    if snap:
        fig, ax = plt.subplots(figsize=(7,6))
        heads=np.asarray(snap['ch']); assignment=np.asarray(snap['assignment'])
        for i, h in enumerate(assignment):
            if h >= 0 and i != h:
                ax.plot([pos[i,0],pos[h,0]],[pos[i,1],pos[h,1]],color='#8baac0',alpha=.28,lw=.8)
        ax.scatter(pos[:,0],pos[:,1],s=25,label='Sensor')
        ax.scatter(pos[heads,0],pos[heads,1],s=150,marker='*',label='Cluster head',zorder=4)
        ax.scatter([results['_bs'][0]],[results['_bs'][1]],s=140,marker='s',label='Base station')
        ax.legend(); ax.set(xlabel='X (m)',ylabel='Y (m)',title='COA-APSO-LEACH initial cluster assignment')
        fig.tight_layout(); fig.savefig(out/'topology.png',dpi=160); plt.close(fig)


def html_report(results, out, config):
    from html import escape
    cols=['protocol','fnd','hnd','lnd','final_alive','control_energy_j','reconfigurations','reconfigs_rejected']
    header=''.join(f'<th>{escape(k)}</th>' for k in cols)
    rows=''.join('<tr>'+''.join(f'<td>{escape(str(res["summary"].get(k, "")))}</td>' for k in cols)+'</tr>' for name,res in results.items() if not name.startswith('_'))
    images=''.join(f'<figure><img loading="lazy" src="{name}" alt="{name}"><figcaption>{name.replace("_"," ")}</figcaption></figure>' for name in ['topology.png','alive_nodes.png','residual_energy.png','control_overhead.png','reconfigurations.png','comparison.png'])
    (out/'dashboard.html').write_text(f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>COA-APSO-LEACH Research Demo</title><style>body{{font:16px system-ui,sans-serif;color:#1c2934;background:#f4f7fa;max-width:1250px;margin:auto;padding:25px}}h1{{color:#123d63}}table{{border-collapse:collapse;overflow-x:auto;display:block;background:white}}td,th{{border-bottom:1px solid #ddd;padding:12px;text-align:left}}th{{background:#dcecf7}}.graphs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:18px}}figure{{margin:0;background:white;padding:12px;border-radius:12px;box-shadow:0 2px 10px #0001}}img{{max-width:100%}}figcaption{{text-align:center;font-size:14px;color:#526171}}p{{line-height:1.5}}code{{background:#e8edf3;padding:3px}}</style></head><body><h1>COA-APSO-LEACH: Research Simulation Dashboard</h1><p><strong>Model-based results, not Contiki Energest measurements.</strong> Network nodes: {config.nodes}; rounds: {config.rounds}; seed: {config.seed}. An absent FND/HND/LND means the event did not occur in the configured horizon. APSO, PSO and COA use centrally computed optimization.</p><h2>Protocol comparison</h2><table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table><h2>Plots</h2><div class="graphs">{images}</div><h2>Research interpretation</h2><p>Improvement is a hypothesis, not guaranteed. Check whether the proposed protocol consumes less <em>total</em> energy and control energy while maintaining or extending FND/HND under matched inputs. The energy simulator uses first-order radio costs and ideal packet delivery. Cooja radio behavior is modeled separately.</p></body></html>''',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description='Energy-aware WSN research demo')
    p.add_argument('--nodes',type=int,default=60)
    p.add_argument('--rounds',type=int,default=250)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--area',type=float,default=100.)
    p.add_argument('--clusters',type=int,default=5)
    p.add_argument('--out',default='results')
    p.add_argument('--particles',type=int,default=9)
    p.add_argument('--iterations',type=int,default=10)
    p.add_argument('--homogeneous',action='store_true')
    p.add_argument('--legacy',action='store_true',help='original rules: weak nodes may stay heads, E-LEACH pays no status cost')
    args=p.parse_args()
    if args.nodes < 5 or args.clusters<1 or args.clusters>args.nodes: p.error('nodes >= 5; 1 <= clusters <= nodes')
    c=Config(nodes=args.nodes,rounds=args.rounds,seed=args.seed,area=args.area,clusters=args.clusters,
             pso_particles=args.particles,pso_iterations=args.iterations,hetero=not args.homogeneous,
             bs_x=args.area/2,bs_y=args.area*1.25,
             exclude_weak_heads=not args.legacy,eleach_status_cost=not args.legacy)
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    results={}
    for name in PROTOCOLS:
        print('Running',name,flush=True)
        results[name]=simulate(c,name,capture=name=='COA-APSO-LEACH')
        csv_write(out/f'{name.lower()}_rounds.csv',results[name]['trace'])
    summary=[results[k]['summary'] for k in PROTOCOLS]
    csv_write(out/'summary.csv',summary)
    (out/'config.json').write_text(json.dumps(vars(c),indent=2))
    (out/'changes.json').write_text(json.dumps(results['COA-APSO-LEACH']['changes'],indent=2))
    results['_bs']=(c.bs_x,c.bs_y)
    figures({k:v for k,v in results.items() if not k.startswith('_')} | {'_bs':results['_bs']},out)
    html_report(results,out,c)
    print('\nResults:')
    for s in summary:
        print(f"  {s['protocol']:<18} FND={str(s['fnd']):<5} HND={str(s['hnd']):<5} alive={s['final_alive']:<4} control={s['control_energy_j']:.4f} J, reconfig={s['reconfigurations']}")
    print('\nOpen:',out/'dashboard.html')

if __name__=='__main__': main()
