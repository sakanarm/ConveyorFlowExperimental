# Beijing public-data microtask RLLM024

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D1.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Nongzhanguan",
    "pm25": 27.0,
    "temperature": 16.5,
    "wind_speed": 0.9
  },
  {
    "station": "Nongzhanguan",
    "pm25": 99.0,
    "temperature": 21.5,
    "wind_speed": 1.8
  },
  {
    "station": "Nongzhanguan",
    "pm25": 34.0,
    "temperature": 4.7,
    "wind_speed": 1.2
  },
  {
    "station": "Nongzhanguan",
    "pm25": 105.0,
    "temperature": 21.3,
    "wind_speed": 7.6
  },
  {
    "station": "Nongzhanguan",
    "pm25": 233.0,
    "temperature": 15.1,
    "wind_speed": 0.9
  },
  {
    "station": "Nongzhanguan",
    "pm25": 32.0,
    "temperature": -1.0,
    "wind_speed": 9.7
  },
  {
    "station": "Nongzhanguan",
    "pm25": 68.0,
    "temperature": 28.8,
    "wind_speed": 2.2
  },
  {
    "station": "Nongzhanguan",
    "pm25": 40.0,
    "temperature": 2.6,
    "wind_speed": 1.5
  },
  {
    "station": "Nongzhanguan",
    "pm25": 47.0,
    "temperature": 17.7,
    "wind_speed": 1.3
  },
  {
    "station": "Nongzhanguan",
    "pm25": 34.0,
    "temperature": 15.7,
    "wind_speed": 1.7
  },
  {
    "station": "Nongzhanguan",
    "pm25": 33.0,
    "temperature": 21.9,
    "wind_speed": 1.2
  },
  {
    "station": "Nongzhanguan",
    "pm25": 137.0,
    "temperature": -0.3,
    "wind_speed": 1.3
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
