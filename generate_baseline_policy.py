"""Optional: switch firmware to a periodic rotating CH schedule for visual comparison.
Run `python generate_baseline_policy.py`, compile in Cooja, and run same scenario.
Restore optimized generated policy with `python export_cooja_policy.py`.
This baseline is illustrative rotation, NOT LEACH's randomized threshold algorithm.
"""
from pathlib import Path
from simulator.engine import assign_nodes
from export_cooja_policy import POSITIONS
import numpy as np

def main():
    e=[]
    for epoch in range(6):
        heads=np.asarray([epoch % 2, 2 + epoch % 2, 4 + epoch % 2, 6 + epoch % 2])
        e.append(assign_nodes(POSITIONS,np.ones(8,dtype=bool),heads).tolist())
    body='\n'.join('  {'+','.join(str(i+2) for i in row)+'},' for row in e)
    code=f'''#ifndef COA_POLICY_H
#define COA_POLICY_H
#include <stdint.h>
#define COA_EPOCHS 6
#define COA_POLICY_NAME "periodic-rotation"
/* Demo-only periodic CH rotation; not standard LEACH. */
static const uint8_t COA_ASSIGNMENT[COA_EPOCHS][8] = {{
{body}
}};
#endif
'''
    output=Path(__file__).parent/'cooja'/'policy.h'
    output.write_text(code)
    print('Periodic policy generated:',output)

if __name__=='__main__':main()
