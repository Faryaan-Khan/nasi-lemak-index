# Nasi Lemak Index: what the data says

Written for a non-technical reader. Every number comes from the tables in `data/marts/`
(`insight_*.csv`), built from the government's PriceCatcher data (130.5 million prices, January
2022 to November 2026). Those tables are rebuilt every night, so the figures below are a snapshot.

**Snapshot used:** the 13 complete weeks from 24 Aug to 22 Nov 2026 for places and regions;
Dec 2025 to Nov 2026 for store types; every festival from 2022 to 2026 for festive spikes.

> PriceCatcher tracks the prices of specific items in specific shops. It is **not** a measure of
> inflation (that's the Consumer Price Index from DOSM). "Nasi Lemak Index" is just the name of a
> basket.

**How to read the figures:** prices are **medians** (the middle price, so a few odd shops can't
skew them), and every price is backed by at least 3 shops. Baskets are only costed where every
item in them is sold.

---

## 1. The same basket costs up to 23% more depending on where you live

Over the last quarter, the ingredients for one Nasi Lemak batch cost **RM 20.81 in Kuala Muda
(Kedah)** and **RM 25.55 in Segambut (Kuala Lumpur)**, a gap of **RM 4.74 (23%)** for exactly
the same items. The pattern holds for bigger baskets too:

| Basket | Cheapest district | Dearest district | Gap |
|---|---|---|---|
| Nasi Lemak (8 items) | Kuala Muda, Kedah: RM 20.81 | Segambut, KL: RM 25.55 | RM 4.74 (23%) |
| Student weekly (10 items) | Kuala Muda, Kedah: RM 55.39 | Lembah Pantai, KL: RM 63.00 | RM 7.61 (14%) |
| Family weekly (19 items) | Kuala Muda, Kedah: RM 138.14 | Segambut, KL: RM 167.14 | RM 29.00 (21%) |

Four of the five dearest districts for the Nasi Lemak basket are in Kuala Lumpur (Segambut,
Lembah Pantai, Batu, Cheras); the fifth is Langkawi. The cheapest are in Kedah, Johor (Segamat)
and Penang (Seberang Perai Utara).

For a family, RM 29 a week is about **RM 1,500 a year**, just from where you shop.

*Chart idea:* a map of Peninsular districts shaded by Family basket cost, with the cheapest and
dearest labelled.

## 2. At state level: Kedah is cheapest, the federal territories are dearest

| Basket | Cheapest state | Dearest state | Gap |
|---|---|---|---|
| Nasi Lemak | Kedah RM 21.46 | Putrajaya RM 23.71 | RM 2.25 (10.5%) |
| Student weekly | Perak RM 56.76 | Kuala Lumpur RM 59.76 | RM 3.00 (5.3%) |
| Family weekly | Kedah RM 143.32 | Putrajaya RM 159.47 | RM 16.15 (11.3%) |

State averages hide a lot: the gap *between districts* (insight 1) is about twice the gap between
states.

*Chart idea:* a ranked bar chart of states for the selected basket, with the national median as a
reference line.

**Why Sabah and Sarawak aren't in these rankings:** some basket items, including the rice brand,
aren't sold there (East Malaysian shops stock local rice brands). Rather than swap items and
compare different baskets, East Malaysia is compared item by item in insight 6.

## 3. Festive spikes are real, but only for a handful of fresh items

Most items don't move before festivals at all: the typical item's price change in the run-up is
**0%**. Price-controlled staples (rice, sugar, cooking oil, flour) stay flat. The spikes are
concentrated in a few fresh items:

- **Before Hari Raya:** only 5 of 113 items rise 5% or more on average.
- **Before Chinese New Year:** 22 of 141 items, the most of any festival.
- **Before Deepavali:** 16 of 122 items.

To make sure these are festive and not just seasonal, each item was also measured **13 weeks after
each festival** (a "placebo" window when nothing is celebrated). The items below rise before the
festival but **fall** in the placebo window.

*Chart idea:* small-multiple line charts of price index (baseline = 100) from 12 weeks before to
2 weeks after each festival, one line per year.

## 4. Before Raya: grapes and limes. Before CNY: tomatoes.

Average rise in the three weeks before the festival, compared with the same item's price 9 to 12
weeks before. "Years" means how many of the festivals since 2022 showed a rise of 5% or more.

**Hari Raya Aidilfitri (2022 to 2026)**

| Item | Avg rise | Placebo | Years up 5%+ | Peaks |
|---|---|---|---|---|
| Red grapes (anggur merah) | **+44%** | −13% | 5 of 5 | Raya week |
| Lime (limau nipis) | **+32%** | −16% | 5 of 5 | Raya week |
| Calamansi (limau kasturi) | **+20%** | −16% | 4 of 5 | Raya week |
| Winged bean (kacang botol) | +11% | +12% | 3 of 4 | Seasonal, not festive |
| Stingray (ikan pari) | +7% | −2% | 2 of 4 | 1 week before |

**Chinese New Year (2023 to 2026)**

| Item | Avg rise | Placebo | Years up 5%+ | Peaks |
|---|---|---|---|---|
| Tomato | **+61%** | −25% | 4 of 4 | 2 weeks before |
| Long brinjal (terung panjang) | **+46%** | −10% | 3 of 3 | CNY week |
| Shallots, Indian rose (bawang merah) | **+31%** | −31% | 3 of 4 | 1 week before |
| Red capsicum | +27% | −22% | 2 of 3 | 2 weeks before |
| Yellow capsicum | +27% | −15% | 2 of 3 | 1 week before |
| Seedless watermelon | +26% | −16% | 3 of 3 | 3 weeks before |
| Red grapes | +27% | +37% | 3 of 3 | Seasonal, not festive |
| Shallots, Indian regular | +21% | −11% | 2 of 4 | 1 week before |
| Lime (limau nipis) | +19% | +15% | 4 of 4 | Mostly seasonal |
| Big onion, India | +15% | −8% | 1 of 4 | Inconsistent |

**Deepavali (2022 to 2026):** only **cauliflower** stands out (**+24%**, 4 of 5 years, placebo
−13%). Shallots also rise before Deepavali, but rise as much or more 13 weeks later, so that's seasonal.

**What this means:** the festive "price hike" people feel is concentrated in fresh produce for
festive dishes (limes and grapes for Raya; tomatoes, brinjal and shallots for CNY), mostly in the
last two weeks. Buying these 3 or more weeks ahead, or switching items, avoids most of it.

**Caveats:** CNY falls in the northeast monsoon, which also hits vegetable supply, and a
placebo check reduces but can't fully rule out weather effects. Five Raya and four CNY
festivals is a small sample.

*Chart idea:* a ranked bar chart of average pre-festival rise per item, with the placebo rise as a
grey marker next to each bar.

## 5. Wet markets charge more than supermarkets; hypermarkets don't charge less

Compared like-for-like (**same item, same district, same month**) over the last 12 months:

| Store type | Typical price vs supermarket | Pairs dearer than supermarket | Comparisons |
|---|---|---|---|
| Hypermarket | **−0.6%** (about the same) | 36% | 32,376 |
| Minimarket (pasar mini) | +1.1% | 56% | 60,939 |
| Sundry shop (kedai runcit) | +5.0% | 70% | 21,443 |
| **Wet market (pasar basah)** | **+10.7%** | 77% | 18,739 |

The wet-market premium is biggest for **dry goods** like onions, garlic and dried chillies
(**+34%**) and fresh produce (**+11%**). For packaged goods the difference is small (+4.5%).
Sundry shops charge **+22%** for dry goods and **+13%** for fresh produce.

This goes against the common belief that the wet market is the cheap option. One caution: the
same item code doesn't guarantee the same freshness or quality, and wet-market prices may include
the convenience of buying small amounts.

*Chart idea:* a dot plot with one row per item group and one dot per store type, showing the
premium vs supermarkets (0% line in the middle).

## 6. East Malaysia pays more for most things, but much less for seafood

Comparing the **same items** sold in both regions over the last quarter (216 items):

- **136 items (63%) cost more in East Malaysia**, 51 cost less, 29 cost the same. Median gap:
  **+3.3%**.
- **Fresh produce is where the gap is:** a median of **+9%**. Long red chillies cost **126% more**
  (RM 29.42 vs RM 13.00 a kg), green chillies 96% more, cabbages 55 to 60% more, and red grapes 63%
  more.
- **Seafood is the opposite:** 15 of 19 fish and seafood items are cheaper in the East, a median of
  **20% less**. Kembung costs RM 11.00 vs RM 18.19 a kg (−40%), squid −37%, red snapper −36%.
- **Price-controlled goods cost the same:** sugar and cooking oil are identical in both regions.
  Eggs are about 9% dearer in the East.
- Among the basket items, the biggest East premiums are **tomatoes (+37%)** and **chicken
  (+31%)**.

*Chart idea:* a diverging bar chart of East vs Peninsular price gap per item, coloured by item
group, with seafood on the left (cheaper) and chillies on the right (dearer).

## 7. The Nasi Lemak basket costs about 11% more than in 2022

The national Nasi Lemak basket averaged **RM 19.42 a week in 2022** and **RM 21.50 so far in
2026** (+10.7%). Student weekly went from RM 51.91 to RM 56.12 (+8.1%), and Family weekly from
RM 135.57 to RM 143.49 (+5.8%).

This is the cost of **these particular items**, not inflation. Ikan bilis, a core nasi lemak
ingredient, isn't included because the government stopped pricing it in July 2025.

*Chart idea:* a weekly line chart of each basket since 2022, with festival dates marked as vertical
lines.

---

## How these were calculated (short version)

| Question | Method | SQL |
|---|---|---|
| Cheapest places | Each item's median price over 13 complete weeks (needs 4+ weeks), × basket quantity, summed only when every item is priced | `sql/04_insights.sql` §1 |
| Festive spikes | Average of the 3 weeks before the festival vs the median of weeks −12 to −9; same calculation 13 weeks later as a placebo; items in 3+ years with 100+ shops | §2 |
| Store types | Pairs of (store type, supermarket) for the same item, district and month; typical ratio = exp(median of log ratios) | §3 |
| East vs West | Median of state medians per region, items sold in 2+ East and 8+ Peninsular states | §4 |

Data: PriceCatcher, Ministry of Domestic Trade and Cost of Living (KPDN) and DOSM, via OpenDOSM /
data.gov.my, licensed CC BY 4.0.
