# kintai
Collect and display daily working hours

https://ryowk.github.io/kintai/

## Artifacts
### Monthly Report
`./docs/data/YYYY-MM.json`
```json
{"2020-01-01": 1.0, "2020-01-02": 2.0, "2020-01-03": 3.0}
```

### Display
`./docs/data/display.json`
```json
{
    "updated_at": "2020-01-01 00:00:00",
    "months": [
        {
            "year_month": "2020-01",
            "dates": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "daily_hours": [1.0, 2.0, 3.0],
            "cumulative_hours": [1.0, 3.0, 6.0]
        }
    ]
}
```

## Secrets
* `SLACK_TOKEN`
    * access token
    * required: `conversations.history`
* `SLACK_CHANNEL`
    * conversation id
