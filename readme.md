# resim
Reverse-engineering blaseball from the PRNG stream.

## Requirements
Python 3.9, at least? numpy, pandas, matplotlib, scikit-learn. 

## Instructions
Clone repository and run `run.py output.txt`, if you want to see the output, or `run.py --silent` if you don't. I thought not generating output would make it go faster but that doesn't seem to be the case. It will take a long time to run the first time, as it builds a set of cache files. Afterwards, it will take...less long, anyway. From there, use Jupyter notebooks included to analyze data, or make your own!

## Structure
- `rng.py`: handles the PRNG calculations
- `data.py`: functions and classes to fetch needed data
- `output.py`: defines class for logging rolls to csv, for analysis
- `resim.py`: the meat of the program; does the actual resimulation
- `run.py`: runs the program. Define time ranges to investigate here