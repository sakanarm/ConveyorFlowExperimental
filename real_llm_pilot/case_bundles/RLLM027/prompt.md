# Beijing public-data microtask RLLM027

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `eda` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 88.0,
    "temperature": 9.9,
    "wind_speed": 0.9
  },
  {
    "station": "Aotizhongxin",
    "pm25": 36.0,
    "temperature": 20.2,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 9.0,
    "temperature": 6.3,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 177.0,
    "temperature": -4.0,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 156.0,
    "temperature": 25.2,
    "wind_speed": 3.8
  },
  {
    "station": "Aotizhongxin",
    "pm25": 11.0,
    "temperature": 19.9,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 48.0,
    "temperature": -1.3,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 56.0,
    "temperature": -1.2,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 33.0,
    "temperature": 2.0,
    "wind_speed": 2.4
  },
  {
    "station": "Aotizhongxin",
    "pm25": 66.0,
    "temperature": 19.6,
    "wind_speed": 1.7
  },
  {
    "station": "Aotizhongxin",
    "pm25": 20.0,
    "temperature": 16.0,
    "wind_speed": 1.4
  },
  {
    "station": "Aotizhongxin",
    "pm25": 13.0,
    "temperature": -6.7,
    "wind_speed": 1.1
  },
  {
    "station": "Aotizhongxin",
    "pm25": 67.0,
    "temperature": 5.5,
    "wind_speed": 1.1
  },
  {
    "station": "Aotizhongxin",
    "pm25": 21.0,
    "temperature": 20.8,
    "wind_speed": 1.4
  },
  {
    "station": "Aotizhongxin",
    "pm25": 144.0,
    "temperature": 21.5,
    "wind_speed": 0.6
  },
  {
    "station": "Aotizhongxin",
    "pm25": 206.0,
    "temperature": 0.7,
    "wind_speed": 0.6
  }
]
```
Forecast rows:
```json
[]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>", "mean_pm25": "<number>", "median_temperature": "<number>", "maximum_wind_speed": "<number>"}}`
Do not include calculations outside the JSON object.
