"""One source of truth for room bounds, enemy placement, progression and QA."""
ROOMS = [
    # name, west X, east X, half-width, ceiling Z, roof
    ('ArrivalCourtyard', 0, 2200, 1300, 1000, False),
    ('EntryPassage', 2200, 4200, 450, 950, True),
    ('RuinedMemoryChamber', 4200, 6300, 1100, 1150, True),
    ('StorySanctum', 6300, 8200, 950, 1150, True),
    ('FirstGuardCourt', 8200, 10600, 1350, 1150, False),
    ('InnerPassage', 10600, 12400, 450, 950, True),
    ('CombatChamber', 12400, 15700, 1500, 1250, True),
    ('MemoryVestibule', 15700, 17400, 900, 1100, True),
    ('GrandHall', 17400, 23600, 2500, 1650, True),
    ('QuietStudy', 23600, 25900, 1100, 1100, True),
    ('StoryGateCourt', 25900, 28400, 1500, 1350, False),
]
ENEMIES = [
    ('Guard_01', 0, False, (9550, 0, 100)),
    ('Guard_02', 1, False, (13000, -420, 100)),
    ('Guard_03', 1, False, (13250, 450, 100)),
    ('Guard_04', 1, False, (14800, -380, 100)),
    ('Guard_05', 1, True,  (14900, 450, 100)),
    ('Guard_06', 2, False, (18700, -1000, 100)),
    ('Guard_07', 2, False, (19000, 1000, 100)),
    ('Guard_08', 2, False, (21300, -1100, 100)),
    ('Guard_09', 2, False, (22000, 1050, 100)),
    ('Guard_10', 2, True,  (22500, -800, 100)),
]
INTERACTIONS = [
    # label, kind, position at floor, safe respawn (capsule centre), required group, prompt
    ('StoryCharacter', 'Story', (7460, 340, 0), (7600, 0, 100), -1, 'Listen'),
    ('FirstMemoryLamp', 'Shrine', (16500, 300, 0), (16600, 0, 100), 1, 'Hold this memory / restore health'),
    ('StudyClue', 'Memory', (24800, 330, 0), (25000, 0, 100), 2, 'Remember the empty chair'),
    ('FinalStoryGate', 'End', (27800, 0, 0), (27300, 0, 100), 2, 'Turn the page'),
    ('OptionalToy', 'Fragment', (5270, 1580, 0), (5300, 0, 100), -1, 'Examine the wooden horse'),
]
SEALS = [
    # X, required encounter, requires sword, requires memory
    (8130, -1, True, False), (10570, 0, True, False),
    (15670, 1, True, False), (23570, 2, True, False),
    (25870, 2, True, True),
]
PLAYER_START = (600, 0, 100)


def walkable(x, y):
    return any(a <= x <= b and abs(y) < w-80 for _,a,b,w,_,_ in ROOMS) or (4800<x<5700 and 1000<y<1900)
