from data import GameData
from resim import Resim
from rng import Rng

# (s0, s1), rng offset, event offset, start timestamp, end timestamp
# position = ((636277877949988771, 3881154616169282314), 39, -10, "2021-05-21T02:34:20.217Z", "2021-05-21T04:10:23.217Z")
# position = ((16943380630585140239, 11517173126754224871), 12, -10, "2021-04-10T17:23:00.667Z", "2021-04-10T21:25:01.667Z")
# position = ((16943380630585140239, 11517173126754224871), 12, -10, "2021-04-10T17:23:00.667Z", "2021-04-10T21:25:01.667Z")
# position = ((85494335616218333, 7724238040931076749), 0, -4, "2021-03-19T06:35:08.525966Z", "2021-03-19T07:10:26.969973Z")
position = ((588802205905282246, 793469634141293574), 37, -6, "2021-03-19T12:06:37.593Z", "2021-03-19T18:40:01.593947Z")

rng_state, rng_offset, step, start_time, end_time = position
rng = Rng(rng_state, rng_offset)
rng.step(step)
resim = Resim(rng)
resim.run(start_time, end_time)