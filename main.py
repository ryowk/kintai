import calendar
import datetime
import json
import os
from pathlib import Path
from typing import NamedTuple

from logzero import logger
from slack_sdk import WebClient

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

START_TEXTS = ['開始']
END_TEXTS = ['終了']


class Record(NamedTuple):
    dt: datetime.datetime
    kind: bool


def list_all_dates(year: int, month: int) -> list[str]:
    days = range(1, calendar.monthrange(year, month)[1] + 1)
    dates = [datetime.datetime(year, month, day).date() for day in days]
    return dates


def calc_hours(date: datetime.date, records: list[Record]) -> float:
    if len(records) == 0:
        return 0
    if records[0].kind:
        dt_start = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=JST)
        records.insert(0, Record(dt_start, False))
    if not records[-1].kind:
        dt_end = min(datetime.datetime.now(JST), datetime.datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=JST))
        records.append(Record(dt_end, True))

    total_seconds = 0

    for i in range(0, len(records), 2):
        record_start = records[i]
        record_end = records[i + 1]
        assert not record_start.kind
        assert record_end.kind
        seconds = (record_end.dt - record_start.dt).total_seconds()
        total_seconds += seconds
    return total_seconds / 3600


def main():
    now = datetime.datetime.now(JST)
    year = now.year
    month = now.month
    first_date_of_this_month = datetime.datetime(year, month, 1, tzinfo=JST)
    last_date_of_last_month = first_date_of_this_month - datetime.timedelta(days=1)
    prev_year = last_date_of_last_month.year
    prev_month = last_date_of_last_month.month

    targets = [(year, month), (prev_year, prev_month)]

    for year, month in targets:
        logger.info(f"target: {year}-{month:02}")

        dt_start = datetime.datetime(year, month, 1, 0, 0, 0, 0, tzinfo=JST)
        dt_end = datetime.datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, 999999, tzinfo=JST)

        client = WebClient(token=os.environ['SLACK_TOKEN'])

        # TODO: pagination
        response = client.conversations_history(
            channel=os.environ['SLACK_CHANNEL'],
            oldest=dt_start.timestamp(),
            latest=dt_end.timestamp(),
            inclusive=True,
        )
        records = []
        for x in response['messages']:
            text = x['text']
            ts = x['ts']
            if text not in START_TEXTS + END_TEXTS:
                continue

            kind = text in END_TEXTS

            dt = datetime.datetime.fromtimestamp(int(float(ts)), tz=JST)
            records.append(Record(dt, kind))
        records = sorted(records)

        # validate records
        for i in range(len(records) - 1):
            assert records[i].kind != records[i + 1].kind

        all_dates = list_all_dates(year, month)
        dt_to_records = {date: [] for date in all_dates}
        for x in records:
            dt_to_records[x.dt.date()].append(Record(x.dt, x.kind))

        summary = {}
        for date in all_dates:
            hours = calc_hours(date, dt_to_records[date])
            summary[str(date)] = hours

        save_path = Path('./docs/data') / f'{year}-{month:02}.json'
        with open(save_path, 'w') as f:
            json.dump(summary, f)
        logger.info(f"saved {save_path}")


if __name__ == '__main__':
    main()
