#!/usr/bin/env python3
"""Summarize saved Cooja mote output: *ticks* are not Joules."""
import re, argparse,csv,json
from pathlib import Path
PATTERN=re.compile(r'ENERGEST id=(\d+) tx_ticks=(\d+) rx_ticks=(\d+) cpu_ticks=(\d+)')
ROOT_ASSIGN=re.compile(r'ASSIGN node=(\d+) head=(\d+) epoch=(\d+)')
ROOT_AGG=re.compile(r'AGG head=(\d+) epoch=(\d+) samples=(\d+)')

def parse(text):
    nodes={}
    configs=[]; aggregates=[]
    for line in text.splitlines():
        m=PATTERN.search(line)
        if m:
            idx,tx,rx,cpu=map(int,m.groups())
            nodes[idx]={'node':idx,'tx_ticks':tx,'rx_ticks':rx,'cpu_ticks':cpu}
        m=ROOT_ASSIGN.search(line)
        if m:
            node,head,epoch=map(int,m.groups());configs.append((node,head,epoch))
        m=ROOT_AGG.search(line)
        if m:
            head,epoch,count=map(int,m.groups());aggregates.append((head,epoch,count))
    return {'nodes':list(nodes.values()),'assignments_sent':len(configs),
            'aggregates':len(aggregates),'samples_aggregated':sum(x[2] for x in aggregates),
            'tx_ticks_sum':sum(x['tx_ticks'] for x in nodes.values()),
            'rx_ticks_sum':sum(x['rx_ticks'] for x in nodes.values()),
            'note':'Cumulative Energest ticks, not energy (J); duration must be matched across runs.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('log_file');p.add_argument('--out',default='results')
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    r=parse(Path(a.log_file).read_text(errors='replace'))
    (out/'cooja_report.json').write_text(json.dumps(r,indent=2))
    if r['nodes']:
        with (out/'cooja_energest.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['node','tx_ticks','rx_ticks','cpu_ticks'])
            writer.writeheader();writer.writerows(sorted(r['nodes'],key=lambda x:x['node']))
    print(json.dumps({k:v for k,v in r.items() if k!='nodes'},indent=2))
    print('Saved:',out/'cooja_report.json')
if __name__=='__main__':main()
