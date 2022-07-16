from data import GameData
from resim import Resim
from rng import Rng

# (s0, s1), rng offset, event offset, start timestamp, end timestamp
# position = ((636277877949988771, 3881154616169282314), 39, -10, "2021-05-21T02:34:20.217Z", "2021-05-21T04:10:23.217Z")
# position = ((16943380630585140239, 11517173126754224871), 12, -10, "2021-04-10T17:23:00.667Z", "2021-04-10T21:25:01.667Z")
# position = ((16943380630585140239, 11517173126754224871), 12, -10, "2021-04-10T17:23:00.667Z", "2021-04-10T21:25:01.667Z")
position = ((85494335616218333, 7724238040931076749), 0, -4, "2021-03-19T06:35:08.525966Z", "2021-03-19T18:40:01.593947Z")
# position = ((588802205905282246, 793469634141293574), 37, -6, "2021-03-19T12:06:37.593Z", "2021-03-19T18:40:01.593947Z")

position = ((5240931180015396439, 15582981864323664294), 34, -5, "2021-03-16T21:01:06.567Z", "2021-03-17T08:50:10.889994Z")
position = ((2912811045091108304, 5836117223166560545), 7, -35, "2021-03-17T08:32:07.534Z", "2021-03-17T18:50:07.535Z")

rng_state, rng_offset, step, start_time, end_time = position
rng = Rng(rng_state, rng_offset)
rng.step(step)
resim = Resim(rng)
resim.run(start_time, end_time)

print("state at end:", rng.get_state_str())