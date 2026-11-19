# Astrolab for Home Assistant

Put what your [Astrolab](https://github.com/bscholer/astrolab) is doing into Home Assistant: the all-night
scheduler, last night's results, tonight's forecast, and the health of the machine that processes your images.
Use it in automations and charts. It doesn't replace Astrolab, which keeps running wherever it runs today.

It pairs with [DWARF 3 for Home Assistant](https://github.com/bscholer/home-assistant-dwarf3), which gives you the
telescope itself (battery, camera, controls). This one covers what Astrolab adds on top. You can use either alone.

## Install

1. In HACS, add this repository as a custom repository (type: Integration) and install **Astrolab**.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → Astrolab**, then enter the address you open Astrolab at,
   for example `http://astrolab.local:8000`.

Home Assistant must be able to reach that address. Astrolab has no login of its own, so keep it on your home network.

## What you get

| Area | Entities |
| --- | --- |
| Scheduler | **Scheduler** state (`off`, `waiting`, `observing`, `switching`, `error`), **Current target**, **Scheduler reason** (why it is waiting), **Total integration** hours (per target in the attributes), and an **Auto scheduler** switch |
| Last night | Date, hours **shot**, **kept** and **scrapped**, frame count. Per-target detail is in the attributes |
| Tonight | **Dusk**, **Dawn**, **Best target tonight**, and how many targets are **visible tonight** |
| Forecast | Peak and average **cloud cover**, **rain** and **snow**, and a **Weather warning** (the same check that says to bring the scope in) |
| Processing | **GPU load** and **temperature**, **cache disk used**, jobs queued, running and failed in 24 h, and a **Processing** sensor |
| Link | **Telescope link**: whether Astrolab can reach the scope |

Entities that Astrolab can't fill yet show as unknown. The forecast needs your site set in Astrolab, and the
last-night sensors need at least one finished night.

## Ideas

- Notify your phone when **Scheduler** becomes `error`, or sits in `waiting` all night.
- Turn a dew heater or an outdoor light off when the scheduler starts `observing`.
- Chart **Last night kept** over time to see how a target is building up.
- Switch **Auto scheduler** off when the **Weather warning** turns on.

## Notes

- The scheduler state refreshes every 30 s. The forecast, nightly results and tonight's list refresh every
  10 to 30 minutes, and processing health every minute.
- The **Auto scheduler** switch only turns the scheduler on or off. It never changes your target list.
- This project is not affiliated with DWARFLAB.

MIT licensed.
