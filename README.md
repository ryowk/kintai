# kintai
Collect and display daily working hours

https://ryowk.github.io/kintai/

TZ: JST

## Usage
1. Fork this repository
1. Create a slack channel
1. Add a slack app to the channel
1. Set the slack conversation id and the access token as repository secrets (see [here](#secrets))
1. Execute workflow `kintai` (or create `gh-pages` branch from `main`)
1. Set GitHub pages source as following
    * branch: `gh-pages`
    * folder: `/docs`
1. Post texts to the channel (see [here](#format))
1. View the published page https://_owner_.github.io/kintai/

### Format
```
<sign>
```
posted datetime is used
```
<sign> <datetime>
```
specified datetime is used

#### Allowed signs
##### Start
* `開始`

##### End
* `終了`

#### Allowed datetime format
`YYYY-MM-DDThh:mm:ss`

#### Examples
* `開始`
* `開始 2020-01-01T12:34:56`
* `終了`
* `終了 2020-01-01T12:34:56`

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

## Development
```console
docker-compose up
```
