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


def read(db, table):
    con = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    try:
        cur = con.execute(f'SELECT * FROM "{table}" ORDER BY LayoutId')
        cols = [c[0] for c in cur.description]
        return {row[0]: dict(zip(cols[1:], row[1:])) for row in cur}
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
        print(f'WheelLayouts match the recorded layouts ({len(actual)} rows)')
        return 0
    for table in ('WheelLayouts', 'BristolLayouts', 'ControllerLayouts'):
        for layout, row in read(db, table).items():
            print(f'{table} {layout}: ' + ', '.join(f'{k}={v}' for k, v in row.items() if v))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
