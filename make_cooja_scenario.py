#!/usr/bin/env python3
"""Generate ready-to-open .csc from an official Contiki-NG example.
Usage: python make_cooja_scenario.py /path/to/contiki-ng
"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from export_cooja_policy import POSITIONS


def generate(repo: Path):
    example=repo/'examples'/'rpl-udp'/'rpl-udp-cooja.csc'
    if not example.exists(): raise SystemExit(f'Cannot find official template: {example}')
    tree=ET.parse(example)
    root=tree.getroot()
    sim=root.find('simulation')
    sim.find('title').text='COA-APSO-LEACH 9-node WSN Demo'
    sim.find('randomseed').text='123456'
    medium=sim.find('radiomedium')
    for element in medium:
        if element.tag == 'transmitting_range': element.text='70.0'
        if element.tag == 'interference_range': element.text='90.0'
    types=sim.findall('motetype')
    if len(types)<2: raise SystemExit('Template does not contain both root and client Cooja mote types')
    for entry,name,desc in [(types[0],'root','COA-APSO Root'),(types[1],'node','COA-APSO Sensor')]:
        entry.find('description').text=desc
        entry.find('source').text=f'[CONTIKI_DIR]/examples/coa-apso-leach/{name}.c'
        entry.find('commands').text=f'$(MAKE) -j$(CPUS) {name}.cooja TARGET=cooja'
    for old in list(sim.findall('mote')): sim.remove(old)
    locs=[(50,50)] + [tuple(x) for x in POSITIONS]
    for idx, (x,y) in enumerate(locs,start=1):
        mote=ET.SubElement(sim,'mote')
        pos=ET.SubElement(mote,'interface_config')
        pos.text='org.contikios.cooja.interfaces.Position\n        '
        for tag,value in [('x',x),('y',y),('z',0)]:
            ET.SubElement(pos,tag).text=str(float(value))
        id_config=ET.SubElement(mote,'interface_config')
        id_config.text='org.contikios.cooja.contikimote.interfaces.ContikiMoteID\n        '
        ET.SubElement(id_config,'id').text=str(idx)
        ET.SubElement(mote,'motetype_identifier').text=types[0].find('identifier').text if idx==1 else types[1].find('identifier').text
    # The upstream example has more motes and an App-only log filter.
    # Keep plugin references within this nine-mote scenario and show our logs.
    for plugin in root.findall('plugin'):
        config = plugin.find('plugin_config')
        if config is None:
            continue
        for mote in list(config.findall('mote')):
            if int(mote.text) >= len(locs):
                config.remove(mote)
        if 'LogListener' in (plugin.text or ''):
            for log_filter in list(config.findall('filter')):
                config.remove(log_filter)
    ET.indent(tree,space='  ')
    target=repo/'examples'/'coa-apso-leach'/'demo.csc'
    tree.write(target,encoding='UTF-8',xml_declaration=True)
    print('Generated Cooja scenario:',target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('contiki_path',type=Path)
    generate(p.parse_args().contiki_path.resolve())
