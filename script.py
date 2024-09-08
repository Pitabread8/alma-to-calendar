import requests
from bs4 import BeautifulSoup
import re
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import os
import calendar

# IMPORTANT: update the following constants with your own information
ALMA_USERNAME = ""
ALMA_PASSWORD = ""
END_DATE = (2024, 12, 18)  # end of school term/year in [YYYY, MM, DD] format
# email sitav@khanlabschool.org for questions/issues

with requests.session() as s:
    # scrape data
    payload = {
        "password": ALMA_PASSWORD,
        "username": ALMA_USERNAME,
    }
    try:
        res = s.post("https://kls.getalma.com/login", data=payload)
        res.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit("Error: Alma login information may be incorrect.")

    # parse data
    req = s.get("https://kls.getalma.com/home/schedule?view=grid")
    stew = BeautifulSoup(req.content, "html.parser")
    rawBlocks = stew.find_all("h5", class_="class-name")


def extract_time(time_str):
    # convert time string to integers
    hours, minutes, *extra = map(int, re.findall(r"\d+", time_str) + ["0"])
    hours += 12 if hours < 4 else 0
    return hours, minutes


classTimes = {}
for block in rawBlocks:
    # gather class details
    name = block.getText(strip=True).replace("\n", "").replace("- Block", "")
    sibling = block.find_next_sibling().find_next_sibling().find_next_sibling()
    time = sibling.select("span")[1].get_text(strip=True)
    day = block.parent.parent.parent.select("h4")[0].getText()

    # format time data
    start_time, end_time = map(extract_time, time.split(" - "))
    classTimes.setdefault(name, []).append(
        {
            "day": day,
            "startHour": start_time[0],
            "startMinute": start_time[1],
            "endHour": end_time[0],
            "endMinute": end_time[1],
        }
    )

cal = Calendar()
# some properties are required for compliance
cal.add("prodid", "-//Sita V//khanlabschool.org//")
cal.add("version", "1.0")
cal.add("X-WR-CALNAME", "KLS Class Schedule")

today = datetime.now()
for name, times in classTimes.items():
    for block in times:
        # find first date for calendar event
        day_name = block["day"]
        day_index = list(calendar.day_name).index(day_name)
        first_date = today.replace(second=0, microsecond=0) + timedelta(
            (day_index - today.weekday() + 7) % 7
        )

        # add event subcomponents
        event = Event()
        event.add("summary", name)
        event.add(
            "dtstart",
            first_date.replace(hour=block["startHour"], minute=block["startMinute"]),
        )
        event.add(
            "dtend",
            first_date.replace(hour=block["endHour"], minute=block["endMinute"]),
        )
        event.add(
            "rrule",
            {
                "freq": "weekly",
                "until": datetime(*END_DATE),
                "byday": day_name[0:2].upper(),
            },
        )
        cal.add_component(event)

# write to disk
f = open(os.path.join("schedule.ics"), "wb")
f.write(cal.to_ical())
f.close()

print("Calendar successfully created!")
