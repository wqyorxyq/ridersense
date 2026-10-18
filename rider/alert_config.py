# SPDX-License-Identifier: AGPL-3.0-only
"""Editable demonstration parameters, not a calibrated collision model."""
CONFIG = dict(area_full=.35, growth_full=.15, distance_far=12., distance_near=1.,
              closing_full=6., alpha=.45, exit_margin=5., direction_margin=.025,
              edges=[.18,.4,.6,.82], angle_edges=[-55.,-15.,15.,55.],
              medium=40., high=70., medium_min=.2, medium_max=.5, switch_margin=10., max_gap=.8,
              max_relative_speed=20., max_area_jump=.2,
              area_weights=[.85,.15], metric_weights=[.3,.15,.4,.15])
HIGH = {'left':{1:.8}, 'right':{2:.8}, 'rear_left':{1:.2,2:.8},
        'rear_right':{3:.8,4:.2}, 'rear':{2:.8,3:.8}}
MEDIUM = {'left':[], 'right':[], 'rear_left':[2], 'rear_right':[3], 'rear':[2,3]}
DIRECTIONS = ['right','rear_right','rear','rear_left','left']

def level_for(score, previous=0):
    if score > CONFIG['high']: return 2
    if previous == 2 and score > CONFIG['high']-CONFIG['exit_margin']: return 2
    if score > CONFIG['medium']: return 1
    if previous and score > CONFIG['medium']-CONFIG['exit_margin']: return 1
    return 0

def channels(direction, score, level=None):
    level = level_for(score) if level is None else level
    output = {i:0. for i in range(1,5)}
    if level == 2: output.update(HIGH.get(direction,{}))
    elif level == 1:
        fraction=max(0.,min(1.,(score-CONFIG['medium'])/(CONFIG['high']-CONFIG['medium'])))
        strength = CONFIG['medium_min']+(CONFIG['medium_max']-CONFIG['medium_min'])*fraction
        output.update({i:strength for i in MEDIUM.get(direction,[])})
    return output
