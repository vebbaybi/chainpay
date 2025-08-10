# chainpay

Version: 1.0.0
Author: webbaby
Script: chainpay.py

## Description

chainpay parses plain text work logs into a clean CSV timesheet.
It makes no assumptions: if a value isn’t explicitly provided, it writes NaN.
It supports multiple time blocks per day, handles locations/clients/tasks cleanly,
applies a single lunch deduction per day (0.5h), writes a watermark, and appends a weekly total.

## Key Features

* No guessing: missing fields are recorded as NaN.
* Clean extraction:

  * `"at LOCATION, TASK"` → location=LOCATION, task=TASK
  * `"... for/with CLIENT, TASK"` → client=CLIENT, task=TASK
  * `"TIME ... free text before at/for/with"` → task
  * `"= tail with at/for/with, TASK"` → location/client from directives; task from trailing comma text
* Multiple time blocks per day.
* Lunch detection: once per day, subtracts 0.5h and appends `(lunch)` to the first task.
* Watermark: `# Compiled with chainpay.py by webbaby` at the top of the CSV.
* Weekly total row appended at the end.

## Input Format

One day per line. Use `|` to separate segments on the same day.
A segment with a time range creates a block (e.g., `0830 - 1700`).
A segment without a time range is a modifier for the most recent block on that day.

##Example Input

```
monday=0900 - 1700 | at Andromeda Riverbelt, Quantum framing | for Zorblaxian Builders | lunch
tuesday=0800 - 1600 | at Elmara Nebula for ACME (Alien Circuitry & Matter Experts), Stellar electrical rough-in | lunch
wednesday=0730 - 1200 | at Maple Star Cluster for NorthBuild Interstellar, Meteor prep | 1230 - 1600 = at 14 Pulsar St for Galactic City Council, Cosmic inspection
thursday=0900 - 1200 | at Oakulon Complex for Nebula Nomads, Astro-drywall | 1300 - 1700 = at Pinex Warp Warehouse for BetaCo Starforge, Gravity install | lunch
friday=0800 - 1100 | at Cedarion Plaza for Delta LLC (Dimensional Labor League), Job prepping for warp core | 1130 - 1500 = at 22 Meadow Asteroid for CityWorks Cosmos, Nebula painting
```

## Expected CSV Output

```
# Compiled with chainpay.py by webbaby
Day,TimeBlocks,Location,Tasks/Details,Client(s),Hours
Monday,0900-1700,Andromeda Riverbelt,Quantum framing(lunch),Zorblaxian Builders,7.5
Tuesday,0800-1600,Elmara Nebula,Stellar electrical rough-in(lunch),ACME (Alien Circuitry & Matter Experts),7.5
Wednesday,"0730-1200, 1230-1600","Maple Star Cluster, 14 Pulsar St","Meteor prep, Cosmic inspection","NorthBuild Interstellar, Galactic City Council",8.0
Thursday,"0900-1200, 1300-1700","Oakulon Complex, Pinex Warp Warehouse","Astro-drywall(lunch), Gravity install","Nebula Nomads, BetaCo Starforge",6.5
Friday,"0800-1100, 1130-1500","Cedarion Plaza, 22 Meadow Asteroid","Job prepping for warp core, Nebula painting","Delta LLC (Dimensional Labor League), CityWorks Cosmos",6.5
TOTAL,,,,,35.5
```

## Requirements

* Python 3.9+
* python-dateutil

## Install

```
pip install python-dateutil
```

## Usage

**Option A:** read from a file and write CSV to the current directory (`work hour.csv`)

```
python chainpay.py input.txt
```

**Option B:** pipe input via stdin

```
cat input.txt | python chainpay.py
```

## Output

* A file named `work hour.csv` in the current working directory.
* First line is a comment watermark.
* Final row is the weekly TOTAL.
