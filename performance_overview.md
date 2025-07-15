# Performance Results Summary

## Connections = Jobs

### TEST `listen_common.sql`

```sql
LISTEN channel_common;
```

#### 1 Connection, 1 Job

- **master**: 103620 TPS (baseline) `{101201, 103548, 104141, 104441, 104771}`
- **optimize_listen_notify**: 104295 TPS (+0.7%) `{101000, 103252, 103518, 105983, 107722}`
- **optimize_listen_notify_v2**: 105824 TPS (+2.1%) `{103950, 105520, 105719, 106556, 107373}`

#### 2 Connections, 2 Jobs

- **master**: 172864 TPS (baseline) `{172063, 172174, 172305, 172424, 175354}`
- **optimize_listen_notify**: 174963 TPS (+1.2%) `{172508, 172759, 174556, 177251, 177737}`
- **optimize_listen_notify_v2**: 177691 TPS (+2.8%) `{172742, 178011, 178330, 178690, 180680}`

#### 4 Connections, 4 Jobs

- **master**: 242245 TPS (baseline) `{241953, 242033, 242335, 242416, 242486}`
- **optimize_listen_notify**: 241961 TPS (-0.1%) `{241168, 241201, 241354, 242671, 243412}`
- **optimize_listen_notify_v2**: 242772 TPS (+0.2%) `{240908, 242178, 242532, 243663, 244580}`

#### 8 Connections, 8 Jobs

- **master**: 302469 TPS (baseline) `{300879, 301232, 301387, 303361, 305487}`
- **optimize_listen_notify**: 295563 TPS (-2.3%) `{286221, 294757, 296577, 299732, 300529}`
- **optimize_listen_notify_v2**: 298654 TPS (-1.3%) `{295856, 297680, 299424, 300045, 300266}`

#### 16 Connections, 16 Jobs

- **master**: 282766 TPS (baseline) `{277196, 279746, 283907, 285418, 287564}`
- **optimize_listen_notify**: 280171 TPS (-0.9%) `{275127, 280254, 280915, 281374, 283187}`
- **optimize_listen_notify_v2**: 283918 TPS (+0.4%) `{279114, 281784, 284288, 284438, 289964}`

#### 32 Connections, 32 Jobs

- **master**: 277125 TPS (baseline) `{271060, 273978, 278642, 279232, 282712}`
- **optimize_listen_notify**: 282542 TPS (+2.0%) `{273815, 281235, 283360, 286306, 287993}`
- **optimize_listen_notify_v2**: 281111 TPS (+1.4%) `{275900, 279936, 282112, 283334, 284275}`

### TEST `listen_notify_common.sql`

```sql
LISTEN channel_common;
NOTIFY channel_common;
```

#### 1 Connection, 1 Job

- **master**: 62818 TPS (baseline) `{62207, 62271, 62580, 63308, 63726}`
- **optimize_listen_notify**: 63091 TPS (+0.4%) `{62182, 62261, 62400, 63369, 65243}`
- **optimize_listen_notify_v2**: 62483 TPS (-0.5%) `{60989, 61877, 62187, 63282, 64079}`

#### 2 Connections, 2 Jobs

- **master**: 92063 TPS (baseline) `{91375, 91413, 91614, 92023, 93890}`
- **optimize_listen_notify**: 91194 TPS (-0.9%) `{89616, 90460, 91371, 91465, 93059}`
- **optimize_listen_notify_v2**: 90668 TPS (-1.5%) `{89481, 90335, 91025, 91195, 91302}`

#### 4 Connections, 4 Jobs

- **master**: 94692 TPS (baseline) `{94023, 94411, 94501, 95173, 95353}`
- **optimize_listen_notify**: 93562 TPS (-1.2%) `{92777, 93256, 93526, 93861, 94387}`
- **optimize_listen_notify_v2**: 93414 TPS (-1.3%) `{92271, 93309, 93416, 93807, 94266}`

#### 8 Connections, 8 Jobs

- **master**: 60928 TPS (baseline) `{60489, 60669, 60926, 61261, 61292}`
- **optimize_listen_notify**: 59979 TPS (-1.6%) `{59539, 59820, 59945, 60255, 60334}`
- **optimize_listen_notify_v2**: 59860 TPS (-1.8%) `{59232, 59721, 59786, 60279, 60282}`

#### 16 Connections, 16 Jobs

- **master**: 40350 TPS (baseline) `{39980, 40205, 40269, 40293, 41002}`
- **optimize_listen_notify**: 40016 TPS (-0.8%) `{39734, 39900, 39942, 40236, 40270}`
- **optimize_listen_notify_v2**: 39751 TPS (-1.5%) `{39346, 39688, 39751, 39960, 40008}`

#### 32 Connections, 32 Jobs

- **master**: 24839 TPS (baseline) `{22047, 25271, 25335, 25591, 25952}`
- **optimize_listen_notify**: 24556 TPS (-1.1%) `{22406, 23736, 25198, 25589, 25849}`
- **optimize_listen_notify_v2**: 24684 TPS (-0.6%) `{22862, 24242, 24993, 25223, 26099}`

### TEST `listen_notify_unique.sql`

```sql
LISTEN channel_:client_id;
NOTIFY channel_:client_id;
```

#### 1 Connection, 1 Job

- **master**: 62566 TPS (baseline) `{61895, 62129, 62690, 62722, 63393}`
- **optimize_listen_notify**: 62836 TPS (+0.4%) `{61851, 62597, 62880, 63026, 63826}`
- **optimize_listen_notify_v2**: 61849 TPS (-1.1%) `{61490, 61540, 61595, 62135, 62486}`

#### 2 Connections, 2 Jobs

- **master**: 90803 TPS (baseline) `{89360, 89875, 90959, 91556, 92266}`
- **optimize_listen_notify**: 108552 TPS (+19.5%) `{106308, 108303, 109239, 109290, 109621}`
- **optimize_listen_notify_v2**: 108122 TPS (+19.1%) `{107299, 107529, 107737, 108952, 109095}`

#### 4 Connections, 4 Jobs

- **master**: 112845 TPS (baseline) `{111188, 112946, 113132, 113407, 113553}`
- **optimize_listen_notify**: 138594 TPS (+22.8%) `{137932, 138465, 138484, 138828, 139262}`
- **optimize_listen_notify_v2**: 137378 TPS (+21.7%) `{132014, 137532, 137899, 138676, 140768}`

#### 8 Connections, 8 Jobs

- **master**: 64033 TPS (baseline) `{63817, 63922, 63992, 64147, 64290}`
- **optimize_listen_notify**: 93514 TPS (+46.0%) `{92542, 93493, 93605, 93928, 94002}`
- **optimize_listen_notify_v2**: 92794 TPS (+44.9%) `{92066, 92728, 92809, 93182, 93184}`

#### 16 Connections, 16 Jobs

- **master**: 41074 TPS (baseline) `{40857, 40972, 41015, 41239, 41287}`
- **optimize_listen_notify**: 83756 TPS (+103.9%) `{82000, 83147, 84334, 84433, 84865}`
- **optimize_listen_notify_v2**: 84830 TPS (+106.5%) `{82179, 84387, 84582, 84843, 88158}`

#### 32 Connections, 32 Jobs

- **master**: 25498 TPS (baseline) `{24808, 25030, 25606, 25970, 26077}`
- **optimize_listen_notify**: 83019 TPS (+225.6%) `{82084, 83042, 83190, 83328, 83449}`
- **optimize_listen_notify_v2**: 83408 TPS (+227.1%) `{83133, 83406, 83429, 83463, 83611}`

### TEST `listen_unique.sql`

```sql
LISTEN channel_:client_id;
```

#### 1 Connection, 1 Job

- **master**: 104129 TPS (baseline) `{102491, 103985, 104049, 104789, 105332}`
- **optimize_listen_notify**: 105022 TPS (+0.9%) `{103193, 104252, 105312, 105655, 106698}`
- **optimize_listen_notify_v2**: 105344 TPS (+1.2%) `{104174, 104610, 105618, 105731, 106589}`

#### 2 Connections, 2 Jobs

- **master**: 175856 TPS (baseline) `{172308, 176256, 176352, 176948, 177416}`
- **optimize_listen_notify**: 175982 TPS (+0.1%) `{171554, 176519, 176837, 177128, 177872}`
- **optimize_listen_notify_v2**: 175875 TPS (+0.0%) `{172231, 174732, 176146, 177127, 179139}`

#### 4 Connections, 4 Jobs

- **master**: 241986 TPS (baseline) `{241123, 241436, 241571, 242104, 243697}`
- **optimize_listen_notify**: 242179 TPS (+0.1%) `{240153, 242134, 242590, 242702, 243315}`
- **optimize_listen_notify_v2**: 242210 TPS (+0.1%) `{241539, 242020, 242281, 242336, 242874}`

#### 8 Connections, 8 Jobs

- **master**: 297684 TPS (baseline) `{288568, 298612, 299736, 300454, 301050}`
- **optimize_listen_notify**: 300012 TPS (+0.8%) `{296710, 299159, 299614, 300768, 303810}`
- **optimize_listen_notify_v2**: 295737 TPS (-0.7%) `{289515, 293556, 296098, 298508, 301006}`

#### 16 Connections, 16 Jobs

- **master**: 282955 TPS (baseline) `{276680, 279850, 280136, 288648, 289461}`
- **optimize_listen_notify**: 281315 TPS (-0.6%) `{274563, 281304, 282051, 282827, 285832}`
- **optimize_listen_notify_v2**: 280270 TPS (-0.9%) `{275396, 280690, 280833, 281686, 282747}`

#### 32 Connections, 32 Jobs

- **master**: 282187 TPS (baseline) `{275274, 281170, 282218, 283171, 289101}`
- **optimize_listen_notify**: 281519 TPS (-0.2%) `{276567, 278472, 282401, 283293, 286861}`
- **optimize_listen_notify_v2**: 285096 TPS (+1.0%) `{279397, 285088, 285926, 286479, 288589}`

### TEST `listen_unlisten_common.sql`

```sql
LISTEN channel_common;
UNLISTEN channel_common;
```

#### 1 Connection, 1 Job

- **master**: 45955 TPS (baseline) `{23364, 50399, 51759, 51772, 52482}`
- **optimize_listen_notify**: 45224 TPS (-1.6%) `{23616, 50234, 50438, 50889, 50943}`
- **optimize_listen_notify_v2**: 51402 TPS (+11.9%) `{50549, 50841, 51262, 52017, 52342}`

#### 2 Connections, 2 Jobs

- **master**: 84893 TPS (baseline) `{83539, 84170, 84414, 85557, 86785}`
- **optimize_listen_notify**: 84282 TPS (-0.7%) `{83022, 83076, 83149, 85733, 86430}`
- **optimize_listen_notify_v2**: 78124 TPS (-8.0%) `{45390, 83578, 86818, 87221, 87615}`

#### 4 Connections, 4 Jobs

- **master**: 103546 TPS (baseline) `{34724, 120262, 120480, 120553, 121712}`
- **optimize_listen_notify**: 118612 TPS (+14.5%) `{116798, 118849, 118934, 119199, 119279}`
- **optimize_listen_notify_v2**: 120208 TPS (+16.1%) `{119748, 119793, 120188, 120335, 120977}`

#### 8 Connections, 8 Jobs

- **master**: 122745 TPS (baseline) `{28163, 144741, 146116, 147094, 147611}`
- **optimize_listen_notify**: 136058 TPS (+10.8%) `{132153, 134076, 136623, 138212, 139224}`
- **optimize_listen_notify_v2**: 144452 TPS (+17.7%) `{143263, 144190, 144211, 144778, 145821}`

#### 16 Connections, 16 Jobs

- **master**: 114639 TPS (baseline) `{9176, 137708, 141592, 141991, 142730}`
- **optimize_listen_notify**: 102298 TPS (-10.8%) `{29885, 52320, 142613, 142836, 143835}`
- **optimize_listen_notify_v2**: 127704 TPS (+11.4%) `{83181, 137525, 138547, 139491, 139778}`

#### 32 Connections, 32 Jobs

- **master**: 142212 TPS (baseline) `{140789, 141343, 142207, 142364, 144359}`
- **optimize_listen_notify**: 131073 TPS (-7.8%) `{96244, 137812, 139408, 140562, 141342}`
- **optimize_listen_notify_v2**: 139490 TPS (-1.9%) `{134015, 137511, 138149, 142415, 145362}`

### TEST `listen_unlisten_unique.sql`

```sql
LISTEN channel_:client_id;
UNLISTEN channel_:client_id;
```

#### 1 Connection, 1 Job

- **master**: 52098 TPS (baseline) `{51128, 51865, 52001, 52456, 53040}`
- **optimize_listen_notify**: 45475 TPS (-12.7%) `{24141, 50392, 50524, 50932, 51386}`
- **optimize_listen_notify_v2**: 51524 TPS (-1.1%) `{51090, 51589, 51595, 51638, 51705}`

#### 2 Connections, 2 Jobs

- **master**: 86515 TPS (baseline) `{84241, 84631, 87540, 87748, 88416}`
- **optimize_listen_notify**: 72046 TPS (-16.7%) `{22027, 82749, 83509, 85910, 86033}`
- **optimize_listen_notify_v2**: 86122 TPS (-0.5%) `{84154, 84453, 86417, 86823, 88761}`

#### 4 Connections, 4 Jobs

- **master**: 120060 TPS (baseline) `{119648, 120075, 120179, 120187, 120212}`
- **optimize_listen_notify**: 106789 TPS (-11.1%) `{62399, 117324, 117531, 117972, 118719}`
- **optimize_listen_notify_v2**: 78924 TPS (-34.3%) `{15035, 21592, 119178, 119375, 119442}`

#### 8 Connections, 8 Jobs

- **master**: 117683 TPS (baseline) `{5869, 144680, 145442, 146177, 146245}`
- **optimize_listen_notify**: 129315 TPS (+9.9%) `{128689, 128975, 129053, 129732, 130126}`
- **optimize_listen_notify_v2**: 142825 TPS (+21.4%) `{137748, 143576, 143673, 143950, 145181}`

#### 16 Connections, 16 Jobs

- **master**: 143134 TPS (baseline) `{142056, 142258, 142905, 142912, 145539}`
- **optimize_listen_notify**: 121940 TPS (-14.8%) `{59626, 135863, 136912, 137236, 140066}`
- **optimize_listen_notify_v2**: 139307 TPS (-2.7%) `{136863, 139018, 139123, 140314, 141218}`

#### 32 Connections, 32 Jobs

- **master**: 142538 TPS (baseline) `{140034, 140923, 142932, 143240, 145561}`
- **optimize_listen_notify**: 125626 TPS (-11.9%) `{93449, 127901, 134262, 135168, 137349}`
- **optimize_listen_notify_v2**: 140927 TPS (-1.1%) `{139015, 139173, 140674, 141482, 144290}`

## Connections = 1000

### TEST `listen_common.sql`

```sql
LISTEN channel_common;
```

#### 1000 Connections, 1 Job

- **master**: 317472 TPS (baseline) `{313113, 314186, 314616, 321023, 324420}`
- **optimize_listen_notify**: 317436 TPS (-0.0%) `{310813, 316068, 317946, 318345, 324010}`
- **optimize_listen_notify_v2**: 319521 TPS (+0.6%) `{313326, 316498, 321269, 322541, 323972}`

#### 1000 Connections, 2 Jobs

- **master**: 392269 TPS (baseline) `{380525, 390042, 395663, 397156, 397960}`
- **optimize_listen_notify**: 391789 TPS (-0.1%) `{383685, 390120, 391237, 396116, 397786}`
- **optimize_listen_notify_v2**: 394123 TPS (+0.5%) `{388509, 391797, 394873, 396850, 398586}`

#### 1000 Connections, 4 Jobs

- **master**: 444796 TPS (baseline) `{421352, 432869, 447960, 460134, 461668}`
- **optimize_listen_notify**: 452340 TPS (+1.7%) `{428233, 446706, 449644, 458690, 478428}`
- **optimize_listen_notify_v2**: 463638 TPS (+4.2%) `{456583, 458485, 463061, 467046, 473018}`

#### 1000 Connections, 8 Jobs

- **master**: 486344 TPS (baseline) `{480841, 484710, 485419, 489464, 491286}`
- **optimize_listen_notify**: 489837 TPS (+0.7%) `{464747, 477635, 480355, 507144, 519303}`
- **optimize_listen_notify_v2**: 465182 TPS (-4.4%) `{414475, 443338, 455222, 494016, 518860}`

#### 1000 Connections, 16 Jobs

- **master**: 517958 TPS (baseline) `{455535, 487498, 522100, 527553, 597106}`
- **optimize_listen_notify**: 522751 TPS (+0.9%) `{487309, 510252, 529752, 540757, 545686}`
- **optimize_listen_notify_v2**: 527797 TPS (+1.9%) `{465750, 506901, 540161, 558421, 567750}`

#### 1000 Connections, 32 Jobs

- **master**: 511954 TPS (baseline) `{490143, 497278, 501236, 533430, 537685}`
- **optimize_listen_notify**: 486674 TPS (-4.9%) `{416401, 482570, 491856, 517993, 524552}`
- **optimize_listen_notify_v2**: 487420 TPS (-4.8%) `{425814, 458443, 476909, 526491, 549444}`

### TEST `listen_notify_common.sql`

```sql
LISTEN channel_common;
NOTIFY channel_common;
```

#### 1000 Connections, 1 Job

- **master**: 130 TPS (baseline) `{91, 95, 98, 108, 258}`
- **optimize_listen_notify**: 97 TPS (-25.7%) `{92, 96, 98, 98, 99}`
- **optimize_listen_notify_v2**: 115 TPS (-11.6%) `{98, 98, 99, 107, 173}`

#### 1000 Connections, 2 Jobs

- **master**: 96 TPS (baseline) `{91, 93, 96, 98, 103}`
- **optimize_listen_notify**: 102 TPS (+5.5%) `{96, 98, 100, 102, 112}`
- **optimize_listen_notify_v2**: 103 TPS (+6.8%) `{99, 102, 103, 104, 105}`

#### 1000 Connections, 4 Jobs

- **master**: 100 TPS (baseline) `{92, 96, 102, 103, 105}`
- **optimize_listen_notify**: 98 TPS (-1.8%) `{95, 96, 96, 96, 106}`
- **optimize_listen_notify_v2**: 106 TPS (+6.0%) `{100, 103, 104, 109, 113}`

#### 1000 Connections, 8 Jobs

- **master**: 98 TPS (baseline) `{93, 96, 99, 100, 104}`
- **optimize_listen_notify**: 101 TPS (+3.3%) `{96, 97, 99, 107, 109}`
- **optimize_listen_notify_v2**: 103 TPS (+4.5%) `{99, 100, 102, 104, 108}`

#### 1000 Connections, 16 Jobs

- **master**: 106 TPS (baseline) `{98, 101, 109, 110, 113}`
- **optimize_listen_notify**: 104 TPS (-2.1%) `{101, 101, 102, 106, 109}`
- **optimize_listen_notify_v2**: 106 TPS (-0.0%) `{100, 102, 106, 110, 112}`

#### 1000 Connections, 32 Jobs

- **master**: 108 TPS (baseline) `{102, 104, 105, 113, 116}`
- **optimize_listen_notify**: 103 TPS (-5.2%) `{96, 99, 103, 105, 109}`
- **optimize_listen_notify_v2**: 103 TPS (-4.4%) `{100, 101, 102, 107, 107}`

### TEST `listen_notify_unique.sql`

```sql
LISTEN channel_:client_id;
NOTIFY channel_:client_id;
```

#### 1000 Connections, 1 Job

- **master**: 103 TPS (baseline) `{96, 97, 107, 108, 110}`
- **optimize_listen_notify**: 3035 TPS (+2834.2%) `{2939, 2975, 2995, 3001, 3264}`
- **optimize_listen_notify_v2**: 2975 TPS (+2776.5%) `{2878, 2971, 2994, 3003, 3029}`

#### 1000 Connections, 2 Jobs

- **master**: 99 TPS (baseline) `{95, 97, 97, 98, 109}`
- **optimize_listen_notify**: 2986 TPS (+2907.6%) `{2880, 2886, 2895, 3007, 3264}`
- **optimize_listen_notify_v2**: 2975 TPS (+2895.9%) `{2857, 2885, 2957, 3052, 3124}`

#### 1000 Connections, 4 Jobs

- **master**: 98 TPS (baseline) `{94, 97, 97, 98, 102}`
- **optimize_listen_notify**: 2920 TPS (+2891.2%) `{2898, 2904, 2912, 2933, 2951}`
- **optimize_listen_notify_v2**: 2866 TPS (+2836.3%) `{2806, 2824, 2856, 2891, 2955}`

#### 1000 Connections, 8 Jobs

- **master**: 102 TPS (baseline) `{98, 99, 101, 103, 111}`
- **optimize_listen_notify**: 2910 TPS (+2742.2%) `{2881, 2888, 2926, 2927, 2929}`
- **optimize_listen_notify_v2**: 2882 TPS (+2715.0%) `{2845, 2848, 2900, 2902, 2916}`

#### 1000 Connections, 16 Jobs

- **master**: 102 TPS (baseline) `{99, 99, 100, 105, 108}`
- **optimize_listen_notify**: 2894 TPS (+2727.7%) `{2818, 2877, 2894, 2942, 2942}`
- **optimize_listen_notify_v2**: 2947 TPS (+2779.2%) `{2894, 2905, 2941, 2975, 3020}`

#### 1000 Connections, 32 Jobs

- **master**: 101 TPS (baseline) `{95, 96, 100, 103, 111}`
- **optimize_listen_notify**: 2937 TPS (+2808.2%) `{2899, 2908, 2918, 2964, 2998}`
- **optimize_listen_notify_v2**: 2910 TPS (+2781.3%) `{2814, 2822, 2917, 2934, 3063}`

### TEST `listen_unique.sql`

```sql
LISTEN channel_:client_id;
```

#### 1000 Connections, 1 Job

- **master**: 312598 TPS (baseline) `{302437, 308242, 316255, 317343, 318712}`
- **optimize_listen_notify**: 314732 TPS (+0.7%) `{308053, 314178, 315213, 316796, 319422}`
- **optimize_listen_notify_v2**: 317932 TPS (+1.7%) `{315673, 316691, 317039, 317530, 322730}`

#### 1000 Connections, 2 Jobs

- **master**: 394357 TPS (baseline) `{387643, 392886, 394205, 398322, 398730}`
- **optimize_listen_notify**: 399328 TPS (+1.3%) `{395341, 397259, 399385, 399827, 404829}`
- **optimize_listen_notify_v2**: 395643 TPS (+0.3%) `{384201, 388896, 397414, 403593, 404110}`

#### 1000 Connections, 4 Jobs

- **master**: 450618 TPS (baseline) `{433726, 436343, 453723, 456670, 472628}`
- **optimize_listen_notify**: 450444 TPS (-0.0%) `{432406, 443098, 450313, 463078, 463326}`
- **optimize_listen_notify_v2**: 443215 TPS (-1.6%) `{412306, 427871, 451187, 453815, 470897}`

#### 1000 Connections, 8 Jobs

- **master**: 474002 TPS (baseline) `{405560, 470443, 478125, 490924, 524957}`
- **optimize_listen_notify**: 474197 TPS (+0.0%) `{413201, 450354, 496278, 505527, 505622}`
- **optimize_listen_notify_v2**: 477213 TPS (+0.7%) `{466703, 468963, 475671, 486047, 488681}`

#### 1000 Connections, 16 Jobs

- **master**: 504507 TPS (baseline) `{435784, 488780, 511391, 521687, 564892}`
- **optimize_listen_notify**: 534800 TPS (+6.0%) `{507706, 534080, 534616, 543298, 554298}`
- **optimize_listen_notify_v2**: 545118 TPS (+8.0%) `{526070, 537331, 539155, 559097, 563937}`

#### 1000 Connections, 32 Jobs

- **master**: 475435 TPS (baseline) `{405622, 474420, 476811, 482273, 538049}`
- **optimize_listen_notify**: 485123 TPS (+2.0%) `{418794, 473708, 500385, 504911, 527818}`
- **optimize_listen_notify_v2**: 512798 TPS (+7.9%) `{496291, 499853, 507407, 508487, 551954}`

### TEST `listen_unlisten_common.sql`

```sql
LISTEN channel_common;
UNLISTEN channel_common;
```

#### 1000 Connections, 1 Job

- **master**: 131758 TPS (baseline) `{93047, 138776, 140358, 142624, 143986}`
- **optimize_listen_notify**: 67536 TPS (-48.7%) `{52560, 53298, 55126, 55234, 121461}`
- **optimize_listen_notify_v2**: 123238 TPS (-6.5%) `{68709, 133834, 137485, 138039, 138124}`

#### 1000 Connections, 2 Jobs

- **master**: 68140 TPS (baseline) `{66307, 67420, 68201, 68873, 69901}`
- **optimize_listen_notify**: 49611 TPS (-27.2%) `{48347, 48735, 49447, 50213, 51316}`
- **optimize_listen_notify_v2**: 66544 TPS (-2.3%) `{64596, 65878, 66437, 67504, 68306}`

#### 1000 Connections, 4 Jobs

- **master**: 58128 TPS (baseline) `{56184, 56474, 57463, 59243, 61275}`
- **optimize_listen_notify**: 43517 TPS (-25.1%) `{43110, 43341, 43541, 43698, 43896}`
- **optimize_listen_notify_v2**: 58697 TPS (+1.0%) `{58107, 58522, 58736, 58760, 59361}`

#### 1000 Connections, 8 Jobs

- **master**: 54404 TPS (baseline) `{53818, 54064, 54293, 54769, 55075}`
- **optimize_listen_notify**: 39740 TPS (-27.0%) `{35223, 39264, 41013, 41556, 41641}`
- **optimize_listen_notify_v2**: 54441 TPS (+0.1%) `{52061, 54208, 54816, 55230, 55888}`

#### 1000 Connections, 16 Jobs

- **master**: 50995 TPS (baseline) `{50001, 50616, 50942, 51642, 51774}`
- **optimize_listen_notify**: 39362 TPS (-22.8%) `{39155, 39237, 39343, 39429, 39642}`
- **optimize_listen_notify_v2**: 51699 TPS (+1.4%) `{49283, 50680, 51050, 53343, 54142}`

#### 1000 Connections, 32 Jobs

- **master**: 52851 TPS (baseline) `{52077, 52122, 52575, 53006, 54476}`
- **optimize_listen_notify**: 41602 TPS (-21.3%) `{40634, 41235, 41747, 41945, 42449}`
- **optimize_listen_notify_v2**: 53056 TPS (+0.4%) `{52392, 52699, 52942, 52961, 54287}`

### TEST `listen_unlisten_unique.sql`

```sql
LISTEN channel_:client_id;
UNLISTEN channel_:client_id;
```

#### 1000 Connections, 1 Job

- **master**: 136760 TPS (baseline) `{133653, 136212, 136576, 137418, 139940}`
- **optimize_listen_notify**: 31190 TPS (-77.2%) `{29848, 30739, 31024, 32138, 32203}`
- **optimize_listen_notify_v2**: 136205 TPS (-0.4%) `{130618, 135940, 136588, 138235, 139645}`

#### 1000 Connections, 2 Jobs

- **master**: 66560 TPS (baseline) `{61101, 66876, 67719, 67950, 69155}`
- **optimize_listen_notify**: 28160 TPS (-57.7%) `{25502, 28086, 28526, 28842, 29845}`
- **optimize_listen_notify_v2**: 68106 TPS (+2.3%) `{67010, 67171, 67307, 69504, 69539}`

#### 1000 Connections, 4 Jobs

- **master**: 58594 TPS (baseline) `{54836, 58460, 59523, 60035, 60118}`
- **optimize_listen_notify**: 26718 TPS (-54.4%) `{26092, 26539, 26629, 27139, 27190}`
- **optimize_listen_notify_v2**: 58118 TPS (-0.8%) `{56034, 57436, 58677, 59027, 59417}`

#### 1000 Connections, 8 Jobs

- **master**: 54801 TPS (baseline) `{54229, 54426, 54757, 55120, 55475}`
- **optimize_listen_notify**: 26954 TPS (-50.8%) `{24831, 26616, 26676, 28031, 28616}`
- **optimize_listen_notify_v2**: 54512 TPS (-0.5%) `{53981, 54388, 54449, 54542, 55198}`

#### 1000 Connections, 16 Jobs

- **master**: 52675 TPS (baseline) `{51124, 52238, 52421, 53252, 54338}`
- **optimize_listen_notify**: 27105 TPS (-48.5%) `{26568, 26938, 27298, 27313, 27410}`
- **optimize_listen_notify_v2**: 53031 TPS (+0.7%) `{52406, 52971, 52988, 53264, 53528}`

#### 1000 Connections, 32 Jobs

- **master**: 51948 TPS (baseline) `{47429, 51403, 51745, 52798, 56366}`
- **optimize_listen_notify**: 30139 TPS (-42.0%) `{29926, 30025, 30115, 30137, 30490}`
- **optimize_listen_notify_v2**: 53222 TPS (+2.5%) `{51596, 52982, 53806, 53850, 53878}`

