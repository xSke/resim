# resim
Reverse-engineering blaseball from the PRNG stream.

## Requirements
Python 3.9, at least? numpy, pandas, matplotlib, scikit-learn.

Run `pip3 install -r requirements.txt` to install all necessary packages.

## Instructions
Clone repository and run `run.py out/output.txt`, if you want to see the output, or `run.py --silent` if you don't. I thought not generating output would make it go faster but that doesn't seem to be the case. It will take a long time to run the first time, as it builds a set of cache files. Afterwards, it will take...less long, anyway. From there, use Jupyter notebooks included to analyze data, or make your own!

## Structure
- `rng.py`: handles the PRNG calculations
- `data.py`: functions and classes to fetch needed data
- `output.py`: defines class for logging rolls to csv, for analysis
- `resim.py`: the meat of the program; does the actual resimulation
- `run.py`: runs the program. Define time ranges to investigate here

## Derived Pesudocode of a normal game tick

For seasons 12-15. This pseudocode is "just" for standard game events. For details about start/end of games, start/end of innings, mod notifications, non-random weather procs like Black Hole/Sun2, etc. see `handle_misc` in `resim.py`.

```
roll for return-from-elsewhere (end event if it procs) and name unscattering (thresholds TODO?)
roll for weather, end event if it procs (thresholds TODO)
roll for party, end event if it procs (threshold known)
if weather is flooding:
  roll for flooding, end event if it procs (thresholds TODO)
roll for consumers, end event if it procs (threshold in progress)
if ballpark has peanut mister:
  roll for peanut mister, end event if it procs (threshold TODO)
if ballpark has smithy:
  roll for smithy, end event if it procs (threshold TODO)
if ballpark has secret base:
  roll for secret base, end event if it procs (regular and attractors; thresholds TODO)
if ballpark has grind rail:
  roll for grind rail, end event if it procs (thresholds TODO?)
if ballpark has tunnels:
  roll for tunnels, end event if it procs (threshold TODO)
roll to choose steal fielder (not confirmed)
for each steal-eligible player:
  roll for steal, end event if it procs (thresholds in progress)
if batter has electric blood mod:
  roll for zap, end event if it procs (threshold TODO)
if pitcher has debt and batter is not observed:
  roll for HBP, end event if it procs (threshold TODO)
if weather is birds:
  roll for bird ambush, end event if it procs (threshold TODO)
roll for mild, end event if it procs (roll regardless if the pitcher has the mod; threshold TODO)
if the count is 0-0 and batter or pitcher has charm blood mod:
  roll for charm, end event if it procs (threshold and exact logic TODO)
if batter is magmatic:
  roll for unknown reasons, possibly unused
  automatic home run, end event
  if ballpark has big buckets:
    roll for big buckets (threshold TODO)
roll for strike zone (threshold known)
if pitcher has acidic blood mod:
  roll for acidic blood (threshold TODO)
if batter has flinch and strike count is 0:
  automatic no-swing
else:
  roll for swing (threshold differs based on strike zone roll; both thresholds known)
if batter didn't swing:
  if ball out of zone:
    ball count += 1
    if ball count == # of balls in a walk:
      result is walk
      if batter has base instincts:
        roll for base instincts (thresholds TODO)
    else:
      result is a ball
  else:
    strike count += 1
    if strike count == # of strikes in a strikeout:
      result is strikeout looking
    else:
      result is strike looking/flinching
else:  # batter did swing
  roll for contact (threshold differs based on strike zone roll; both thresholds known)
  if no contact:
    strike count += 1
    if strike count == # of strikes in a strikeout:
      result is strikeout swinging
    else:
      result is strike swinging
  else:  # yes contact
    roll for foul (threshold known)
    if foul:
      result is foul
    else:
      roll to choose a fielder (known)
      roll for out (threshold in progress)
      if out:
        num outs += 1
        roll to choose a flyout assigned fielder (known)
        roll for fly (threshold known)
        if fly:
          if num outs < # of outs in a half-inning:
            for each runner in reverse order:
              if the next base is open:
                roll for runner advancement (threshold in progress)
          result is flyout with flyout assigned fielder responsible
        else:
          roll to choose a ground out assigned fielder (known)
          if num outs < # of outs in a half-inning:
            refer to https://github.com/xSke/resim/blob/83cb0d6165da8e099bc41e634272fcce8efe55d8/resim.py#L871 for double play, fielders choice, and runner advancement logic (all thresholds known)
          else:
            result is groundout with ground out assigned fielder responsible
        if batter has debt, result is a simple ground out or flyout, and assigned fielder is not already observed:
          roll for debt (threshold TODO)
      else:  # not an out
        roll for home run (threshold known)
        if home run:
          result is home run
          roll buckets (threshold unknown)
        else:  # base hit
          roll for fielder (known)
          roll for double (threshold known)
          roll for triple (threshold known)
          if triples roll passed:
            result is triple
          else if doubles roll passed:
            result is double
          else:
            result is single
          apply automatic advancement based on the hit type
          for each runner in reverse order:
            if the next base is open:
              roll for extra runner advancement (threshold TODO)
if batter is reverberating and this event ends the PA and it wasn't a hit or HR:
  roll for reverberating (threshold TODO)
if the attractor async thing happened:  # idk ask astrid
  roll for attractor's fake stars (formula known)
```
