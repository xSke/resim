import json
import time
from argparse import ArgumentParser
from collections import defaultdict
from enum import Enum, auto
from multiprocessing import Pool, Queue
from os.path import splitext
from queue import Empty
from sys import stdout
from tqdm import tqdm
from typing import Optional, List, Dict

from data import get_feed_between
from resim import Csv, Resim
from rng import Rng

# fmt: off
# season (0-indexed), (s0, s1), rng offset, event offset, start timestamp, end timestamp
FRAGMENTS_WITH_SEASON = [
    # SEASON 12:
    (11, (12933895067857275469, 10184511423779887981), 54, 0, "2021-03-01T16:00:00Z", "2021-03-01T16:59:00.000Z"),
    # deploy at 2021-03-01T17:00:00Z
    (11, (14692912971575338444, 10258878526251633180), 10, 0, "2021-03-01T17:00:00Z", "2021-03-01T17:55:00.000Z"),
    # deploy at 2021-03-01T17:55:00Z
    # deploy at 2021-03-01T19:45:00Z
    (11, (7344712312998972205, 1322614744124056105), 10, 0, "2021-03-01T20:00:00Z", "2021-03-01T22:24:33.807Z"),
    # Lots of data missing at the end of this game; not sure if fixable
    (11, (17890502365312422818, 3874941140339393875), 36, 0, "2021-03-02T09:00:00Z", "2021-03-02T14:24:46.430Z"),
    # Lots of missing data at the end of this game; could probably be manually sorted out, but I don't feel like it
    # deploy at 2021-03-02T17:50:00Z
    # deploy at 2021-03-02T20:50:00Z
    (11, (2887724892689068370, 7824040834361231079), 49, 0, "2021-03-02T23:00:00.000Z", "2021-03-03T16:50:00.000Z"),
    # deploy at 2021-03-03T16:50:00Z
    (11, (9516845697228190797, 6441957190109821557), 10, 0, "2021-03-03T17:00:00.000Z", "2021-03-04T02:50:00.000Z"),
    # deploy at 2021-03-04T02:45:00Z
    (11, (3898039635056169634, 13636121169112427915), 10, 0, "2021-03-04T03:00:00.000Z", "2021-03-04T04:50:00Z"),
    # deploy at 2021-03-04T04:50:00Z
    # (11, (6354326472372730027, 3011744895320117042), 10, 0, "2021-03-04T05:00:00.000Z", "2021-03-04T18:50:00.000Z"),
    # deploy at 2021-03-04T18:55:00Z
    (11, (617776737860945499, 6965272805741501853), 10, 0, "2021-03-04T19:00:00.000Z", "2021-03-05T19:15:00.000Z"),
    # mid-game restart during S12D98, between 2021-03-05T19:14:36.000Z and 2021-03-05T19:15:10.091Z
    (11, (3038364565806058511, 15510617008273015236), 0, 0, "2021-03-05T19:15:00.000Z", "2021-03-05T21:50:16.083Z"),
    (11, (11460721463282082147, 11936110632627786929), 53, 0, "2021-03-05T22:00:00Z", "2021-03-06T19:26:00Z"),
    # mid-game restart during S12D112 between 2021-03-06T19:25:33.920Z and 2021-03-06T19:26:12.847Z
    (11, (15656707514096936112, 6103459252510298906), 0, 0, "2021-03-06T19:26:00Z", "2021-03-06T23:50:00.000Z"),
    # SEASON 13:
    (12, (2300985152363521761, 16070535759624553037), 0, 0, "2021-03-08T16:00:00.000Z", "2021-03-09T01:50:00.000Z"),
    # deploy at 2021-03-09T01:55:00Z
    (12, (12625543386802094591, 8574312021167992434), 12, 0, "2021-03-09T02:00:00.000Z", "2021-03-09T15:50:00.000Z"),
    # we're missing most of day 25 for some reason. resume on day 26
    (12, (2011003944438535900, 1095087939505767591), 3, 0, "2021-03-09T17:00:00.000Z", "2021-03-09T20:50:00.000Z"),
    # deploy at 2021-03-09T20:50:00Z
    (12, (2154942915490753213, 4636043162326033301), 13, 0, "2021-03-09T21:00:00.000Z", "2021-03-10T21:22:00.000Z"),
    # mid-game restart during S13D53, between 2021-03-10T21:21:45.575Z and 2021-03-10T21:22:18.985Z
    (12, (15380396381966399715, 13714309750257610776), 0, 0, "2021-03-10T21:22:00.000Z", "2021-03-11T14:50:00.000Z"),
    # deploy at 2021-03-11T14:55:00Z
    (12, (7021708722608607714, 3158314368145462130), 12, 0, "2021-03-11T15:00:00.000Z", "2021-03-12T00:55:00.000Z"),
    # S13 D80 is a separate fragment for some reason
    (12, (14557622918943320291, 14569056651611896317), 12, 0, "2021-03-12T01:00:00.000Z", "2021-03-12T01:50:00Z"),
    # deploy at 2021-03-12T01:50:00Z
    (12, (11529751786223941563, 7398827681552859473), 12, 0, "2021-03-12T02:00:00.000Z", "2021-03-12T09:21:30.000Z"),
    # mid-game restart during S12D88, between 2021-03-12T09:21:22.163Z and 2021-03-12T09:21:46.082Z.
    # For some reason the range 09:24:00-09:24:10 is impossible for me to align with what's after it.
    # I don't know why! So there's about 4 minutes missing in day 88.
    (12, (17262598579754601440, 1372102753813730563), 34, -4, "2021-03-12T09:25:21.623Z", "2021-03-12T19:50:00.000Z"),
    # deploy at 2021-03-12T19:50:00Z
    (12, (12600639729467795539, 6003152159250863900), 0, 0, "2021-03-12T20:00:00.000Z", "2021-03-13T01:50:00Z"),
    # No listed deploy, but there seems to be a break between S13D103 and D104
    (12, (12572462612291142032, 12133846605477681375), 8, 0, "2021-03-13T02:00:00.000Z", "2021-03-14T04:05:00Z"),
    # deploy at 2021-03-14T04:05:00Z
    # SEASON 14:
    (13, (8640116423355544309, 9923965671729542710), 0, 0, "2021-03-15T15:00:00.000Z", "2021-03-15T20:55:29.050219Z"),
    (13, (12335197627095558518, 4993735724122314585), 11, -2, "2021-03-15T21:00:00.000Z", "2021-03-16T15:50:01.111345Z"),  # noqa: E501
    # deploy at 2021-03-16T16:20:00Z
    (13, (3707231913994734955, 16004224931998739944), 51, -1, "2021-03-16T18:00:00Z", "2021-03-16T20:50:00.000Z"),
    (13, (16935077139086615170, 7227318407464058534), 12, 0, "2021-03-16T21:00:00.000Z", "2021-03-17T18:50:07.535Z"),
    # deploy at 2021-03-17T18:50:00Z
    (13, (647677220274352043, 14172195254117178691), 12, 0, "2021-03-17T19:00:00Z", "2021-03-17T19:50:00Z"),
    # deploy at 2021-03-17T19:55:00Z
    (13, (5750154725705680658, 7572065454551339919), 12, -1, "2021-03-17T20:00:00Z", "2021-03-18T14:50:37.673409Z"),
    # deploy at 2021-03-18T14:50:00Z
    (13, (14329231552902792263, 18343048993884457641), 12, 0, "2021-03-18T15:00:00Z", "2021-03-18T17:40:00.966Z"),
    # deploy at 2021-03-18T17:40:00Z
    (13, (16471765453082535911, 290065450250321384), 12, -5, "2021-03-18T18:00:00Z", "2021-03-18T18:50:51.385Z"),
    # deploy at 2021-03-18T18:50:00Z
    # deploy at 2021-03-18T19:10:00Z
    (13, (4843171135789851264, 15316903146384693430), 4, 0, "2021-03-18T19:13:02.179Z", "2021-03-18T21:50:02.180Z"),
    # deploy at 2021-03-18T22:00:00Z
    (13, (18280451156624678684, 16123465889931048163), 2, 0, "2021-03-18T22:01:16.566Z", "2021-03-19T00:56:16.567Z"),
    (13, (4369050506664465536, 4603334513036430167), 12, 0, "2021-03-19T01:00:00.000Z", "2021-03-19T18:40:01.593947Z"),
    # 2021-03-19T18:50:00Z
    (13, (1705402211782391315, 14786618665043368424), 63, -1, "2021-03-19T19:00:00Z", "2021-03-19T19:19:26.102Z"),
    # Mid-game restart during S14D99
    (13, (17332235655028997556, 6510596254177638633), 6, 0, "2021-03-19T19:20:09.000Z", "2021-03-20T19:50:01.020Z"),
    # SEASON 15:
    (14, (5663433618038523615, 14076760388081329253), 38, 0, "2021-04-05T15:00:00Z", "2021-04-05T16:43:00Z"),
    # mid-game deploy between 2021-04-05T16:42:31.409Z and 2021-04-05T16:43:00.568Z
    (14, (17427984274213299410, 10295578987196636638), 50, 0, "2021-04-05T16:43:00Z", "2021-04-05T17:50:00.000Z"),
    # deploy at 2021-04-05T19:00:00Z
    (14, (8572860974500469665, 4065346147574372575), 62, 0, "2021-04-05T19:00:00Z", "2021-04-05T21:45:00.000Z"),
    # deploy at 2021-04-05T21:45:00Z
    (14, (2729743526261167128, 14220066028502999848), 8, 0, "2021-04-05T23:00:00Z", "2021-04-05T23:55:00Z"),
    # deploy at 2021-04-05T23:55:00Z
    (14, (1572775861984790377, 14927238043745363817), 3, 0, "2021-04-06T01:00:00Z", "2021-04-06T16:50:21.741Z"),
    # deploy at 2021-04-06T16:50:00Z
    (14, (11575834613258116171, 9179890967976243405), 62, 0, "2021-04-06T17:00:00Z", "2021-04-06T22:50:01.740Z"),
    # deploy at 2021-04-06T22:50:00Z
    (14, (13606427098695492650, 9537038708173591254), 62, 0, "2021-04-06T23:00:00Z", "2021-04-07T16:50:00.594684Z"),
    # deploy at 2021-04-07T16:55:00Z
    (14, (6033393494486318410, 6992320288130472062), 62, 0, "2021-04-07T17:00:00Z", "2021-04-07T22:50:13.341Z"),
    (14, (5082886454574003662, 2374945375831325277), 62, 0, "2021-04-07T23:00:00Z", "2021-04-08T01:50:56.946Z"),
    # deploy at 2021-04-08T02:00:00Z
    (14, (818230392324657822, 13958695923778937231), 50, -12, "2021-04-08T02:00:00.000Z", "2021-04-08T14:50:46.446Z"),
    (14, (14089361583866000722, 2263563325949770448), 62, 0, "2021-04-08T15:00:00Z", "2021-04-08T17:26:26.937Z"),
    # mid-game restart between 2021-04-08T17:26:26.937Z and 2021-04-08T17:26:50.939Z
    (14, (14445530066672905733, 9753476557479306590), 50, 0, "2021-04-08T17:26:35Z", "2021-04-08T19:50:00Z"),
    # deploy at 2021-04-08T19:50:00Z
    (14, (11947114742050313518, 14817598476034896117), 62, -1, "2021-04-08T20:00:00.000Z", "2021-04-09T19:40:40.804096Z"),  # noqa: E501
    (14, (11741473536472310906, 13138857156664992063), 50, 0, "2021-04-09T21:00:00Z", "2021-04-10T20:50:43.708Z"),
    # SEASON 16
    (15, (10932564791979919451, 14996520360868746409), 0, 0, "2021-04-12T15:00:00Z", "2021-04-12T15:59:00.000Z"),
    (15, (2630659810699049822, 6988656998221057606), 12, 0, "2021-04-12T16:00:00Z", "2021-04-12T17:50:32Z"),
    # deploy at 2021-04-12T17:55:00Z
    (15, (17323399111022330811, 4879149733790758757), 12, -1, "2021-04-12T18:00:00Z", "2021-04-13T03:50:51.789Z"),
    # deploy at 2021-04-13T03:50:00Z
    (15, (10477766721903297251, 12705963767891031099), 12, 0, "2021-04-13T04:00:00Z", "2021-04-13T22:50:00.000Z"),
    # deploy at 2021-04-13T22:50:00Z
    (15, (4553246806715641641, 2091247548393494550), 12, -1, "2021-04-13T23:00:00Z", "2021-04-14T22:50:20Z"),
    # These don't seem to be connected even though there's no known deploy
    (15, (6108537368578273164, 16160283723408631925), 12, 0, "2021-04-14T23:00:00Z", "2021-04-15T14:45:00.000Z"),
    # deploy at 2021-04-15T14:45:00Z
    (15, (11830519604653945177, 6347150039073630797), 12, 0, "2021-04-15T15:00:00Z", "2021-04-16T13:10:10.252Z"),
    # There's a bunch of missing data during this game
    (15, (4171720260983161235, 6259522112588850629), 38, 0, "2021-04-16T14:00:00Z", "2021-04-16T15:08:13.584Z"),
    # mid-game restart
    (15, (14445511397013126193, 15344599895236837205), 3, 0, "2021-04-16T15:08:51.471Z", "2021-04-17T15:50:00.000Z"),
    (15, (8446026695989093392, 9456589704687145533), 4, 0, "2021-04-17T16:00:00Z", "2021-04-18T17:10:00.000Z"),
    # deploy at 2021-04-18T17:10:00Z
    # deploy at 2021-04-18T17:45:00Z
    # deploy at 2021-04-18T18:00:00Z
    # SEASON 17
    (16, (9700276183957801543, 1781052055904152059), 39, 0, "2021-04-19T15:20:59.302Z", "2021-04-19T23:50:00.000Z"),
    # deploy at 2021-04-20T00:00:00Z
    (16, (1938649611673329265, 7626630235419679892), 12, 0, "2021-04-20T00:00:00Z", "2021-04-20T15:50:00.000Z"),
    # deploy at 2021-04-20T15:50:00Z
    (16, (2615094872925212987, 10785311068506962293), 12, 0, "2021-04-20T16:00:00Z", "2021-04-20T22:55:00.000Z"),
    # deploy at 2021-04-20T22:55:00Z
    (16, (1545183801643444274, 11628662956451449120), 12, -3, "2021-04-20T23:00:00Z", "2021-04-21T23:14:45.163Z"),
    # mid-game restart between 2021-04-21T23:14:45.163Z and 2021-04-21T23:15:18.115Z
    (16, (18429607522424503338, 13228705917792247179), 0, 0, "2021-04-21T23:15:18.114Z", "2021-04-22T03:50:00.000Z"),
    # deploy at 2021-04-22T03:50:00Z
    (16, (12546856154551792590, 1162678545057283425), 13, 0, "2021-04-22T04:00:00Z", "2021-04-22T19:45:00.000Z"),
    # deploy at 2021-04-22T19:45:00Z
    # deploy at 2021-04-22T20:40:00Z
    (16, (8687228792144776478, 6797152899916764019), 12, 0, "2021-04-22T21:00:00Z", "2021-04-22T22:13:45.215Z"),
    # mid-game restart between 2021-04-22T22:13:45.214Z and 2021-04-22T22:14:20.083Z
    # deploy at 2021-04-23T05:45:00Z
    (16, (2689660673373449332, 17115118443619503741), 59, 0, "2021-04-23T06:00:00Z", "2021-04-24T02:59:00.000Z"),
    # SEASON 18
    # deploy at 2021-05-10T15:50:00Z
    (17, (7880339813634557576, 171519300893460508), 12, 0, "2021-05-10T16:00:00Z", "2021-05-10T19:07:44.439Z"),
    # mid-game reset between 2021-05-10T19:07:44.438Z and 2021-05-10T19:08:56.021Z
    (17, (5641131764121179054, 11988683151420110141), 48, 0, "2021-05-10T19:19:22.771Z", "2021-05-10T21:59:00.000Z"),
    (17, (15812229738853570065, 15548065784110606380), 12, 0, "2021-05-10T22:00:00Z", "2021-05-11T01:45:00.000Z"),
    # deploy at 2021-05-11T01:45:00Z
    (17, (4682029815740372257, 3533887921931845028), 12, 0, "2021-05-11T02:00:00Z", "2021-05-11T16:50:00.000Z"),
    # deploy at 2021-05-11T17:00:00Z
    # deploy at 2021-05-11T17:50:00Z
    (17, (13114281757507717717, 5019394425794688289), 13, -1, "2021-05-11T18:00:00Z", "2021-05-12T18:20:06.952Z"),
    # mid-game restart between 2021-05-12T18:20:06.951Z and 2021-05-12T18:20:38.259Z
    (17, (12169231481536370333, 15331095008534537875), 0, 0, "2021-05-12T18:20:38.258Z", "2021-05-13T01:50:00.000Z"),
    # deploy at 2021-05-13T01:50:00Z
    (17, (6975934767133830346, 14379619455193848711), 12, 0, "2021-05-13T02:00:00Z", "2021-05-13T05:45:00.000Z"),
    # deploy at 2021-05-13T05:45:00Z
    (17, (169756623349483764, 10724764427362166896), 12, 0, "2021-05-13T06:00:00Z", "2021-05-13T14:59:00.000Z"),
    (17, (3249557743938083318, 7782548880230924147), 11, 0, "2021-05-13T15:00:00Z", "2021-05-14T15:01:56.644Z"),
    # mid-game restart between 2021-05-14T15:01:56.645Z and 2021-05-14T15:02:36.127Z
    (17, (5414059934210130424, 9147784782760993019), 63, 0, "2021-05-14T15:02:36.126Z",   "2021-05-15T03:59:00.000Z"),
    (17, (10258348600073239750, 6640146572529175717), 7, 0, "2021-05-15T04:00:00Z", "2021-05-15T22:59:00.000Z"),
    # deploy at 2021-05-16T17:45:00Z
    # SEASON 19
    (18, (2539326290161707890, 2412861567137376176), 53, 0, "2021-05-17T15:00:00Z", "2021-05-17T18:45:00.000Z"),
    # deploy at 2021-05-17T18:45:00Z
    (18, (15378406236295699154, 17279250379653914870), 12, 0, "2021-05-17T19:00:00Z", "2021-05-17T19:16:21.086Z"),
    # mid-game restart between 2021-05-17T19:16:21.020Z and 2021-05-17T19:16:23.071Z
    (18, (2697853937575908157, 11764077085734762375), 11, 0, "2021-05-17T19:16:23.070Z", "2021-05-18T17:59:00.000Z"),
    # deploy at 2021-05-18T18:25:00Z
    # deploy at 2021-05-18T18:40:00Z
    (18, (322772071358183462, 14325568949321818108), 12, 0, "2021-05-18T19:00:00Z", "2021-05-19T18:59:00.000Z"),
    # doesn't seem to connect to the next game
    (18, (8827114537495343080, 14424246698642899362), 12, 0, "2021-05-19T19:00:00Z", "2021-05-20T05:59:00.000Z"),
    # deploy at 2021-05-20T06:05:00Z
    (18, (8102282771631894131, 10722580432945378578), 0, 0, "2021-05-20T06:05:00Z", "2021-05-20T15:35:21.981Z"),
    # skipping latesiesta between these
    (18, (2660238593085031484, 15579834670990899106), 63, 0, "2021-05-20T17:00:00Z", "2021-05-21T06:37:18.183Z"),
    # no known deploy here, but they're not connected, apparently
    (18, (18092727977450531827, 6395006528213370935), 12, 0, "2021-05-21T07:00:00Z", "2021-05-22T03:59:00.000Z"),
    # gap between playoff rounds
    (18, (16743591074603639980, 8802697527274036586), 0, 0, "2021-05-22T15:00:00Z", "2021-05-23T00:59:00.000Z"),
    # SEASON 20
    # missing data at the beginning of day 1
    (19, (13189048446507658518, 15635856416103723808), 34, 0, "2021-06-14T15:02:25.673Z", "2021-06-14T19:16:35.020Z"),
    # mid game reset between 2021-06-14T19:16:35.020Z and 2021-06-14T19:17:03.653Z
    (19, (15955678348363204908, 7707961550328798044), 0, 0, "2021-06-14T19:17:03.653Z", "2021-06-14T23:59:00.000Z"),
    (19, (5279388538996975652, 14545947148766704888), 59, 0, "2021-06-15T01:00:00Z", "2021-06-15T02:50:00.000Z"),
    # deploy at 2021-06-15T02:50:00Z
    # deploy at 2021-06-15T03:45:00Z
    (19, (11834657142774484639, 8847393975141676978), 13, 0, "2021-06-15T04:00:00Z", "2021-06-15T05:00:57.910Z"),
    # mid--game restart between 2021-06-15T05:00:57.910Z and 2021-06-15T05:02:02.734Z
    # another mid-game restart between 2021-06-15T05:04:53.785Z and 2021-06-15T05:16:44.924Z
    # having difficulty getting these few minutes to line up properly
    (19, (16146927183484644083, 12635323359905163121), 0, 0, "2021-06-15T05:20:44.924Z", "2021-06-15T10:59:00.000Z"),
    (19, (5586582117725844015, 17505527080988874596), 20, 1, "2021-06-15T11:00:00Z", "2021-06-15T21:55:00.000Z"),
    # deploy at 2021-06-15T21:55:00Z
    (19, (7943813107847417936, 11710957498055735526), 12, 0, "2021-06-15T22:00:00Z", "2021-06-16T04:59:00.000Z"),
    (19, (12471352467777430005, 13632017682517987076), 49, 6, "2021-06-16T05:00:00Z", "2021-06-16T07:59:00.000Z"),
    (19, (17791062997308723570, 9874943169784635931), 8, -1, "2021-06-16T08:00:00Z", "2021-06-16T14:59:00.000Z"),
    (19, (14221967040496645937, 16738649322168749995), 58, -1, "2021-06-16T15:00:00Z", "2021-06-16T22:12:58.475Z"),
    #mid-game restart between 2021-06-16T22:12:58.475Z and 2021-06-16T22:13:33.811Z
    (19, (13144040369900249853, 13982262684361311212), 0, 0, "2021-06-16T22:13:33.810Z", "2021-06-17T08:59:00.000Z"),
    (19, (6731472628929309800, 15633055231165530437), 61, 0, "2021-06-17T09:00:00.000Z", "2021-06-17T13:50:00.000Z"),
    # deploy at 2021-06-17T13:50:00Z
    (19, (1505011938451294133, 14444347201119398829), 32, 0, "2021-06-17T17:00:00Z", "2021-06-17T17:45:00.000Z"),
    # deploy at 2021-06-17T17:45:00Z
    (19, (16374154405258174406, 7181060442794521510), 12, -1, "2021-06-17T18:00:00Z", "2021-06-17T20:45:00.000Z"),
    # deploy at 2021-06-17T20:45:00Z
    (19, (12626833481785816798, 14819463179663166176), 12, 0, "2021-06-17T21:00:00Z", "2021-06-18T00:50:00.000Z"),
    # deploy at 2021-06-18T00:50:00Z
    (19, (2474051231912652739, 7697123856631804636), 11, -3, "2021-06-18T01:00:00Z", "2021-06-18T04:00:00Z"),
    (19, (15283653784601827550, 17277569543084107761), 40, 0, "2021-06-18T04:00:00Z", "2021-06-18T10:59:00.000Z"),
    (19, (1681088041855734602, 12260922948212003034), 47, -1, "2021-06-18T11:00:00Z", "2021-06-18T20:59:00.000Z"),
    (19, (10224770184903718855, 6886338571997413591), 28, 0, "2021-06-18T21:00:00Z", "2021-06-19T01:03:21.249Z"),
    # midgame restart between 2021-06-19T01:03:21.249Z and 2021-06-19T01:04:05.913Z
    # having trouble getting these few minutes to line up.
    (19, (14718838674862637822, 4960275232824896908), 0, 0, "2021-06-19T01:11:23.704Z", "2021-06-19T23:59:00.000Z"),
    # deploy at 2021-06-20T17:35:00Z 

    # # s21 season
    # deploy at 2021-06-21T15:40:00Z
    (20, (8005871686283442186, 1367633559999327135), 12, -1, "2021-06-21T16:00:00Z", "2021-06-22T15:50:00.000Z"),
    # deploy at 2021-06-22T15:50:00Z
    (20, (10029294435931187556, 16869252615682473268), 14, 0, "2021-06-22T16:00:00Z", "2021-06-22T19:03:32.829Z"),
    # mid-game restart between 2021-06-22T19:02:45.990Z and 2021-06-22T19:03:32.829Z
    # deploy at 2021-06-22T19:45:00Z
    # deploy at 2021-06-22T19:55:00Z
    (20, (2320695979190012174, 15435819863139029863), 14, 0, "2021-06-22T20:00:00Z", "2021-06-23T18:50:00.000Z"),
    # deploy at 2021-06-23T18:50:00Z
    # deploy at 2021-06-23T19:55:00Z
    (20, (15925274024784204014, 16560435110756045768), 27, 0, "2021-06-23T21:00:00Z", "2021-06-24T14:45:00.000Z"),
    #(20, (453308231946141103, 3094461473270754192), 59, 0, "2021-06-23T21:16:00Z", "2021-06-24T14:45:00.000Z"),

    # deploy at 2021-06-24T14:45:00Z
    # deploy at 2021-06-24T15:50:00Z
    # deploy at 2021-06-24T16:35:00Z
    # deploy at 2021-06-24T17:00:00Z
    # deploy at 2021-06-24T18:55:00Z
    (20, (16993716307475245277, 13630975682157262811), 17, 4, "2021-06-24T19:00:00Z", "2021-06-24T20:59:59.000Z"),
    (20, (15361302264504170125, 4199317014251846854), 12, 0, "2021-06-24T21:00:00Z", "2021-06-25T02:55:00.000Z"),
    # The beginning of day 83 has missing update data. Something broke and they had to restart it 10 minutes later.
    (20, (12517766727501020327, 1999791830960913276), 48, 0, "2021-06-25T03:18:16.762Z", "2021-06-25T21:59:59.000Z"),
    # deploy at 2021-06-25T21:55:00Z
    # s21 postseason
    (20, (1203568976480913342, 6212285493021009556), 0, 0, "2021-06-25T22:00:00Z", "2021-06-27T03:59:01.289138Z"),

    # s22
    (21, (13880531733247279510, 14458547266857370788), 43, -5, "2021-06-29T03:03:58.345Z", "2021-06-29T08:50:05.032485Z"),

    # s23
    (22, (13846068740922721357,11524572744584342458), 2, -7, "2021-07-19T16:16:05.034Z", "2021-07-19T21:55:09.251933Z"),
    (22, (13317437497403022007,6662414531266329035), 10, -1, "2021-07-19T22:04:31.962Z", "2021-07-20T02:59:00.000Z"),
    (22, (5488047787108505201,17826242146809410701), 37, -1, "2021-07-20T04:22:44.190Z", "2021-07-20T15:59:00.000Z"),
    # have some short fragments here that i'm skipping
    (22, (4670535542535921690, 16968841491642259329), 40, -5, "2021-07-20T22:23:40.515Z", "2021-07-21T21:59:00.000Z"),
    (22, (15998260536714738484,4989596261685492250), 28, -4, "2021-07-22T02:16:26.533Z", "2021-07-22T13:55:41.638Z"), # deploy *right after* last tick
    (22, (1764847228751663249,9318035025343240913), 48, -5, "2021-07-22T14:12:49.353Z", "2021-07-22T23:59:56.853138Z"),
    (22, (3706102759520822111, 5462219946727173654), 44, 0, "2021-07-22T23:31:50.090Z", "2021-07-23T14:22:08.858Z"), # another deploy right after this tick
    (22, (11481638577253635672, 5140074249329476905), 54, -5, "2021-07-23T19:00:38.436Z", "2021-07-24T01:00:05.000Z"),
    (22, (36280927752704142,8633184220585947735), 60, -1, "2021-07-24T02:02:54.536Z", "2021-07-24T21:14:49.244519Z"),

    # s24 pre-d27
    (23, (6592997816912457403,7854296290632548816), 21, -1, "2021-07-26T15:12:00.097Z", "2021-07-26T17:40:01.106716Z"),
    (23, (3726545395323469742,13267718001480266576), 20, -1, "2021-07-26T18:09:01.108Z", "2021-07-26T18:50:01.586505Z"),
    # (23, (2605955602667776325,6823395170911582559), 59, -1, "2021-07-26T21:11:04.355Z", "2021-07-26T21:12:01.258994Z") doesn't work

    # s24 post-d27
    (23, (12661730784922262542,2839897453499281877), 55, -7, "2021-07-28T09:04:33.068Z", "2021-07-28T11:50:59.98005Z"),
    # (23, (15910897462727625775,13922773343731330606), 63, -1, "2021-07-30T12:19:25.010Z", "2021-07-30T12:25:02.743545Z"), # broken because of scattered
]


# fmt: on

PROGRESS_QUEUE: Optional[Queue] = None


class ProgressEventType(Enum):
    EVENTS = auto()
    FRAGMENT_START = auto()
    FRAGMENT_FINISH = auto()


def parse_args():
    parser = ArgumentParser("resim")

    parser.add_argument("outfile", nargs="?", default="-")
    parser.add_argument("--silent", default=False, action="store_true")
    parser.add_argument("--no-multiprocessing", "-no", default=False, action="store_true")
    parser.add_argument("--jobs", "-j", default=None)
    parser.add_argument(
        "--csv",
        nargs="+",
        default=[],
        metavar="CSV",
        help="Only log these CSV types. Default is logging all CSV types. Use --csv-list to see possible CSVs.",
    )
    parser.add_argument("--csv-list", default=False, action="store_true", help="List the CSVs which can be included")
    parser.add_argument("--season", action="extend", nargs="+", type=int, help="Season(s) to include, zero-indexed")

    args = parser.parse_args()
    args.csv = [Csv(Csv.__members__.get(csv, csv)) for csv in args.csv]
    return args


def get_out_file(silent, out_file_name, start_time):
    if silent:
        return None
    if out_file_name == "-":
        return stdout

    basic_filename, extension = splitext(out_file_name)
    filename = f"{basic_filename}-{start_time.replace(':', '_')}{extension}"
    return open(filename, "w", encoding="utf8")


def main():
    args = parse_args()
    if args.csv_list:
        print("Current CSV options:")
        for csv in Csv:
            print(f"  {csv.name}")
        return

    total_events = get_total_events(args.season)

    print("Running resim...")
    with tqdm(total=total_events, unit=" events", unit_scale=True) as progress:
        all_pool_args = [
            ((args.silent, args.outfile, args.csv), fragment)
            for fragment in FRAGMENTS_WITH_SEASON
            if not args.season or fragment[0] in args.season
        ]
        if args.no_multiprocessing:
            for pool_args in all_pool_args:
                run_fragment(pool_args, progress_callback=lambda: progress.update())
        else:
            global PROGRESS_QUEUE  # not really necessary but it gets rid of the shadowing warning in pycharm
            PROGRESS_QUEUE = Queue()
            processes = int(args.jobs) if args.jobs else None
            fragments_waiting = len(all_pool_args)
            fragments_processing = 0
            fragments_finished = 0

            def update_progress_postfix():
                progress.set_postfix_str(
                    f"Fragments W:{fragments_waiting}|P:{fragments_processing}|F:{fragments_finished}"
                )

            update_progress_postfix()
            with Pool(processes=processes, initializer=init_pool_worker, initargs=(PROGRESS_QUEUE,)) as pool:
                result = pool.map_async(run_fragment, all_pool_args)
                while not result.ready():
                    try:
                        (progress_event_type, data) = PROGRESS_QUEUE.get(timeout=1)
                    except Empty:
                        pass  # Check loop condition and wait again
                    else:
                        if progress_event_type == ProgressEventType.EVENTS:
                            progress.update(data)
                        elif progress_event_type == ProgressEventType.FRAGMENT_START:
                            fragments_waiting -= 1
                            fragments_processing += 1
                            update_progress_postfix()
                        elif progress_event_type == ProgressEventType.FRAGMENT_FINISH:
                            fragments_processing -= 1
                            fragments_finished += 1
                            update_progress_postfix()
                        else:
                            raise ValueError("Unknown ProgressEventType")
                result.get()  # reraise any exception from the processes
    print("Finished")


def _total_events_for_seasons(season_events: Dict[str, int], seasons: Optional[List[int]]):
    if seasons is None:
        return sum(season_events.values())
    return sum(season_events[str(season)] for season in seasons)


def get_total_events(seasons: Optional[List[int]]):
    # Using json as a "hash" because it's easy and the value we're hashing isn't too huge.
    # Note python's builtin `hash()` can't be used because it's not stable between runs.
    # "version" here is just a cachebuster
    fragments_hash = json.dumps({"version": 2, "fragments": FRAGMENTS_WITH_SEASON})
    try:
        with open("cache/event_count.json") as f:
            event_count_cache = json.load(f)
    except FileNotFoundError:
        pass
    else:
        if event_count_cache["fragments_hash"] == fragments_hash:
            return _total_events_for_seasons(event_count_cache["seasons"], seasons)
    print("Counting events...")
    print("This may take a long time if new events need to be fetched from chron")
    season_events = defaultdict(lambda: 0)
    with tqdm(total=len(FRAGMENTS_WITH_SEASON), unit=" fragments") as progress:
        for season, _, _, _, start_time, end_time in FRAGMENTS_WITH_SEASON:
            # JSON is going to stringify the season because it stringifies all object keys, so
            # _total_events_for_seasons expects string keys, and therefore we need to stringify
            # the keys here
            season_events[str(season)] += len(get_feed_between(start_time, end_time))
            progress.update()
            progress.set_description(f"Season {season}")
    with open("cache/event_count.json", "w") as f:
        json.dump(
            {
                "fragments_hash": fragments_hash,
                "seasons": season_events,
            },
            f,
        )
    return _total_events_for_seasons(season_events, seasons)


def init_pool_worker(init_args):
    global PROGRESS_QUEUE
    PROGRESS_QUEUE = init_args


def run_fragment(pool_args, progress_callback=None):
    if PROGRESS_QUEUE:
        PROGRESS_QUEUE.put((ProgressEventType.FRAGMENT_START, None))
    (silent, out_file_name, csvs_to_log), (season, rng_state, rng_offset, step, start_time, end_time) = pool_args
    out_file = get_out_file(silent, out_file_name, start_time)
    rng = Rng(rng_state, rng_offset)
    rng.step(step)
    resim = Resim(rng, out_file, run_name=f"s{season}-{start_time}", raise_on_errors=False, csvs_to_log=csvs_to_log)

    unreported_progress = 0

    if progress_callback is None:
        last_progress_report_time = time.perf_counter()

        def progress_callback():
            nonlocal unreported_progress, last_progress_report_time
            unreported_progress += 1
            now = time.perf_counter()
            if PROGRESS_QUEUE and now - last_progress_report_time > 0.25:  # report progress every quarter-second
                PROGRESS_QUEUE.put((ProgressEventType.EVENTS, unreported_progress))
                unreported_progress = 0
                last_progress_report_time = now

    resim.run(start_time, end_time, progress_callback)

    if out_file:
        out_file.close()

    if PROGRESS_QUEUE:
        PROGRESS_QUEUE.put((ProgressEventType.EVENTS, unreported_progress))
        PROGRESS_QUEUE.put((ProgressEventType.FRAGMENT_FINISH, None))


if __name__ == "__main__":
    main()
