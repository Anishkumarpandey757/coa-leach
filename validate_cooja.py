"""Create a 10-minute Cooja smoke-test scenario beside demo.csc.

Run in Ubuntu: python3 validate_cooja.py ~/coa-demo/contiki-ng
Then use Cooja --no-gui with the generated validation.csc.
"""
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

repo = Path(sys.argv[1]).expanduser().resolve()
folder = repo / 'examples' / 'coa-apso-leach'
tree = ET.parse(folder / 'demo.csc')
root = tree.getroot()
for plugin in list(root.findall('plugin')):
    root.remove(plugin)
plugin = ET.SubElement(root, 'plugin')
plugin.text = 'org.contikios.cooja.plugins.ScriptRunner'
config = ET.SubElement(plugin, 'plugin_config')
ET.SubElement(config, 'script').text = '''
var configs = {}, energy = {}, members = 0, clusters = 0, aggregates = 0;
TIMEOUT(600000);
timeout_function = function() {
  if (Object.keys(configs).length == 8 && Object.keys(energy).length == 8
      && members > 0 && clusters > 0 && aggregates > 0) {
    log.testOK();
  } else {
    log.log("Missing configuration, energy, or packet evidence\\n");
    log.testFailed();
  }
};
while (true) {
  log.log(time + " ID:" + id + " " + msg + "\\n");
  if (msg.indexOf("CONFIG id=") >= 0) configs[id] = true;
  if (msg.indexOf("ENERGEST id=") >= 0) energy[id] = true;
  if (msg.indexOf("MEMBER DATA") >= 0) members++;
  if (msg.indexOf("CLUSTER RX") >= 0) clusters++;
  if (msg.indexOf("AGG head=") >= 0) aggregates++;
  YIELD();
}
'''
ET.SubElement(config, 'active').text = 'true'
ET.indent(tree, space='  ')
tree.write(folder / 'validation.csc', encoding='UTF-8', xml_declaration=True)
print(folder / 'validation.csc')
