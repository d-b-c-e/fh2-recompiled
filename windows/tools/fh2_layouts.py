#!/usr/bin/env python3
"""Prints FH2's pad action layouts from the game database and checks the wheel ones.

FH2 does not hard-code its controls: sub_8255C410 formats "SELECT * FROM %s%s WHERE LayoutId=%d"
(0x82019B7C) with "Wheel", "Bristol" or "Controller" and "Layouts", and reads the row from
media/db/gamedb.slt (plain SQLite). See docs/wheel-layouts.md.

    python -I fh2_layouts.py <game_root>/media/db/gamedb.slt          # print every layout
    python -I fh2_layouts.py <game_root>/media/db/gamedb.slt --check  # exit 1 if WheelLayouts differ
"""
import sqlite3
import sys
from pathlib import Path

# WheelLayouts as read from gamedb.slt of disc 15E4FA3D v0.0.0.6 (2026-10-23). The three rows
# differ only in ButtonB, ButtonX and ButtonY.
_COMMON = {'LeftThumbUp': 'Handbrake', 'LeftThumbDown': 'Handbrake', 'LeftThumbButton': '',
           'RightThumbUp': 'Clutch', 'RightThumbDown': 'Clutch', 'RightThumbLeft': '',
           'RightThumbRight': '', 'RightThumbButton': '', 'DPadUp': 'CarChallengeInfo',
           'DPadDown': 'LookStraightBack', 'DPadLeft': 'RadioLeft', 'DPadRight': 'RadioRight',
           'ButtonA': 'Handbrake', 'LeftShoulder': 'ShiftDown', 'RightShoulder': 'ShiftUp',
           'LeftTrigger': 'Brake', 'RightTrigger': 'Gas', 'Back': 'SwitchCamera'}
EXPECTED_WHEEL = {
    0: {**_COMMON, 'ButtonB': 'Clutch', 'ButtonX': 'Activate', 'ButtonY': 'Rewind'},
    1: {**_COMMON, 'ButtonB': 'Activate', 'ButtonX': 'Clutch', 'ButtonY': 'Rewind'},
    2: {**_COMMON, 'ButtonB': 'Clutch', 'ButtonX': 'Rewind', 'ButtonY': 'Activate'},
}

# Profile option defaults for the wheel pages (GameOptionCategoryMap group 4, categories 6 and
# 8), resolved through GameOptionValues where the option has named values.
EXPECTED_WHEEL_DEFAULTS = {
    'WheelLayout': 'DefaultLayout=0', 'InvertGearUpDownWheel': 'Off=0', 'RumbleSettingWheel': 'On=1',
    'InvertCameraLookBackWheel': '0', 'InvertHandbrakeClutchWheel': '0', 'Use900DegreeSettings': '1',
    'ForceFeedbackScale': '1',
}
_DEFAULTS_QUERY = """
SELECT o.Token, m.DefValue, v.Token, v.Value FROM GameOptions o
JOIN GameOptionCategoryMap m ON m.OptionId = o.Id AND m.GroupId = 4 AND m.CatId IN (6, 8)
LEFT JOIN GameOptionMap g ON g.OptionId = o.Id AND g.ValueId = m.DefValue
LEFT JOIN GameOptionValues v ON v.Id = g.ValueId"""


# The per-player wheel options as the profile schema defines them (media/profileschema/ForzaProfile.sch). A player's
# saved profile can change any of them; these are only the values a new profile starts with.
EXPECTED_WHEEL_PROFILE = {'Layout': '0', 'RumbleSetting': '1', 'InvertGearUpDown': '0', 'InvertHandbrakeClutch': '0',
                          'InvertCameraLookBack': '0', 'RewindOnBack': '0', 'ActivateOnBack': '0'}


def wheel_profile(db):
    import xml.etree.ElementTree as ET
    schema = Path(db).resolve().parents[1] / 'profileschema' / 'ForzaProfile.sch'
    bag = ET.parse(schema).getroot().find("Property[@name='WheelOptions']")
    return {p.get('name'): p.get('value') for p in bag.findall('Property')}


def connect(db):
    return sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro&immutable=1', uri=True)


def read(db, table):
    con = connect(db)
    try:
        cur = con.execute(f'SELECT * FROM "{table}" ORDER BY LayoutId')
        cols = [c[0] for c in cur.description]
        return {row[0]: dict(zip(cols[1:], row[1:])) for row in cur}
    finally:
        con.close()


def wheel_defaults(db):
    con = connect(db)
    try:
        return {token: (f'{name}={value}' if name else str(default))
                for token, default, name, value in con.execute(_DEFAULTS_QUERY)
                if token in EXPECTED_WHEEL_DEFAULTS}
    finally:
        con.close()


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    db = argv[1]
    if '--check' in argv:
        actual = read(db, 'WheelLayouts')
        if actual != EXPECTED_WHEEL:
            print(f'WheelLayouts differ from the recorded layouts:\n{actual}')
            return 1
        defaults = wheel_defaults(db)
        if defaults != EXPECTED_WHEEL_DEFAULTS:
            print(f'Wheel option defaults differ from the recorded ones:\n{defaults}')
            return 1
        profile = wheel_profile(db)
        if profile != EXPECTED_WHEEL_PROFILE:
            print(f'WheelOptions in the profile schema differ from the recorded ones:\n{profile}')
            return 1
        print(f'WheelLayouts ({len(actual)} rows), wheel option defaults ({len(defaults)}) and profile schema WheelOptions ({len(profile)}) match')
        return 0
    for table in ('WheelLayouts', 'BristolLayouts', 'ControllerLayouts'):
        for layout, row in read(db, table).items():
            print(f'{table} {layout}: ' + ', '.join(f'{k}={v}' for k, v in row.items() if v))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
