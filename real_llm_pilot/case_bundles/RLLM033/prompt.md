# Beijing public-data microtask RLLM033

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `validate_load` microtask at preregistered difficulty D2.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
[
  {
    "station": "Aotizhongxin",
    "pm25": 256.0,
    "temperature": -2.6,
    "wind_speed": 1.5
  },
  {
    "station": "Changping",
    "pm25": 31.0,
    "temperature": 2.8,
    "wind_speed": 1.6
  },
  {
    "station": "Dingling",
    "pm25": 12.0,
    "temperature": 18.6,
    "wind_speed": 3.8
  },
  {
    "station": "Dingling",
    "pm25": 10.0,
    "temperature": 19.7,
    "wind_speed": 3.9
  },
  {
    "station": "Dongsi",
    "pm25": 278.0,
    "temperature": 7.4,
    "wind_speed": 0.0
  },
  {
    "station": "Dongsi",
    "pm25": 118.0,
    "temperature": 9.3,
    "wind_speed": 0.8
  },
  {
    "station": "Guanyuan",
    "pm25": 283.0,
    "temperature": -3.9,
    "wind_speed": 1.1
  },
  {
    "station": "Gucheng",
    "pm25": 9.0,
    "temperature": 0.0,
    "wind_speed": 5.8
  },
  {
    "station": "Huairou",
    "pm25": 65.0,
    "temperature": 6.4,
    "wind_speed": 1.8
  },
  {
    "station": "Nongzhanguan",
    "pm25": 54.0,
    "temperature": 3.2,
    "wind_speed": 0.4
  },
  {
    "station": "Nongzhanguan",
    "pm25": 217.0,
    "temperature": 5.9,
    "wind_speed": 1.3
  },
  {
    "station": "Shunyi",
    "pm25": 39.0,
    "temperature": 1.1,
    "wind_speed": 2.0
  },
  {
    "station": "Tiantan",
    "pm25": 40.0,
    "temperature": 3.0,
    "wind_speed": 6.4
  },
  {
    "station": "Wanliu",
    "pm25": 29.0,
    "temperature": -3.3,
    "wind_speed": 1.0
  },
  {
    "station": "Wanshouxigong",
    "pm25": 52.0,
    "temperature": 15.9,
    "wind_speed": 1.4
  },
  {
    "station": "Wanshouxigong",
    "pm25": 13.0,
    "temperature": 9.1,
    "wind_speed": 5.1
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
