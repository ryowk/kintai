import calendar
import datetime
import json
import os
from itertools import accumulate
from pathlib import Path
from typing import NamedTuple

from logzero import logger
from slack_sdk import WebClient

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

START_TEXTS = ['開始']
END_TEXTS = ['終了']
DATA_DIR = Path('./docs/data')


class Record(NamedTuple):
    dt: datetime.datetime
    kind: bool  # start: False, end: True


def fetch_conversations_history(
        dt_start: datetime.datetime,
        dt_end: datetime.datetime,
        token: str,
        channel: str) -> list[dict[str, str]]:
    """fetch all messages from slack channel between dt_start and dt_end (inclusive)
    """
    client = WebClient(token=token)

    messages = []
    cursor = None
    while True:
        response = client.conversations_history(
            channel=channel,
            oldest=dt_start.timestamp(),
            latest=dt_end.timestamp(),
            inclusive=True,
            cursor=cursor
        )
        messages += response['messages']
        if not response['has_more']:
            break
        cursor = response['response_metadata']['next_cursor']
    return messages


def parse_message(text: str, ts: int) -> Record:
    """
    valid format examples:
    開始
    終了
    開始 2020-01-01T00:00:00
    終了 2020-01-01T00:00:00
    """
    dt = datetime.datetime.fromtimestamp(int(float(ts)), tz=JST)
    error_msg = f"invalid message: {text} at {dt}"
    splitted = list(filter(lambda x: x, text.split(' ')))

    if len(splitted) == 1:
        if splitted[0] in START_TEXTS:
            return Record(dt, False)
        if splitted[0] in END_TEXTS:
            return Record(dt, True)
        raise ValueError(error_msg)

    if len(splitted) == 2:
        if splitted[0] in START_TEXTS:
            try:
                dt = datetime.datetime.fromisoformat(splitted[1]).astimezone(JST)
            except ValueError:
                raise ValueError(error_msg)
            return Record(dt, False)
        if splitted[0] in END_TEXTS:
            try:
                dt = datetime.datetime.fromisoformat(splitted[1]).astimezone(JST)
            except ValueError:
                raise ValueError(error_msg)
            return Record(dt, True)

    raise ValueError(error_msg)


def extract_records(messages: list[dict[str, str]]) -> list[Record]:
    """extract Records from messages
    """
    records = []
    for x in messages:
        text = x['text']
        ts = x['ts']
        record = parse_message(text, int(float(ts)))
        records.append(record)
    records = sorted(records)
    return records


def calc_total_hours(records: list[Record], date: datetime.date, now: datetime.datetime) -> float:
    """calculate total hours from records
    date and now are necessary to decide borders
    """
    if len(records) == 0:
        return 0

    # borders
    if records[0].kind:
        dt_start = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=JST)
        records.insert(0, Record(dt_start, False))
    if not records[-1].kind:
        dt_end = min(now, datetime.datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=JST))
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


def list_all_dates(year: int, month: int) -> list[datetime.date]:
    """list all dates in (year, month)
    """
    days = range(1, calendar.monthrange(year, month)[1] + 1)
    dates = [datetime.datetime(year, month, day).date() for day in days]
    return dates


def get_target_year_months(now: datetime.datetime) -> list[tuple[int, int]]:
    """get current (year, month) and previous (year, month)
    """
    year = now.year
    month = now.month
    first_date_of_this_month = datetime.datetime(year, month, 1, tzinfo=JST)
    last_date_of_last_month = first_date_of_this_month - datetime.timedelta(days=1)
    prev_year = last_date_of_last_month.year
    prev_month = last_date_of_last_month.month
    return [(year, month), (prev_year, prev_month)]


def ym_str(year: str, month: str) -> str:
    return f"{year}-{month:02}"


def main():
    SLACK_TOKEN = os.environ['SLACK_TOKEN']
    SLACK_CHANNEL = os.environ['SLACK_CHANNEL']

    now = datetime.datetime.now(JST)

    targets = get_target_year_months(now)

    summaries = {}
    for year, month in targets:
        logger.info(f"target: {ym_str(year, month)}")

        dt_start = datetime.datetime(year, month, 1, 0, 0, 0, 0, tzinfo=JST)
        dt_end = datetime.datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, 999999, tzinfo=JST)

        messages = fetch_conversations_history(dt_start, dt_end, SLACK_TOKEN, SLACK_CHANNEL)
        records = extract_records(messages)

        # validate records
        for i in range(len(records) - 1):
            if records[i].kind == records[i + 1].kind:
                raise ValueError(f"two consective starts or ends at {records[i].dt} and {records[i+1].dt}")

        all_dates = list_all_dates(year, month)
        dt_to_records = {date: [] for date in all_dates}
        for x in records:
            dt_to_records[x.dt.date()].append(Record(x.dt, x.kind))

        summary = {}
        for date in all_dates:
            summary[str(date)] = calc_total_hours(dt_to_records[date], date, now)

        save_path = DATA_DIR / f'{ym_str(year, month)}.json'
        with open(save_path, 'w') as f:
            json.dump(summary, f)
        logger.info(f"saved {save_path}")

        summaries[ym_str(year, month)] = summary

    months = []
    for year, month in targets:
        summary = summaries[ym_str(year, month)]
        year_month = ym_str(year, month)
        dates = sorted(summary.keys())
        daily_hours = [summary[d] for d in dates]
        cumulative_hours = list(accumulate(daily_hours))
        months.append({
            'year_month': year_month,
            'dates': dates,
            'daily_hours': daily_hours,
            'cumulative_hours': cumulative_hours,
        })
    display = {
        'updated_at': datetime.datetime.now(JST).isoformat(),
        'months': months,
    }
    save_path = DATA_DIR / 'display.json'
    with open(save_path, 'w') as f:
        json.dump(display, f)
    logger.info(f"saved {save_path}")


if __name__ == '__main__':
    main()
