# Beijing public-data microtask RLLM032

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `report` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 18.0,
    "temperature": 36.5,
    "wind_speed": 1.3
  },
  {
    "station": "Changping",
    "pm25": 51.0,
    "temperature": 13.5,
    "wind_speed": 0.6
  },
  {
    "station": "Dingling",
    "pm25": 148.0,
    "temperature": 29.1,
    "wind_speed": 4.8
  },
  {
    "station": "Dingling",
    "pm25": 16.0,
    "temperature": 17.3,
    "wind_speed": 1.3
  },
  {
    "station": "Dongsi",
    "pm25": 41.0,
    "temperature": 29.0,
    "wind_speed": 2.1
  },
  {
    "station": "Guanyuan",
    "pm25": 3.0,
    "temperature": 32.5,
    "wind_speed": 2.3
  },
  {
    "station": "Gucheng",
    "pm25": 51.0,
    "temperature": 13.4,
    "wind_speed": 0.0
  },
  {
    "station": "Huairou",
    "pm25": 77.0,
    "temperature": 23.2,
    "wind_speed": 3.1
  },
  {
    "station": "Huairou",
    "pm25": 37.0,
    "temperature": 15.1,
    "wind_speed": 0.9
  },
  {
    "station": "Nongzhanguan",
    "pm25": 4.0,
    "temperature": 31.5,
    "wind_speed": 2.8
  },
  {
    "station": "Shunyi",
    "pm25": 49.0,
    "temperature": 4.9,
    "wind_speed": 1.7
  },
  {
    "station": "Tiantan",
    "pm25": 46.0,
    "temperature": 8.6,
    "wind_speed": 0.7
  },
  {
    "station": "Tiantan",
    "pm25": 55.0,
    "temperature": 8.1,
    "wind_speed": 0.8
  },
  {
    "station": "Wanliu",
    "pm25": 155.0,
    "temperature": 22.1,
    "wind_speed": 0.7
  },
  {
    "station": "Wanliu",
    "pm25": 64.0,
    "temperature": 23.6,
    "wind_speed": 1.9
  },
  {
    "station": "Wanshouxigong",
    "pm25": 45.0,
    "temperature": 20.2,
    "wind_speed": 0.1
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
