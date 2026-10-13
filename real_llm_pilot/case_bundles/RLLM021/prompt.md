# Beijing public-data microtask RLLM021

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D1.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 140.0,
    "temperature": 28.0,
    "wind_speed": 2.2
  },
  {
    "station": "Aotizhongxin",
    "pm25": 58.0,
    "temperature": 8.4,
    "wind_speed": 0.2
  },
  {
    "station": "Aotizhongxin",
    "pm25": 59.0,
    "temperature": 6.9,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 77.0,
    "temperature": 2.8,
    "wind_speed": 1.1
  },
  {
    "station": "Aotizhongxin",
    "pm25": 53.0,
    "temperature": 21.6,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 135.0,
    "temperature": 1.2,
    "wind_speed": 0.0
  },
  {
    "station": "Aotizhongxin",
    "pm25": 40.0,
    "temperature": 16.7,
    "wind_speed": 3.8
  },
  {
    "station": "Aotizhongxin",
    "pm25": 9.0,
    "temperature": 31.1,
    "wind_speed": 1.5
  },
  {
    "station": "Aotizhongxin",
    "pm25": 15.0,
    "temperature": 1.4,
    "wind_speed": 2.2
  },
  {
    "station": "Aotizhongxin",
    "pm25": 30.0,
    "temperature": 29.2,
    "wind_speed": 2.9
  },
  {
    "station": "Aotizhongxin",
    "pm25": 23.0,
    "temperature": 18.7,
    "wind_speed": 1.9
  },
  {
    "station": "Aotizhongxin",
    "pm25": 103.0,
    "temperature": 5.3,
    "wind_speed": 0.9
  }
]
```
Forecast rows:
```json
[]
```

Return exactly one JSON object of the form:
`{"answer": {"records": "<number>", "station_count": "<number>", "minimum_pm25": "<number>", "maximum_pm25": "<number>"}}`
Do not include calculations outside the JSON object.
